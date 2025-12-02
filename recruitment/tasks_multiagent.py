"""
Multi-agent Celery task with WebSocket progress updates.

This task runs the multi-agent orchestration system asynchronously
and sends real-time progress updates via WebSocket.
"""

from celery import shared_task
import logging
import os

logger = logging.getLogger(__name__)

# Initialize LLM once at module load time (not per-task)
logger.info("[Module Init] Initializing LLM for multi-agent tasks...")
from app.agents.orchestrator import RecruitmentOrchestrator
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

# Get LLM provider from environment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
logger.info(f"[Module Init] Using LLM provider: {LLM_PROVIDER}")

if LLM_PROVIDER == "ollama":
    SHARED_LLM = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        timeout=60  # Add timeout
    )
    logger.info(f"[Module Init] Initialized Ollama LLM: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
else:
    SHARED_LLM = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3
    )
    logger.info(f"[Module Init] Initialized OpenAI LLM: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")

logger.info("[Module Init] LLM initialization complete!")


@shared_task(bind=True, name='recruitment.analyze_with_multiagent', max_retries=2, time_limit=300, soft_time_limit=270)
def analyze_application_multiagent(self, application_id: int):
    """
    Asynchronously analyze application using multi-agent orchestration.
    
    This task:
    1. Runs RetrieverAgent, AnalyzerAgent, InterviewerAgent
    2. Sends WebSocket progress updates at each step
    3. Stores comprehensive results in database
    
    Args:
        self: Task instance (bind=True)
        application_id: ID of the Application to analyze
        
    Returns:
        dict: Multi-agent analysis results with traces
    """
    from recruitment.utils.websocket_utils import send_task_update
    from recruitment.models import Application
    
    try:
        logger.info(f"[MultiAgent Task {self.request.id}] Starting for application {application_id}")
        
        # Get application
        application = Application.objects.select_related('candidate', 'job').get(id=application_id)
        
        # Send initial WebSocket notification
        send_task_update(
            task_id=self.request.id,
            status='started',
            result={
                'application_id': application_id,
                'type': 'multiagent_analysis',
                'candidate_name': application.candidate.name,
                'job_title': application.job.title,
                'progress': 0
            }
        )
        
        # Use the shared LLM instance (already initialized at module load)
        logger.info(f"[MultiAgent Task {self.request.id}] Using pre-initialized {LLM_PROVIDER.upper()} LLM")
        
        # Create progress callback
        def progress_callback(event_type: str, data: dict):
            """Send WebSocket updates for each agent event."""
            logger.info(f"[MultiAgent Task {self.request.id}] Progress callback: {event_type} - {data}")
            
            progress_map = {
                'retriever_started': 10,
                'retriever_completed': 30,
                'analyzer_started': 35,
                'analyzer_completed': 70,
                'interviewer_started': 75,
                'interviewer_completed': 95
            }
            
            progress = progress_map.get(event_type, 50)
            
            send_task_update(
                task_id=self.request.id,
                status='progress',
                result={
                    'application_id': application_id,
                    'type': 'multiagent_analysis',
                    'event': event_type,
                    'progress': progress,
                    **data
                }
            )
        
        # Create orchestrator using the shared LLM
        logger.info(f"[MultiAgent Task {self.request.id}] Creating RecruitmentOrchestrator with shared LLM...")
        orchestrator = RecruitmentOrchestrator(SHARED_LLM, progress_callback=progress_callback)
        logger.info(f"[MultiAgent Task {self.request.id}] Orchestrator created successfully")
        
        # Run multi-agent workflow
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        logger.info(f"[MultiAgent Task {self.request.id}] Starting orchestrator.run()")
        logger.info(f"[MultiAgent Task {self.request.id}] Job: {application.job.title}")
        logger.info(f"[MultiAgent Task {self.request.id}] Candidate: {application.candidate.name}")
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        
        result = orchestrator.run(
            job_description=application.job.description,
            resume_text=application.candidate.resume_text_cache,
            candidate_id=application.candidate.id,
            job_id=application.job.id
        )
        
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        logger.info(f"[MultiAgent Task {self.request.id}] Orchestrator completed!")
        logger.info(f"[MultiAgent Task {self.request.id}] Match Score: {result.match_score}/100")
        logger.info(f"[MultiAgent Task {self.request.id}] Confidence: {result.confidence_score:.2%}")
        logger.info(f"[MultiAgent Task {self.request.id}] Agents Used: {', '.join(result.agents_used)}")
        logger.info(f"[MultiAgent Task {self.request.id}] Execution Time: {result.total_execution_time_ms}ms")
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        
        # Update application with results
        logger.info(f"[MultiAgent Task {self.request.id}] Updating application in database...")
        application.ai_score = result.match_score
        application.ai_feedback = {
            'summary': result.summary,
            'missing_skills': result.missing_skills,
            'interview_questions': result.interview_questions,
            'detailed_analysis': result.detailed_analysis.model_dump() if result.detailed_analysis else None,
            'confidence_score': result.confidence_score,
            'total_execution_time_ms': result.total_execution_time_ms,
            'agents_used': result.agents_used,
            'agent_traces': [
                {
                    'agent_name': trace.agent_name,
                    'execution_time_ms': trace.execution_time_ms,
                    'reasoning_preview': trace.reasoning[:200] + '...' if len(trace.reasoning) > 200 else trace.reasoning
                }
                for trace in result.agent_traces
            ]
        }
        application.save()
        logger.info(f"[MultiAgent Task {self.request.id}] Application updated successfully")
        logger.info(f"[MultiAgent Task {self.request.id}] Stored {len(result.agent_traces)} agent traces")
        
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        logger.info(f"[MultiAgent Task {self.request.id}] TASK COMPLETED SUCCESSFULLY")
        logger.info(f"[MultiAgent Task {self.request.id}] ========================================")
        
        # Send completion WebSocket notification
        send_task_update(
            task_id=self.request.id,
            status='completed',
            result={
                'application_id': application_id,
                'type': 'multiagent_analysis',
                'match_score': result.match_score,
                'confidence': result.confidence_score,
                'summary': result.summary,
                'progress': 100
            }
        )
        
        return {
            'application_id': application_id,
            'match_score': result.match_score,
            'confidence': result.confidence_score,
            'execution_time_ms': result.total_execution_time_ms,
            'agents_used': result.agents_used
        }
        
    except Exception as e:
        logger.error(f"[MultiAgent Task {self.request.id}] Error: {str(e)}")
        
        # Send failure WebSocket notification
        send_task_update(
            task_id=self.request.id,
            status='failed',
            error=str(e)
        )
        
        # Retry with backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)
            raise self.retry(exc=e, countdown=countdown)
        else:
            raise
