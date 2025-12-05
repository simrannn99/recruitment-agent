"""
Chat endpoints for conversational AI agent.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from app.models import (
    ChatStartRequest,
    ChatStartResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse
)
from app.agents.session_manager import SessionManager
from app.agents.conversational_agent import ConversationalAgent
from app.agents.conversation_state import ConversationMessage

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])


def create_chat_router(
    session_manager: SessionManager,
    conversational_agent: ConversationalAgent
) -> APIRouter:
    """
    Create chat router with dependencies injected.
    
    Args:
        session_manager: Session manager instance
        conversational_agent: Conversational agent instance
        
    Returns:
        Configured APIRouter
    """
    
    @router.post("/start", response_model=ChatStartResponse)
    async def start_conversation(request: ChatStartRequest) -> ChatStartResponse:
        """
        Start a new conversation session.
        
        Returns a session ID that should be used for subsequent messages.
        """
        try:
            session = session_manager.create_session(user_id=request.user_id)
            
            return ChatStartResponse(
                session_id=session.session_id,
                message="Hello! I'm your AI recruitment assistant. I can help you find candidates, analyze resumes, and answer questions about the recruitment process. What would you like to do today?"
            )
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start conversation: {str(e)}"
            )
    
    
    @router.post("/message", response_model=ChatMessageResponse)
    async def send_message(request: ChatMessageRequest) -> ChatMessageResponse:
        """
        Send a message in an existing conversation.
        
        The agent will classify intent, extract context, and generate a response.
        """
        try:
            # Get session
            session = session_manager.get_session(request.session_id)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {request.session_id} not found or expired"
                )
            
            # Add user message to session
            user_message = ConversationMessage(
                role="user",
                content=request.message
            )
            session.add_message(user_message)
            
            # Classify intent
            intent_result = conversational_agent.classify_intent(
                message=request.message,
                session=session
            )
            
            # Update context
            session.context.update(intent_result.context)
            
            # Generate response based on intent
            agent_results = None
            
            if intent_result.needs_clarification:
                response_text = conversational_agent.handle_clarification(intent_result)
            else:
                # Import agents for integration
                from app.agents.conversation_state import ConversationIntent
                from app.agents.retriever_agent import RetrieverAgent
                from app.agents.analyzer_agent import AnalyzerAgent
                from app.agents.state import AgentState
                
                # Handle different intents
                if intent_result.intent == ConversationIntent.JOB_SEARCH:
                    # Build job description from context
                    job_requirements = intent_result.context.get('job_requirements', {})
                    skills = job_requirements.get('skills', [])
                    experience = job_requirements.get('experience', '')
                    
                    # Create job description from extracted context
                    job_desc_parts = []
                    if experience:
                        job_desc_parts.append(f"{experience} level")
                    if skills:
                        job_desc_parts.append(f"with skills in {', '.join(skills)}")
                    
                    job_description = " ".join(job_desc_parts) if job_desc_parts else request.message
                    
                    # Create agent state
                    state = AgentState(job_description=job_description)
                    
                    # Call RetrieverAgent to get real candidates
                    # Wrap in sync_to_async since Django ORM doesn't work in async context
                    from asgiref.sync import sync_to_async
                    
                    def run_retriever():
                        retriever = RetrieverAgent(conversational_agent.llm)
                        return retriever.execute(state)
                    
                    state = await sync_to_async(run_retriever)()
                    
                    # Debug logging and print
                    print(f"[DEBUG] RetrieverAgent returned {len(state.retrieved_candidates)} candidates")
                    logger.info(f"RetrieverAgent returned {len(state.retrieved_candidates)} candidates")
                    
                    # Store results in session context
                    if state.retrieved_candidates:
                        print(f"[DEBUG] Processing {len(state.retrieved_candidates)} candidates")
                        session.context.search_results = [
                            {
                                'candidate_id': c.candidate_id,
                                'name': c.name,
                                'email': c.email,
                                'similarity_score': c.similarity_score,
                                'resume_text': c.resume_text[:500]  # Store snippet
                            }
                            for c in state.retrieved_candidates[:5]  # Top 5
                        ]
                        
                        print(f"[DEBUG] Stored {len(session.context.search_results)} candidates in session context")
                        logger.info(f"Stored {len(session.context.search_results)} candidates in session context")
                        
                        agent_results = {
                            'candidates': session.context.search_results,
                            'count': len(state.retrieved_candidates)
                        }
                    else:
                        print("[DEBUG] No candidates retrieved from RetrieverAgent")
                        logger.warning("No candidates retrieved from RetrieverAgent")
                        agent_results = {
                            'candidates': [],
                            'count': 0,
                            'message': 'No candidates found matching your criteria.'
                        }
                
                elif intent_result.intent == ConversationIntent.CANDIDATE_ANALYSIS:
                    # Check if we have candidates in context
                    if session.context.search_results:
                        # Try to identify which candidate they're asking about
                        candidate_ref = request.message.lower()
                        
                        if 'first' in candidate_ref or '1' in candidate_ref:
                            candidate_data = session.context.search_results[0]
                        elif 'second' in candidate_ref or '2' in candidate_ref:
                            candidate_data = session.context.search_results[1] if len(session.context.search_results) > 1 else None
                        elif 'third' in candidate_ref or '3' in candidate_ref:
                            candidate_data = session.context.search_results[2] if len(session.context.search_results) > 2 else None
                        else:
                            candidate_data = None
                        
                        if candidate_data:
                            # Get job description from context
                            job_desc = session.context.job_requirements.get('description', 'the role')
                            
                            # Create agent state for analysis
                            state = AgentState(
                                job_description=str(job_desc),
                                resume_text=candidate_data.get('resume_text', '')
                            )
                            
                            # Call AnalyzerAgent
                            analyzer = AnalyzerAgent(conversational_agent.llm)
                            state = analyzer.execute(state)
                            
                            if state.analysis:
                                agent_results = {
                                    'candidate': candidate_data,
                                    'analysis': {
                                        'match_score': state.analysis.match_score,
                                        'technical_score': state.analysis.technical_score,
                                        'experience_score': state.analysis.experience_score,
                                        'summary': state.analysis.summary,
                                        'strengths': state.analysis.strengths,
                                        'missing_skills': state.analysis.missing_skills
                                    }
                                }
                        else:
                            agent_results = {
                                'error': 'Could not identify which candidate you are referring to.'
                            }
                    else:
                        agent_results = {
                            'error': 'No candidates in context. Please search for candidates first.'
                        }
                
                # Generate conversational response with real data
                response_text = conversational_agent.generate_response(
                    message=request.message,
                    intent_result=intent_result,
                    session=session,
                    agent_results=agent_results
                )
            
            # Add assistant message to session
            assistant_message = ConversationMessage(
                role="assistant",
                content=response_text,
                intent=intent_result.intent
            )
            session.add_message(assistant_message)
            
            # Save session
            session_manager.save_session(session)
            
            return ChatMessageResponse(
                session_id=session.session_id,
                message=response_text,
                intent=intent_result.intent.value,
                confidence=intent_result.confidence,
                needs_clarification=intent_result.needs_clarification,
                clarifying_questions=intent_result.clarifying_questions,
                context=intent_result.context,
                timestamp=datetime.now()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process message: {str(e)}"
            )
    
    
    @router.get("/history/{session_id}", response_model=ChatHistoryResponse)
    async def get_history(session_id: str) -> ChatHistoryResponse:
        """
        Get conversation history for a session.
        """
        try:
            session = session_manager.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found or expired"
                )
            
            return ChatHistoryResponse(
                session_id=session.session_id,
                messages=[msg.to_dict() for msg in session.messages],
                message_count=session.message_count,
                started_at=session.started_at,
                last_message_at=session.last_message_at,
                context=session.context.to_dict()  # Include full context
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get history: {str(e)}"
            )
    
    
    @router.post("/reset/{session_id}")
    async def reset_conversation(session_id: str):
        """
        Reset conversation context while keeping the session.
        """
        try:
            session = session_manager.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found or expired"
                )
            
            # Clear messages and context
            session.messages = []
            session.message_count = 0
            session.context = ConversationContext()
            
            session_manager.save_session(session)
            
            return {"message": "Conversation reset successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to reset conversation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reset conversation: {str(e)}"
            )
    
    
    @router.delete("/{session_id}")
    async def end_conversation(session_id: str):
        """
        End a conversation and delete the session.
        """
        try:
            success = session_manager.delete_session(session_id)
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found"
                )
            
            return {"message": "Conversation ended successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to end conversation: {str(e)}"
            )
    
    return router
