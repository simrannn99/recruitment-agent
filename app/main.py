from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from dotenv import load_dotenv
import os

from app.models import (
    ScreeningRequest,
    ScreeningResponse,
    AgentAnalysisRequest,
    AgentAnalysisResponse,
    AgentTraceInfo,
    ToolCallInfo,
    DetailedAnalysis,
    CandidateMatchInfo
)
from app.screening_service import ResumeScreeningService

# Load environment variables
load_dotenv()


# Initialize FastAPI app
app = FastAPI(
    title="AI Resume Screening Service",
    description="Analyze resumes against job descriptions using LLM and multi-agent systems",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Initialize the screening service
screening_service = ResumeScreeningService()

# Initialize multi-agent orchestrator (lazy loading)
_orchestrator = None


def get_orchestrator():
    """Lazy load the orchestrator to avoid import issues."""
    global _orchestrator
    if _orchestrator is None:
        from app.agents.orchestrator import RecruitmentOrchestrator
        from langchain_ollama import ChatOllama
        from langchain_openai import ChatOpenAI
        
        llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if llm_provider == "ollama":
            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        else:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.3
            )
        
        _orchestrator = RecruitmentOrchestrator(llm)
    
    return _orchestrator


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Resume Screening Service",
        "version": "2.0.0",
        "features": ["single-llm-analysis", "multi-agent-orchestration"]
    }


@app.post("/analyze", response_model=ScreeningResponse)
async def analyze_resume(request: ScreeningRequest) -> ScreeningResponse:
    """
    Analyze a resume against a job description (single LLM call).

    Args:
        request: ScreeningRequest containing job_description and resume_text

    Returns:
        ScreeningResponse with structured evaluation including:
        - match_score: 0-100 score
        - summary: Brief 2-sentence summary
        - missing_skills: List of missing skills
        - interview_questions: 3 specific interview questions
    """
    try:
        result = await screening_service.analyze(
            job_description=request.job_description, resume_text=request.resume_text
        )
        return result
    except ConnectionError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"LLM service unavailable. Is Ollama running? Error: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid response from LLM: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in analyze_resume: {error_details}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing resume: {str(e)}"
        )


@app.post("/agent/analyze", response_model=AgentAnalysisResponse)
async def agent_analyze(request: AgentAnalysisRequest) -> AgentAnalysisResponse:
    """
    Analyze using multi-agent orchestration system.
    
    This endpoint uses a sophisticated multi-agent workflow:
    1. RetrieverAgent: Finds relevant candidates (if needed)
    2. AnalyzerAgent: Performs deep analysis with multi-dimensional scoring
    3. InterviewerAgent: Generates targeted interview questions
    
    Args:
        request: AgentAnalysisRequest with job description and optional resume/candidate
        
    Returns:
        AgentAnalysisResponse with comprehensive results and execution traces
    """
    try:
        orchestrator = get_orchestrator()
        
        # Run multi-agent workflow
        result = await orchestrator.arun(
            job_description=request.job_description,
            resume_text=request.resume_text,
            candidate_id=request.candidate_id,
            job_id=request.job_id
        )
        
        # Convert to response model
        response = AgentAnalysisResponse(
            match_score=result.match_score,
            summary=result.summary,
            missing_skills=result.missing_skills,
            interview_questions=result.interview_questions,
            detailed_analysis=DetailedAnalysis(**result.detailed_analysis.model_dump()) if result.detailed_analysis else None,
            retrieved_candidates=[
                CandidateMatchInfo(
                    candidate_id=c.candidate_id,
                    name=c.name,
                    email=c.email,
                    similarity_score=c.similarity_score
                ) for c in result.retrieved_candidates
            ],
            agent_traces=[
                AgentTraceInfo(
                    agent_name=trace.agent_name,
                    reasoning=trace.reasoning,
                    tools_called=[
                        ToolCallInfo(
                            tool_name=tc.tool_name,
                            execution_time_ms=tc.execution_time_ms,
                            success=tc.error is None
                        ) for tc in trace.tools_called
                    ],
                    execution_time_ms=trace.execution_time_ms,
                    timestamp=trace.timestamp
                ) for trace in result.agent_traces
            ],
            total_execution_time_ms=result.total_execution_time_ms,
            confidence_score=result.confidence_score,
            total_tools_called=result.total_tools_called,
            agents_used=result.agents_used
        )
        
        return response
        
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in agent_analyze: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in multi-agent analysis: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
