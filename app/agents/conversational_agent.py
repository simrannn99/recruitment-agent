"""
Conversational Agent - Multi-turn dialogue for recruitment.

Handles natural language conversations, intent classification,
and context-aware interactions with users.
"""

import time
import logging
from typing import Dict, Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.memory import ConversationBufferWindowMemory

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.conversation_state import (
    ConversationSession,
    ConversationMessage,
    ConversationIntent,
    IntentClassificationResult
)

logger = logging.getLogger(__name__)


class ConversationalAgent(BaseAgent):
    """
    Agent specialized in multi-turn conversations.
    
    Capabilities:
    - Intent classification
    - Context extraction and management
    - Clarifying questions
    - Natural language understanding
    - Integration with other agents
    """
    
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name="ConversationalAgent")
        
        # Initialize memory for conversation context
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Keep last 10 messages
            memory_key="chat_history",
            return_messages=True
        )
        
        # Intent classification prompt
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant for a recruitment platform. 
            Analyze the user's message and classify their intent.
            
            Conversation history:
            {history}
            
            User message: {message}
            
            Classify into ONE of these intents:
            - job_search: User wants to find candidates for a job
            - candidate_analysis: User wants detailed analysis of specific candidate(s)
            - clarification_needed: Not enough information to proceed
            - general_query: General questions about the platform
            - conversation_end: User wants to end conversation
            
            Extract any relevant context from the message:
            - job_requirements:
              * skills: List of technical skills mentioned (e.g., ["Python", "Django", "React"])
              * experience: Experience level (e.g., "junior", "mid", "senior", "5 years")
              * location: Location if mentioned
              * remote: true/false if mentioned
            - candidate_references: References to candidates (e.g., "first", "second", "the senior one")
            - preferences: salary, culture, team size, etc.
            
            IMPORTANT: Extract skills and experience even if other details are missing!
            
            Return JSON with this exact structure:
            {{
                "intent": "job_search|candidate_analysis|clarification_needed|general_query|conversation_end",
                "confidence": 0.95,
                "context": {{
                    "job_requirements": {{
                        "skills": [],
                        "experience": "",
                        "location": "",
                        "remote": false
                    }},
                    "candidate_ids": [],
                    "preferences": {{}}
                }},
                "needs_clarification": false,
                "clarifying_questions": []
            }}
            
            Only set needs_clarification=true if the message is truly vague (e.g., "I need help").
            If skills or experience are mentioned, extract them and set needs_clarification=false.
            """),
            ("user", "{message}")
        ])
        
        self.intent_chain = self.intent_prompt | self.llm | JsonOutputParser()
        
        # Response generation prompt
        self.response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI recruitment assistant. 
            Generate a natural, conversational response based on the intent and context.
            
            Conversation history:
            {history}
            
            Current intent: {intent}
            Extracted context: {context}
            
            Guidelines:
            - Be conversational and friendly
            - If clarification is needed, ask specific questions
            - If you have search results, present them clearly
            - Offer next steps or follow-up actions
            - Keep responses concise but informative
            - Use bullet points for lists
            - Use emojis sparingly for emphasis
            
            Generate a helpful response to the user.
            """),
            ("user", "{message}")
        ])
        
        self.response_chain = self.response_prompt | self.llm
    
    def classify_intent(
        self,
        message: str,
        session: ConversationSession
    ) -> IntentClassificationResult:
        """
        Classify user intent from message.
        
        Args:
            message: User's message
            session: Current conversation session
            
        Returns:
            IntentClassificationResult with classified intent and context
        """
        try:
            # Get conversation history
            history = session.get_history_text(n=5)
            
            # Classify intent
            result = self.intent_chain.invoke({
                "message": message,
                "history": history
            })
            
            # Parse result
            intent = ConversationIntent(result['intent'])
            
            return IntentClassificationResult(
                intent=intent,
                confidence=result.get('confidence', 0.0),
                context=result.get('context', {}),
                needs_clarification=result.get('needs_clarification', False),
                clarifying_questions=result.get('clarifying_questions', [])
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Default to clarification if classification fails
            return IntentClassificationResult(
                intent=ConversationIntent.CLARIFICATION_NEEDED,
                confidence=0.5,
                needs_clarification=True,
                clarifying_questions=[
                    "Could you please rephrase your question?",
                    "What specific information are you looking for?"
                ]
            )
    
    def generate_response(
        self,
        message: str,
        intent_result: IntentClassificationResult,
        session: ConversationSession,
        agent_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate conversational response.
        
        Args:
            message: User's message
            intent_result: Classified intent
            session: Current conversation session
            agent_results: Optional results from other agents (search, analysis)
            
        Returns:
            Generated response text
        """
        try:
            # If we have agent results with candidates, format them directly
            if agent_results and 'candidates' in agent_results:
                candidates = agent_results['candidates']
                
                if not candidates or len(candidates) == 0:
                    return ("I searched our database but couldn't find any candidates matching those exact criteria. "
                           "Would you like to:\n"
                           "• Broaden the search criteria?\n"
                           "• Try different skills or experience levels?\n"
                           "• See candidates with partial matches?")
                
                # Build response with REAL candidate data
                response = f"Great! I found {len(candidates)} candidate{'s' if len(candidates) > 1 else ''} matching your requirements:\n\n"
                
                for i, candidate in enumerate(candidates[:5], 1):
                    name = candidate.get('name', 'Unknown')
                    email = candidate.get('email', 'N/A')
                    score = candidate.get('similarity_score', 0.0)
                    
                    response += f"{i}. **{name}** ({email})\n"
                    response += f"   Match score: {score:.0%}\n\n"
                
                response += "\nWould you like to:\n"
                response += "• See detailed analysis of any specific candidate?\n"
                response += "• Get interview questions for these candidates?\n"
                response += "• Refine the search further?"
                
                return response
            
            # If we have analysis results
            if agent_results and 'analysis' in agent_results:
                analysis = agent_results['analysis']
                candidate = agent_results.get('candidate', {})
                
                response = f"Here's a detailed analysis of **{candidate.get('name', 'the candidate')}**:\n\n"
                response += f"**Match Score:** {analysis.get('match_score', 0)}/100\n"
                response += f"**Technical Score:** {analysis.get('technical_score', 0)}/100\n"
                response += f"**Experience Score:** {analysis.get('experience_score', 0)}/100\n\n"
                
                if analysis.get('summary'):
                    response += f"**Summary:**\n{analysis['summary']}\n\n"
                
                if analysis.get('strengths'):
                    response += "**Strengths:**\n"
                    for strength in analysis['strengths'][:5]:
                        response += f"• {strength}\n"
                    response += "\n"
                
                if analysis.get('missing_skills'):
                    response += "**Areas for Development:**\n"
                    for skill in analysis['missing_skills'][:5]:
                        response += f"• {skill}\n"
                
                return response
            
            # If there's an error in agent_results
            if agent_results and 'error' in agent_results:
                return f"I encountered an issue: {agent_results['error']}\n\nCould you please try rephrasing your request?"
            
            # Fallback: Use LLM for general responses (no agent data)
            history = session.get_history_text(n=5)
            context = intent_result.context.copy()
            
            # Simple prompt for non-search responses
            simple_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI recruitment assistant.
                Generate a brief, conversational response.
                
                Conversation history:
                {history}
                
                User's message: {message}
                Intent: {intent}
                
                Keep your response concise and helpful. Ask clarifying questions if needed.
                """),
                ("user", "{message}")
            ])
            
            chain = simple_prompt | self.llm
            response = chain.invoke({
                "message": message,
                "history": history,
                "intent": intent_result.intent.value
            })
            
            return response.content
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I apologize, but I'm having trouble processing your request. Could you please try again?"
    
    def handle_clarification(
        self,
        intent_result: IntentClassificationResult
    ) -> str:
        """
        Generate clarifying questions.
        
        Args:
            intent_result: Intent classification with clarifying questions
            
        Returns:
            Formatted clarification message
        """
        questions = intent_result.clarifying_questions
        
        if not questions:
            questions = [
                "Could you provide more details about what you're looking for?",
                "What specific requirements do you have?"
            ]
        
        response = "I'd like to help you better! To give you the most relevant results, could you tell me:\n\n"
        for i, question in enumerate(questions, 1):
            response += f"{i}. {question}\n"
        
        response += "\nOr feel free to describe your needs in your own words!"
        
        return response
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute conversational interaction.
        
        This is a placeholder - actual conversation handling is done
        through the chat endpoints, not the standard agent workflow.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        start_time = time.time()
        
        try:
            # For now, just log that this was called
            logger.info("ConversationalAgent.execute() called - use chat endpoints instead")
            
            execution_time = int((time.time() - start_time) * 1000)
            trace = self.create_trace(
                reasoning="ConversationalAgent is designed for chat endpoints, not workflow execution",
                tools_called=[],
                output=None,
                execution_time_ms=execution_time
            )
            
            state.agent_traces.append(trace)
            return state
            
        except Exception as e:
            logger.error(f"ConversationalAgent failed: {e}")
            state.error = f"ConversationalAgent: {str(e)}"
            return state
