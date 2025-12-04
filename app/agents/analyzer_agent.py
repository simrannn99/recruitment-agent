"""
Analyzer Agent - Deep resume analysis with structured outputs.

This agent performs comprehensive analysis of candidate-job fit,
including skill matching, experience assessment, and gap analysis.
"""

import time
import json
from typing import List
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState, AnalysisResult, ToolCall
from app.agents.tools.analytics_tool import (
    predict_candidate_success,
    analyze_bias_patterns
)

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    """
    Agent specialized in analyzing candidate-job fit.
    
    Capabilities:
    - Multi-dimensional scoring (technical, experience, culture)
    - Skill gap analysis
    - Strength identification
    - Confidence scoring
    - Explainable reasoning
    - ML-based success prediction
    - Bias pattern analysis
    """
    
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name="AnalyzerAgent")
        
        # Register analytics tools for ML predictions
        self.register_tools([
            predict_candidate_success,
            analyze_bias_patterns
        ])
        
        # Create analysis prompt
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Technical Recruiter with expertise in evaluating candidates.

Analyze the candidate's resume against the job description and provide a comprehensive evaluation.

Return your response as JSON with this EXACT structure:
{{
    "match_score": <0-100>,
    "technical_score": <0-100>,
    "experience_score": <0-100>,
    "culture_score": <0-100>,
    "summary": "<2-3 sentence summary>",
    "missing_skills": ["skill1", "skill2", ...],
    "strengths": ["strength1", "strength2", ...],
    "confidence": <0.0-1.0>,
    "reasoning": "<detailed explanation of your assessment>"
}}

Scoring Guidelines:
- match_score: Overall fit (weighted average of other scores)
- technical_score: Technical skills match (0=no match, 100=perfect match)
- experience_score: Years and relevance of experience (0=no experience, 100=exceeds requirements)
- culture_score: Soft skills, communication, team fit indicators (0=poor fit, 100=excellent fit)
- confidence: How confident you are in this assessment (0.0=very uncertain, 1.0=very certain)

Be honest and objective. It's okay to give low scores if the fit is poor.
"""),
            ("user", """Job Description:
{job_description}

Candidate Resume:
{resume_text}

Provide your detailed analysis:""")
        ])
        
        self.analysis_chain = self.analysis_prompt | self.llm | JsonOutputParser()
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute candidate analysis.
        
        Steps:
        1. Get candidate resume (from state or retrieved candidates)
        2. Perform LLM-based analysis
        3. Validate and structure results
        4. Update state with analysis
        """
        start_time = time.time()
        tools_called: List[ToolCall] = []
        reasoning = ""
        
        try:
            # Determine which candidate to analyze
            if state.resume_text:
                # Direct analysis mode (single candidate)
                resume_text = state.resume_text
                reasoning += "Analyzing provided resume\n"
            elif state.retrieved_candidates:
                # Analyze top retrieved candidate
                top_candidate = state.retrieved_candidates[0]
                resume_text = top_candidate.resume_text
                reasoning += f"Analyzing top candidate: {top_candidate.name}\n"
            else:
                raise ValueError("No candidate to analyze (no resume_text or retrieved_candidates)")
            
            # Perform LLM analysis
            logger.info("Performing LLM-based candidate analysis")
            analysis_result = self.analysis_chain.invoke({
                "job_description": state.job_description,
                "resume_text": resume_text
            })
            
            reasoning += f"LLM analysis completed\n"
            reasoning += f"Match score: {analysis_result.get('match_score', 0)}\n"
            
            # Validate scores are in range
            for score_field in ['match_score', 'technical_score', 'experience_score', 'culture_score']:
                score = analysis_result.get(score_field, 0)
                if not (0 <= score <= 100):
                    logger.warning(f"{score_field} out of range: {score}, clamping to 0-100")
                    analysis_result[score_field] = max(0, min(100, score))
            
            # Validate confidence
            confidence = analysis_result.get('confidence', 0.5)
            if not (0.0 <= confidence <= 1.0):
                logger.warning(f"Confidence out of range: {confidence}, clamping to 0-1")
                analysis_result['confidence'] = max(0.0, min(1.0, confidence))
            
            # Create AnalysisResult object
            analysis = AnalysisResult(**analysis_result)
            
            # Update state
            state.analysis = analysis
            state.next_action = "generate_questions"
            
            # Create execution trace
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning=reasoning + "\n" + analysis.reasoning,
                tools_called=tools_called,
                output={
                    "match_score": analysis.match_score,
                    "technical_score": analysis.technical_score,
                    "experience_score": analysis.experience_score,
                    "culture_score": analysis.culture_score,
                    "confidence": analysis.confidence,
                    "num_missing_skills": len(analysis.missing_skills),
                    "num_strengths": len(analysis.strengths)
                },
                execution_time_ms=execution_time
            )
            
            state.agent_traces.append(trace)
            
            logger.info(f"AnalyzerAgent completed: match_score={analysis.match_score}")
            return state
            
        except Exception as e:
            logger.error(f"AnalyzerAgent failed: {e}")
            state.error = f"AnalyzerAgent: {str(e)}"
            
            # Create trace even on failure
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning=reasoning + f"\nERROR: {str(e)}",
                tools_called=tools_called,
                output=None,
                execution_time_ms=execution_time
            )
            state.agent_traces.append(trace)
            
            return state
