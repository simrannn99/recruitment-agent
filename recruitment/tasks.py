"""
Celery tasks for background job processing in the recruitment application.

This module contains asynchronous tasks for:
- AI-powered resume analysis
- Email notifications
- Batch processing of applications
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_application_async(self, application_id):
    """
    Asynchronously analyze a job application using AI.
    
    This task is automatically triggered when a new application is created
    via Django signals. It can also be manually triggered from the admin panel.
    
    Args:
        self: Task instance (when bind=True)
        application_id: ID of the Application to analyze
        
    Returns:
        dict: Analysis results with score and feedback
        
    Raises:
        Retry: If analysis fails, retry up to 3 times with 60-second delay
    """
    from recruitment.utils.websocket_utils import send_task_update
    
    try:
        logger.info(f"[Task {self.request.id}] Starting AI analysis for application {application_id}")
        
        # Send WebSocket notification: task started
        send_task_update(
            task_id=self.request.id,
            status='started',
            result={'application_id': application_id, 'type': 'ai_analysis'}
        )
        
        # Import here to avoid circular imports
        from recruitment.services.ai_analyzer import analyze_application
        
        # Perform the analysis (calls FastAPI service)
        result = analyze_application(application_id)
        
        logger.info(f"[Task {self.request.id}] Completed AI analysis for application {application_id}")
        
        # Send WebSocket notification: task completed
        send_task_update(
            task_id=self.request.id,
            status='completed',
            result={
                'application_id': application_id,
                'type': 'ai_analysis',
                'ai_score': result.get('ai_score'),
                'summary': result.get('summary')
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Error analyzing application {application_id}: {str(e)}")
        
        # Send WebSocket notification: task failed
        send_task_update(
            task_id=self.request.id,
            status='failed',
            error=str(e)
        )
        
        # Retry with exponential backoff
        # 1st retry: 60s, 2nd retry: 120s, 3rd retry: 180s
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)


@shared_task
def send_application_status_email(application_id, status):
    """
    Send email notification when application status changes.
    
    Args:
        application_id: ID of the Application
        status: New status ('accepted' or 'rejected')
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from recruitment.models import Application
        
        application = Application.objects.select_related(
            'candidate', 'job'
        ).get(id=application_id)
        
        # Prepare email content
        subject = f"Application Update: {application.job.title}"
        
        if status == 'accepted':
            message = f"""
Dear {application.candidate.name},

Congratulations! Your application for the position of {application.job.title} has been accepted.

We were impressed by your qualifications and would like to move forward with the next steps in the hiring process.

Best regards,
Recruitment Team
"""
        else:  # rejected
            message = f"""
Dear {application.candidate.name},

Thank you for your interest in the position of {application.job.title}.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.

We appreciate the time you invested in the application process and wish you the best in your job search.

Best regards,
Recruitment Team
"""
        
        # Send email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [application.candidate.email],
            fail_silently=False,
        )
        
        logger.info(f"Sent {status} email to {application.candidate.email} for application {application_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for application {application_id}: {str(e)}")
        raise


@shared_task
def batch_analyze_applications(job_id):
    """
    Analyze all pending applications for a specific job in batch.
    
    This task queues individual analysis tasks for each pending application
    that hasn't been analyzed yet.
    
    Args:
        job_id: ID of the JobPosting
        
    Returns:
        dict: Summary of batch analysis with counts
    """
    try:
        # Import here to avoid circular imports
        from recruitment.models import JobPosting
        
        logger.info(f"Starting batch analysis for job {job_id}")
        
        job = JobPosting.objects.get(id=job_id)
        pending_applications = job.applications.filter(
            status='pending',
            ai_score__isnull=True  # Only analyze applications without scores
        )
        
        results = {
            'job_id': job_id,
            'job_title': job.title,
            'total': pending_applications.count(),
            'queued': 0,
            'failed': 0
        }
        
        # Queue individual analysis tasks
        for application in pending_applications:
            try:
                analyze_application_async.delay(application.id)
                results['queued'] += 1
                logger.info(f"Queued analysis for application {application.id}")
            except Exception as e:
                logger.error(f"Failed to queue application {application.id}: {str(e)}")
                results['failed'] += 1
        
        logger.info(f"Batch analysis completed for job {job_id}: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Batch analysis failed for job {job_id}: {str(e)}")
        raise


@shared_task
def cleanup_old_results():
    """
    Periodic task to clean up old rejected applications.
    
    This task can be scheduled with Celery Beat to run daily.
    It removes rejected applications older than 30 days to keep the database clean.
    
    Returns:
        dict: Summary of cleanup operation
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from recruitment.models import Application
        
        logger.info("Starting cleanup of old rejected applications")
        
        # Delete applications rejected more than 30 days ago
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = Application.objects.filter(
            status='rejected',
            updated_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleanup completed: deleted {deleted_count} old rejected applications")
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise


# ============================================
# Vector Search / Embedding Tasks
# ============================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_candidate_embedding_async(self, candidate_id):
    """
    Generate embedding for a candidate's resume.
    
    This task extracts text from the resume PDF and generates a vector embedding
    for semantic search capabilities.
    
    Args:
        self: Task instance (when bind=True)
        candidate_id: ID of the Candidate
        
    Returns:
        dict: Result with embedding status
    """
    from recruitment.utils.websocket_utils import send_task_update
    
    try:
        from recruitment.models import Candidate
        from recruitment.services.embedding_service import EmbeddingService
        from recruitment.services.ai_analyzer import extract_text_from_pdf
        from django.utils import timezone
        
        logger.info(f"[Task {self.request.id}] Generating embedding for candidate {candidate_id}")
        
        # Send WebSocket notification: task started
        send_task_update(
            task_id=self.request.id,
            status='started',
            result={'candidate_id': candidate_id, 'type': 'embedding_generation'}
        )
        
        # Fetch candidate
        candidate = Candidate.objects.get(id=candidate_id)
        
        # Extract resume text if not cached
        if not candidate.resume_text_cache:
            resume_text = extract_text_from_pdf(candidate.resume_file.path)
            candidate.resume_text_cache = resume_text
        else:
            resume_text = candidate.resume_text_cache
        
        if not resume_text or not resume_text.strip():
            logger.warning(f"No text extracted from resume for candidate {candidate_id}")
            send_task_update(
                task_id=self.request.id,
                status='failed',
                error='No text extracted from resume'
            )
            return {'status': 'failed', 'reason': 'No text extracted'}
        
        # Generate embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(resume_text)
        
        if embedding:
            candidate.resume_embedding = embedding
            candidate.embedding_generated_at = timezone.now()
            candidate.save(update_fields=['resume_text_cache', 'resume_embedding', 'embedding_generated_at'])
            
            logger.info(f"[Task {self.request.id}] Successfully generated embedding for candidate {candidate_id}")
            
            result = {
                'status': 'success',
                'candidate_id': candidate_id,
                'embedding_dimension': len(embedding)
            }
            
            # Send WebSocket notification: task completed
            send_task_update(
                task_id=self.request.id,
                status='completed',
                result=result
            )
            
            return result
        else:
            logger.error(f"Failed to generate embedding for candidate {candidate_id}")
            send_task_update(
                task_id=self.request.id,
                status='failed',
                error='Embedding generation returned None'
            )
            return {'status': 'failed', 'reason': 'Embedding generation returned None'}
            
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Error generating embedding for candidate {candidate_id}: {str(e)}")
        
        # Send WebSocket notification: task failed
        send_task_update(
            task_id=self.request.id,
            status='failed',
            error=str(e)
        )
        
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_job_embedding_async(self, job_id):
    """
    Generate embedding for a job posting description.
    
    Args:
        self: Task instance (when bind=True)
        job_id: ID of the JobPosting
        
    Returns:
        dict: Result with embedding status
    """
    try:
        from recruitment.models import JobPosting
        from recruitment.services.embedding_service import EmbeddingService
        from django.utils import timezone
        
        logger.info(f"[Task {self.request.id}] Generating embedding for job {job_id}")
        
        # Fetch job posting
        job = JobPosting.objects.get(id=job_id)
        
        if not job.description or not job.description.strip():
            logger.warning(f"No description for job {job_id}")
            return {'status': 'failed', 'reason': 'No description'}
        
        # Generate embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(job.description)
        
        if embedding:
            job.description_embedding = embedding
            job.embedding_generated_at = timezone.now()
            job.save(update_fields=['description_embedding', 'embedding_generated_at'])
            
            logger.info(f"[Task {self.request.id}] Successfully generated embedding for job {job_id}")
            return {
                'status': 'success',
                'job_id': job_id,
                'embedding_dimension': len(embedding)
            }
        else:
            logger.error(f"Failed to generate embedding for job {job_id}")
            return {'status': 'failed', 'reason': 'Embedding generation returned None'}
            
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Error generating embedding for job {job_id}: {str(e)}")
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)


@shared_task
def backfill_embeddings(model_type='all', force=False):
    """
    Backfill embeddings for existing candidates and/or jobs.
    
    This task is useful for generating embeddings for records that were created
    before the vector search feature was implemented.
    
    Args:
        model_type: 'candidate', 'job', or 'all' (default: 'all')
        force: If True, regenerate embeddings even if they exist (default: False)
        
    Returns:
        dict: Summary of backfill operation
    """
    try:
        from recruitment.models import Candidate, JobPosting
        
        logger.info(f"Starting embedding backfill for: {model_type} (force={force})")
        
        results = {
            'candidates': {'total': 0, 'queued': 0, 'skipped': 0},
            'jobs': {'total': 0, 'queued': 0, 'skipped': 0}
        }
        
        # Backfill candidates
        if model_type in ['candidate', 'all']:
            if force:
                candidates = Candidate.objects.all()
            else:
                candidates = Candidate.objects.filter(resume_embedding__isnull=True)
            
            results['candidates']['total'] = candidates.count()
            
            for candidate in candidates:
                try:
                    generate_candidate_embedding_async.delay(candidate.id)
                    results['candidates']['queued'] += 1
                except Exception as e:
                    logger.error(f"Failed to queue embedding for candidate {candidate.id}: {e}")
                    results['candidates']['skipped'] += 1
        
        # Backfill jobs
        if model_type in ['job', 'all']:
            if force:
                jobs = JobPosting.objects.all()
            else:
                jobs = JobPosting.objects.filter(description_embedding__isnull=True)
            
            results['jobs']['total'] = jobs.count()
            
            for job in jobs:
                try:
                    generate_job_embedding_async.delay(job.id)
                    results['jobs']['queued'] += 1
                except Exception as e:
                    logger.error(f"Failed to queue embedding for job {job.id}: {e}")
                    results['jobs']['skipped'] += 1
        
        logger.info(f"Embedding backfill completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Embedding backfill failed: {str(e)}")
        raise


@shared_task(bind=True, name='recruitment.test_retriever_agent', max_retries=2, time_limit=120, soft_time_limit=100)
def test_retriever_agent_async(self, job_id: int):
    """
    Asynchronously test the RetrieverAgent for a specific job.
    
    This task runs the RetrieverAgent to find matching candidates
    and stores the results in cache for display in the admin.
    
    Args:
        self: Task instance
        job_id: ID of the JobPosting to test
        
    Returns:
        dict: Results with candidates and execution stats
    """
    import os
    from django.core.cache import cache
    from recruitment.models import JobPosting
    from django.core.cache import cache
    
    logger.info(f"[Task {self.request.id}] ========== Starting RetrieverAgent test for job {job_id} ==========")
    
    try:
        # Get job first (before heavy imports)
        logger.info(f"[Task {self.request.id}] Fetching job posting from database...")
        job = JobPosting.objects.get(id=job_id)
        logger.info(f"[Task {self.request.id}] Job found: '{job.title}'")
        logger.info(f"[Task {self.request.id}] Job description length: {len(job.description)} characters")
        
        # Import agents (these might be slow)
        logger.info(f"[Task {self.request.id}] Importing agent modules...")
        from app.agents.retriever_agent import RetrieverAgent
        from app.agents.state import AgentState
        from langchain_ollama import ChatOllama
        logger.info(f"[Task {self.request.id}] Agent modules imported successfully")
        
        # Initialize LLM
        logger.info(f"[Task {self.request.id}] Initializing LLM...")
        llm_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        llm_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info(f"[Task {self.request.id}] LLM Model: {llm_model}, URL: {llm_url}")
        
        llm = ChatOllama(
            model=llm_model,
            base_url=llm_url,
            timeout=60  # Add timeout
        )
        logger.info(f"[Task {self.request.id}] LLM initialized successfully")
        
        # Initialize RetrieverAgent
        logger.info(f"[Task {self.request.id}] Initializing RetrieverAgent...")
        retriever = RetrieverAgent(llm)
        logger.info(f"[Task {self.request.id}] RetrieverAgent initialized")
        
        # Create initial state
        logger.info(f"[Task {self.request.id}] Creating initial agent state...")
        initial_state = AgentState(
            job_description=job.description,
            job_id=job.id
        )
        logger.info(f"[Task {self.request.id}] Initial state created")
        
        # Run retrieval
        logger.info(f"[Task {self.request.id}] ========== Calling RetrieverAgent (LLM will be invoked) ==========")
        result_state = retriever(initial_state)
        logger.info(f"[Task {self.request.id}] ========== RetrieverAgent completed ==========")
        
        # Check for errors
        if result_state.error:
            logger.error(f"[Task {self.request.id}] RetrieverAgent returned error: {result_state.error}")
            results = {
                'status': 'error',
                'error': result_state.error,
                'job_id': job_id,
                'job_title': job.title
            }
        else:
            logger.info(f"[Task {self.request.id}] Processing results...")
            logger.info(f"[Task {self.request.id}] Total candidates retrieved: {len(result_state.retrieved_candidates)}")
            
            candidates_data = []
            for i, candidate in enumerate(result_state.retrieved_candidates[:5], 1):
                logger.info(f"[Task {self.request.id}]   #{i}: {candidate.name} (score: {candidate.similarity_score:.2%})")
                candidates_data.append({
                    'id': candidate.candidate_id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'similarity_score': candidate.similarity_score,
                    'match_score': int(candidate.similarity_score * 100)
                })
            
            # Get execution stats
            tools_used = []
            execution_time = 0
            if result_state.agent_traces:
                trace = result_state.agent_traces[-1]
                tools_used = [tc.tool_name for tc in trace.tools_called]
                execution_time = trace.execution_time_ms
                logger.info(f"[Task {self.request.id}] Tools used: {', '.join(tools_used)}")
                logger.info(f"[Task {self.request.id}] Execution time: {execution_time}ms")
            
            results = {
                'status': 'success',
                'job_id': job_id,
                'job_title': job.title,
                'candidates': candidates_data,
                'candidate_count': len(candidates_data),
                'tools_used': tools_used,
                'execution_time_ms': execution_time,
                'task_id': self.request.id
            }
        
        # Store results in cache (expires in 1 hour)
        cache_key = f'retriever_test_{job_id}'
        logger.info(f"[Task {self.request.id}] Storing results in cache with key: {cache_key}")
        cache.set(cache_key, results, 3600)
        
        logger.info(f"[Task {self.request.id}] ========== Task completed successfully ==========")
        return results
        
    except Exception as e:
        logger.error(f"[Task {self.request.id}] ========== EXCEPTION OCCURRED ==========")
        logger.error(f"[Task {self.request.id}] Exception type: {type(e).__name__}")
        logger.error(f"[Task {self.request.id}] Exception message: {str(e)}")
        logger.exception(f"[Task {self.request.id}] Full traceback:")
        
        error_results = {
            'status': 'error',
            'error': str(e),
            'job_id': job_id
        }
        cache_key = f'retriever_test_{job_id}'
        cache.set(cache_key, error_results, 3600)
        raise


# Import multi-agent task (defined in separate file to avoid circular imports)
from recruitment.tasks_multiagent import analyze_application_multiagent

__all__ = [
    'analyze_application_async',
    'analyze_application_multiagent',
    'send_application_status_email',
    'batch_analyze_applications',
    'generate_candidate_embedding_async',
    'generate_job_embedding_async',
    'backfill_embeddings',
    'test_retriever_agent_async'
]
