"""
Retriever Agent - Intelligent candidate retrieval with hybrid search.

This agent is responsible for finding the most relevant candidates
for a given job description using multiple search strategies.
"""

import time
from typing import List
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState, CandidateMatch, ToolCall
from app.agents.tools.database_tools import vector_search_tool, search_candidates_tool

logger = logging.getLogger(__name__)


class RetrieverAgent(BaseAgent):
    """
    Agent specialized in finding relevant candidates.
    
    Capabilities:
    - Semantic vector search using embeddings
    - Keyword-based skill matching
    - Hybrid search combining both approaches
    - Query expansion using LLM
    """
    
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name="RetrieverAgent")
        
        # Register tools
        self.register_tools([vector_search_tool, search_candidates_tool])
        
        # Create prompt for query expansion
        self.query_expansion_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert recruiter. Given a job description, extract the key skills 
            and requirements that should be used to search for candidates.
            
            Return your response as JSON with this structure:
            {{
                "primary_skills": ["skill1", "skill2", ...],
                "secondary_skills": ["skill3", "skill4", ...],
                "experience_keywords": ["keyword1", "keyword2", ...],
                "search_strategy": "vector" or "keyword" or "hybrid"
            }}
            
            Primary skills are must-haves, secondary skills are nice-to-haves.
            Choose search_strategy based on how specific the requirements are:
            - "vector" for broad, conceptual matching
            - "keyword" for very specific technical skills
            - "hybrid" for a balanced approach (recommended)
            """),
            ("user", "Job Description:\n{job_description}")
        ])
        
        self.query_chain = self.query_expansion_prompt | self.llm | JsonOutputParser()
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute candidate retrieval.
        
        Steps:
        1. Analyze job description to extract search criteria
        2. Perform vector search for semantic matching
        3. Optionally perform keyword search for specific skills
        4. Combine and rank results
        5. Update state with retrieved candidates
        """
        start_time = time.time()
        tools_called: List[ToolCall] = []
        reasoning = ""
        
        try:
            # Step 1: Query expansion
            logger.info("Analyzing job description for search criteria")
            search_criteria = self.query_chain.invoke({
                "job_description": state.job_description
            })
            
            reasoning += f"Extracted search criteria: {search_criteria}\n"
            strategy = search_criteria.get("search_strategy", "hybrid")
            
            # Step 2: Vector search
            if strategy in ["vector", "hybrid"]:
                logger.info("Performing vector search")
                vector_tool_call = self.call_tool(
                    "vector_search_candidates",
                    job_desc=state.job_description
                )
                tools_called.append(vector_tool_call)
                
                vector_results = vector_tool_call.result or []
                reasoning += f"Vector search found {len(vector_results)} candidates\n"
            else:
                vector_results = []
            
            # Step 3: Keyword search (if hybrid or keyword strategy)
            if strategy in ["keyword", "hybrid"]:
                # Combine primary and secondary skills
                all_skills = search_criteria.get("primary_skills", []) + \
                           search_criteria.get("secondary_skills", [])
                skills_query = ", ".join(all_skills[:5])  # Limit to top 5 skills
                
                logger.info(f"Performing keyword search for: {skills_query}")
                keyword_tool_call = self.call_tool(
                    "search_candidates_by_skills",
                    skills=skills_query
                )
                tools_called.append(keyword_tool_call)
                
                keyword_results = keyword_tool_call.result or []
                reasoning += f"Keyword search found {len(keyword_results)} candidates\n"
            else:
                keyword_results = []
            
            # Step 4: Combine and deduplicate results
            candidates_map = {}
            
            # Add vector search results
            for candidate in vector_results:
                candidate_id = candidate['id']
                candidates_map[candidate_id] = CandidateMatch(
                    candidate_id=candidate_id,
                    name=candidate['name'],
                    email=candidate['email'],
                    resume_text=candidate['resume_text'],
                    similarity_score=candidate.get('similarity_score', 0.0),
                    vector_score=candidate.get('similarity_score', 0.0)
                )
            
            # Add keyword search results (merge if already exists)
            for candidate in keyword_results:
                candidate_id = candidate['id']
                if candidate_id in candidates_map:
                    # Already found via vector search, just add keyword score
                    candidates_map[candidate_id].keyword_score = 0.8  # Placeholder score
                else:
                    # New candidate from keyword search
                    candidates_map[candidate_id] = CandidateMatch(
                        candidate_id=candidate_id,
                        name=candidate['name'],
                        email=candidate['email'],
                        resume_text=candidate['resume_text'],
                        similarity_score=0.7,  # Default score for keyword matches
                        keyword_score=0.8
                    )
            
            # Step 5: Rank candidates (prefer candidates found by both methods)
            ranked_candidates = sorted(
                candidates_map.values(),
                key=lambda c: (
                    (c.vector_score or 0) * 0.6 + (c.keyword_score or 0) * 0.4
                ),
                reverse=True
            )
            
            # Limit to top 10
            top_candidates = ranked_candidates[:10]
            
            reasoning += f"Final ranking produced {len(top_candidates)} candidates\n"
            reasoning += f"Top candidate: {top_candidates[0].name if top_candidates else 'None'} "
            reasoning += f"(score: {top_candidates[0].similarity_score:.2f})\n" if top_candidates else "\n"
            
            # Update state
            state.retrieved_candidates = top_candidates
            state.next_action = "analyze" if top_candidates else "expand_search"
            
            # Create execution trace
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning=reasoning,
                tools_called=tools_called,
                output={
                    "num_candidates": len(top_candidates),
                    "search_strategy": strategy,
                    "top_score": top_candidates[0].similarity_score if top_candidates else 0.0
                },
                execution_time_ms=execution_time
            )
            
            state.agent_traces.append(trace)
            
            logger.info(f"RetrieverAgent completed: found {len(top_candidates)} candidates")
            return state
            
        except Exception as e:
            logger.error(f"RetrieverAgent failed: {e}")
            state.error = f"RetrieverAgent: {str(e)}"
            
            # Still create trace even on failure
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning=reasoning + f"\nERROR: {str(e)}",
                tools_called=tools_called,
                output=None,
                execution_time_ms=execution_time
            )
            state.agent_traces.append(trace)
            
            return state
