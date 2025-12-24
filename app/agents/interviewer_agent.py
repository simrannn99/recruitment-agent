"""
Interviewer Agent - Personalized interview question generation.

This agent generates tailored interview questions based on the
candidate's profile and the job requirements.
"""

import time
from typing import List
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState, InterviewQuestion, ToolCall

logger = logging.getLogger(__name__)


class InterviewerAgent(BaseAgent):
    """
    Agent specialized in generating interview questions.
    
    Capabilities:
    - Technical questions based on required skills
    - Behavioral questions (STAR format)
    - Scenario-based questions
    - Difficulty calibration
    - Gap-focused questions
    """
    
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name="InterviewerAgent")
        
        # Create question generation prompt
        self.question_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert interviewer who creates insightful, role-specific interview questions.

Generate interview questions that:
1. Assess the candidate's fit for the specific role
2. Probe areas where the candidate may lack experience
3. Validate claimed skills and experience
4. Assess problem-solving and critical thinking
5. Evaluate cultural fit and soft skills

IMPORTANT: Return ONLY the JSON object below, with no explanations, markdown formatting, or additional text before or after the JSON.

Your response must be valid JSON that can be parsed directly, with this EXACT structure:
{{
    "questions": [
        {{
            "question": "<the question text>",
            "category": "technical|behavioral|scenario",
            "difficulty": "easy|medium|hard",
            "expected_answer_points": ["point1", "point2", ...]
        }},
        ...
    ]
}}

Generate exactly 5 questions:
- 2 technical questions (focused on missing or key skills)
- 2 behavioral questions (STAR format)
- 1 scenario question (real-world problem-solving)

Make questions specific to this role and candidate, not generic.
"""),
            ("user", """Job Description:
{job_description}

Candidate Analysis:
- Match Score: {match_score}/100
- Missing Skills: {missing_skills}
- Strengths: {strengths}
- Summary: {summary}

Generate 5 targeted interview questions:""")
        ])
        
        self.question_chain = self.question_prompt | self.llm | JsonOutputParser()
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute interview question generation.
        
        Steps:
        1. Get analysis results from state
        2. Generate targeted questions using LLM
        3. Validate and structure questions
        4. Update state with questions
        """
        start_time = time.time()
        tools_called: List[ToolCall] = []
        reasoning = ""
        
        try:
            # Check if we have analysis results
            if not state.analysis:
                raise ValueError("No analysis results available for question generation")
            
            analysis = state.analysis
            
            # Prepare input for question generation
            missing_skills_str = ", ".join(analysis.missing_skills) if analysis.missing_skills else "None identified"
            strengths_str = ", ".join(analysis.strengths) if analysis.strengths else "None identified"
            
            reasoning += f"Generating questions based on analysis\n"
            reasoning += f"Focus areas: {missing_skills_str}\n"
            
            # Generate questions using LLM
            logger.info("Generating interview questions")
            result = self.question_chain.invoke({
                "job_description": state.job_description,
                "match_score": analysis.match_score,
                "missing_skills": missing_skills_str,
                "strengths": strengths_str,
                "summary": analysis.summary
            })
            
            # Parse and validate questions
            questions_data = result.get("questions", [])
            questions: List[InterviewQuestion] = []
            
            for q_data in questions_data:
                try:
                    question = InterviewQuestion(**q_data)
                    questions.append(question)
                except Exception as e:
                    logger.warning(f"Failed to parse question: {e}")
                    continue
            
            reasoning += f"Generated {len(questions)} interview questions\n"
            
            # Categorize questions
            technical_count = sum(1 for q in questions if q.category == "technical")
            behavioral_count = sum(1 for q in questions if q.category == "behavioral")
            scenario_count = sum(1 for q in questions if q.category == "scenario")
            
            reasoning += f"Breakdown: {technical_count} technical, {behavioral_count} behavioral, {scenario_count} scenario\n"
            
            # Update state
            state.interview_questions = questions
            state.next_action = "complete"
            
            # Create execution trace
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning=reasoning,
                tools_called=tools_called,
                output={
                    "num_questions": len(questions),
                    "technical_count": technical_count,
                    "behavioral_count": behavioral_count,
                    "scenario_count": scenario_count
                },
                execution_time_ms=execution_time
            )
            
            state.agent_traces.append(trace)
            
            logger.info(f"InterviewerAgent completed: generated {len(questions)} questions")
            return state
            
        except Exception as e:
            logger.error(f"InterviewerAgent failed: {e}")
            state.error = f"InterviewerAgent: {str(e)}"
            
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
