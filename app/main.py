from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.models import ScreeningRequest, ScreeningResponse
from app.screening_service import ResumeScreeningService

# Load environment variables
load_dotenv()


# Initialize FastAPI app
app = FastAPI(
    title="AI Resume Screening Service",
    description="Analyze resumes against job descriptions using LLM",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the screening service
screening_service = ResumeScreeningService()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Resume Screening Service",
        "version": "1.0.0"
    }


@app.post("/analyze", response_model=ScreeningResponse)
async def analyze_resume(request: ScreeningRequest) -> ScreeningResponse:
    """
    Analyze a resume against a job description.
    
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
            job_description=request.job_description,
            resume_text=request.resume_text
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing resume: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
