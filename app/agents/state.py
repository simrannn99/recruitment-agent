"""
Agent state management using Pydantic models.

This module defines the state structure for multi-agent workflows,
including conversation history, intermediate results, and execution metadata.
"""

from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
import operator


class ToolCall(BaseModel):
    """Represents a single tool call made by an agent."""
    
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class AgentExecutionTrace(BaseModel):
    """Trace of a single agent's execution."""
    
    agent_name: str
    reasoning: str = ""
    tools_called: List[ToolCall] = Field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class CandidateMatch(BaseModel):
    """Represents a candidate match from retrieval."""
    
    candidate_id: int
    name: str
    email: str
    resume_text: str
    similarity_score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


class AnalysisResult(BaseModel):
    """Result from analyzer agent."""
    
    match_score: int = Field(ge=0, le=100)
    technical_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    culture_score: int = Field(ge=0, le=100)
    summary: str
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class InterviewQuestion(BaseModel):
    """Represents an interview question."""
    
    question: str
    category: str  # technical, behavioral, scenario
    difficulty: str  # easy, medium, hard
    expected_answer_points: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """
    State for multi-agent recruitment workflow.
    
    This state is passed between agents in the LangGraph workflow.
    Each agent reads from and writes to this state.
    """
    
    # Input
    job_id: Optional[int] = None
    job_description: str
    candidate_id: Optional[int] = None
    resume_text: Optional[str] = None
    
    # Retrieval results
    retrieved_candidates: List[CandidateMatch] = Field(default_factory=list)
    
    # Analysis results
    analysis: Optional[AnalysisResult] = None
    
    # Interview questions
    interview_questions: List[InterviewQuestion] = Field(default_factory=list)
    
    # Execution metadata
    agent_traces: Annotated[List[AgentExecutionTrace], operator.add] = Field(default_factory=list)
    current_agent: Optional[str] = None
    
    # Workflow control
    next_action: Optional[str] = None  # Used for conditional routing
    error: Optional[str] = None
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


class MultiAgentResponse(BaseModel):
    """Final response from multi-agent workflow."""
    
    # Core results
    match_score: int
    summary: str
    missing_skills: List[str]
    interview_questions: List[str]
    
    # Enhanced multi-agent fields
    detailed_analysis: Optional[AnalysisResult] = None
    retrieved_candidates: List[CandidateMatch] = Field(default_factory=list)
    
    # Execution metadata
    agent_traces: List[AgentExecutionTrace] = Field(default_factory=list)
    total_execution_time_ms: int = 0
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Tool usage stats
    total_tools_called: int = 0
    agents_used: List[str] = Field(default_factory=list)
