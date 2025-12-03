"""
Multi-agent orchestrator using LangGraph.

This module coordinates the execution of multiple agents in a workflow,
handling state transitions, conditional routing, and error recovery.
"""

import time
from datetime import datetime
from typing import Literal, Optional, Callable
import logging

from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel

from app.agents.state import AgentState, MultiAgentResponse
from app.agents.retriever_agent import RetrieverAgent
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.interviewer_agent import InterviewerAgent

logger = logging.getLogger(__name__)


class RecruitmentOrchestrator:
    """
    Orchestrates multi-agent workflow for recruitment analysis.
    
    Workflow:
    1. RetrieverAgent: Find relevant candidates (if not provided)
    2. AnalyzerAgent: Analyze candidate-job fit
    3. InterviewerAgent: Generate interview questions
    4. Return comprehensive results
    """
    
    def __init__(self, llm: BaseChatModel, progress_callback: Optional[Callable] = None):
        """
        Initialize the orchestrator with agents.
        
        Args:
            llm: Language model to use for all agents
            progress_callback: Optional callback for progress updates (event_type, data)
        """
        self.llm = llm
        self.progress_callback = progress_callback
        
        # Initialize agents
        self.retriever = RetrieverAgent(llm)
        self.analyzer = AnalyzerAgent(llm)
        self.interviewer = InterviewerAgent(llm)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("RecruitmentOrchestrator initialized")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes (agents)
        workflow.add_node("retrieve", self.retriever)
        workflow.add_node("analyze", self.analyzer)
        workflow.add_node("interview", self.interviewer)
        
        # Define conditional routing logic
        def should_retrieve(state: AgentState) -> Literal["retrieve", "analyze"]:
            """
            Decide if we need to retrieve candidates or can go straight to analysis.
            
            If resume_text is provided, skip retrieval.
            If candidate_id is provided, skip retrieval.
            Otherwise, retrieve candidates.
            """
            if state.resume_text or state.candidate_id:
                logger.info("Skipping retrieval (resume/candidate provided)")
                return "analyze"
            else:
                logger.info("Starting with retrieval")
                return "retrieve"
        
        def after_retrieval(state: AgentState) -> Literal["analyze", "end"]:
            """
            Decide what to do after retrieval.
            
            If candidates found, proceed to analysis.
            If no candidates and error, end workflow.
            """
            if state.error:
                logger.error(f"Retrieval failed: {state.error}")
                return "end"
            
            if state.retrieved_candidates:
                logger.info(f"Retrieved {len(state.retrieved_candidates)} candidates, proceeding to analysis")
                return "analyze"
            else:
                logger.warning("No candidates retrieved, ending workflow")
                return "end"
        
        def after_analysis(state: AgentState) -> Literal["interview", "end"]:
            """
            Decide what to do after analysis.
            
            If analysis successful, generate questions.
            If error, end workflow.
            """
            if state.error:
                logger.error(f"Analysis failed: {state.error}")
                return "end"
            
            if state.analysis:
                logger.info("Analysis complete, generating interview questions")
                return "interview"
            else:
                logger.warning("No analysis results, ending workflow")
                return "end"
        
        # Set entry point with conditional routing
        workflow.set_conditional_entry_point(
            should_retrieve,
            {
                "retrieve": "retrieve",
                "analyze": "analyze"
            }
        )
        
        # Add edges
        workflow.add_conditional_edges(
            "retrieve",
            after_retrieval,
            {
                "analyze": "analyze",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "analyze",
            after_analysis,
            {
                "interview": "interview",
                "end": END
            }
        )
        
        # Interview always ends the workflow
        workflow.add_edge("interview", END)
        
        # Compile the graph
        return workflow.compile()
    
    def run(
        self,
        job_description: str,
        resume_text: str = None,
        candidate_id: int = None,
        job_id: int = None
    ) -> MultiAgentResponse:
        """
        Run the multi-agent workflow.
        
        Args:
            job_description: Job description text
            resume_text: Optional resume text (if analyzing specific candidate)
            candidate_id: Optional candidate ID (if analyzing specific candidate)
            job_id: Optional job ID
            
        Returns:
            MultiAgentResponse with comprehensive results
        """
        start_time = time.time()
        
        try:
            # Initialize state
            initial_state = AgentState(
                job_description=job_description,
                resume_text=resume_text,
                candidate_id=candidate_id,
                job_id=job_id,
                started_at=datetime.now()
            )
            
            logger.info("Starting multi-agent workflow")
            
            # Run the workflow - LangGraph returns a dict
            result = self.workflow.invoke(initial_state)
            
            # Convert dict back to AgentState if needed
            if isinstance(result, dict):
                final_state = AgentState(**result)
            else:
                final_state = result
            
            # Mark completion time
            final_state.completed_at = datetime.now()
            
            # Calculate total execution time
            total_time = int((time.time() - start_time) * 1000)
            
            # Build response
            response = self._build_response(final_state, total_time)
            
            logger.info(f"Multi-agent workflow completed in {total_time}ms")
            return response
            
        except Exception as e:
            logger.error(f"Multi-agent workflow failed: {e}")
            
            # Return error response
            return MultiAgentResponse(
                match_score=0,
                summary=f"Workflow failed: {str(e)}",
                missing_skills=[],
                interview_questions=[],
                total_execution_time_ms=int((time.time() - start_time) * 1000),
                confidence_score=0.0
            )
    
    async def arun(
        self,
        job_description: str,
        resume_text: str = None,
        candidate_id: int = None,
        job_id: int = None
    ) -> MultiAgentResponse:
        """
        Run the multi-agent workflow asynchronously.
        
        Args:
            job_description: Job description text
            resume_text: Optional resume text (if analyzing specific candidate)
            candidate_id: Optional candidate ID (if analyzing specific candidate)
            job_id: Optional job ID
            
        Returns:
            MultiAgentResponse with comprehensive results
        """
        # For now, just call the sync version
        # In the future, this could use async LangGraph execution
        return self.run(job_description, resume_text, candidate_id, job_id)
    
    def _build_response(self, state: AgentState, total_time: int) -> MultiAgentResponse:
        """
        Build the final response from the workflow state.
        
        Args:
            state: Final workflow state
            total_time: Total execution time in milliseconds
            
        Returns:
            MultiAgentResponse
        """
        # Extract core results
        if state.analysis:
            match_score = state.analysis.match_score
            summary = state.analysis.summary
            missing_skills = state.analysis.missing_skills
            confidence = state.analysis.confidence
            detailed_analysis = state.analysis
        else:
            match_score = 0
            summary = "Analysis not completed"
            missing_skills = []
            confidence = 0.0
            detailed_analysis = None
        
        # Convert interview questions from InterviewQuestion objects to dicts
        interview_questions = [
            {
                "question": q.question,
                "category": q.category,
                "difficulty": q.difficulty,
                "expected_answer_points": q.expected_answer_points
            }
            for q in state.interview_questions
        ]
        
        # Get list of agents that were used
        agents_used = list(set([trace.agent_name for trace in state.agent_traces]))
        
        # Count total tools called
        total_tools = sum(len(trace.tools_called) for trace in state.agent_traces)
        
        # Build response
        return MultiAgentResponse(
            match_score=match_score,
            summary=summary,
            missing_skills=missing_skills,
            interview_questions=interview_questions,
            retrieved_candidates=state.retrieved_candidates,
            detailed_analysis=detailed_analysis,
            agent_traces=state.agent_traces,
            total_execution_time_ms=total_time,
            confidence_score=confidence,
            agents_used=agents_used,
            total_tools_called=total_tools
        )
