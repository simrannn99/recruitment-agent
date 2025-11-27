from pydantic import BaseModel, Field
from typing import List


class ScreeningRequest(BaseModel):
    """Request model for resume screening."""
    job_description: str = Field(..., description="The job description text")
    resume_text: str = Field(..., description="The resume/CV text")


class ScreeningResponse(BaseModel):
    """Response model for resume screening results."""
    match_score: int = Field(..., ge=0, le=100, description="Match score between 0-100")
    summary: str = Field(..., max_length=500, description="Brief summary (max 2 sentences)")
    missing_skills: List[str] = Field(..., description="List of skills mentioned in JD but missing from resume")
    interview_questions: List[str] = Field(..., min_length=3, max_length=3, description="Exactly 3 specific interview questions")
