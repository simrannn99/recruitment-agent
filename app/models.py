"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ScreeningRequest(BaseModel):
    """Request model for resume screening."""
    job_description: str = Field(..., description="The job description text")
    resume_text: str = Field(..., description="The resume/CV text")


class ScreeningResponse(BaseModel):
    """Response model for resume screening."""
    match_score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    summary: str = Field(..., description="Brief 2-sentence summary of candidate fit")
    missing_skills: List[str] = Field(default_factory=list, description="List of missing skills")
    interview_questions: List[Dict[str, Any]] = Field(default_factory=list, description="Interview questions with category, difficulty, and expected answers")
    safety_report: Optional[Dict[str, Any]] = Field(None, description="Safety guardrails report")


# ============================================
# Multi-Agent Models
# ============================================

class AgentAnalysisRequest(BaseModel):
    """Request model for multi-agent analysis."""
    
    job_description: str = Field(..., description="The job description text")
    resume_text: Optional[str] = Field(None, description="Optional resume text for direct analysis")
    candidate_id: Optional[int] = Field(None, description="Optional candidate ID from database")
    job_id: Optional[int] = Field(None, description="Optional job ID from database")
    use_retrieval: bool = Field(True, description="Whether to use retrieval agent (if no resume provided)")


class ToolCallInfo(BaseModel):
    """Information about a tool call made by an agent."""
    
    tool_name: str
    execution_time_ms: Optional[int] = None
    success: bool = True


class AgentTraceInfo(BaseModel):
    """Execution trace for a single agent."""
    
    agent_name: str
    reasoning: str
    tools_called: List[ToolCallInfo] = Field(default_factory=list)
    execution_time_ms: int
    timestamp: datetime


class DetailedAnalysis(BaseModel):
    """Detailed analysis results."""
    
    match_score: int = Field(ge=0, le=100)
    technical_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    culture_score: int = Field(ge=0, le=100)
    summary: str
    missing_skills: List[str]
    strengths: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class CandidateMatchInfo(BaseModel):
    """Information about a matched candidate."""
    
    candidate_id: int
    name: str
    email: str
    similarity_score: float


class AgentAnalysisResponse(BaseModel):
    """Response model for multi-agent analysis."""
    
    # Core results (backward compatible with ScreeningResponse)
    match_score: int = Field(ge=0, le=100)
    summary: str
    missing_skills: List[str]
    interview_questions: List[Dict[str, Any]]  # Changed to preserve rich format
    
    # Enhanced multi-agent fields
    detailed_analysis: Optional[DetailedAnalysis] = None
    retrieved_candidates: List[CandidateMatchInfo] = Field(default_factory=list)
    
    # Execution metadata
    agent_traces: List[AgentTraceInfo] = Field(default_factory=list)
    total_execution_time_ms: int
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Tool usage stats
    total_tools_called: int = 0
    agents_used: List[str] = Field(default_factory=list)


# ============================================
# Conversational Chat Models
# ============================================

class ChatStartRequest(BaseModel):
    """Request to start a new conversation."""
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class ChatStartResponse(BaseModel):
    """Response with new session ID."""
    session_id: str
    message: str = "Conversation started! How can I help you today?"


class ChatMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    """Response to a chat message."""
    session_id: str
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    needs_clarification: bool = False
    clarifying_questions: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Response with conversation history."""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int
    started_at: datetime
    last_message_at: datetime
    context: Optional[Dict[str, Any]] = None  # Include full session context

