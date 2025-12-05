"""
Conversation state management for multi-turn dialogue.

Handles session tracking, context management, and conversation history.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ConversationIntent(str, Enum):
    """Possible user intents in conversation."""
    JOB_SEARCH = "job_search"
    CANDIDATE_ANALYSIS = "candidate_analysis"
    CLARIFICATION_NEEDED = "clarification_needed"
    GENERAL_QUERY = "general_query"
    CONVERSATION_END = "conversation_end"


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[ConversationIntent] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'intent': self.intent.value if self.intent else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            intent=ConversationIntent(data['intent']) if data.get('intent') else None,
            metadata=data.get('metadata', {})
        )


@dataclass
class ConversationContext:
    """Extracted context from conversation."""
    job_requirements: Dict[str, Any] = field(default_factory=dict)
    candidate_ids: List[int] = field(default_factory=list)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    current_focus: Optional[str] = None  # What the user is currently asking about
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_requirements': self.job_requirements,
            'candidate_ids': self.candidate_ids,
            'search_results': self.search_results,
            'preferences': self.preferences,
            'current_focus': self.current_focus
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary."""
        return cls(
            job_requirements=data.get('job_requirements', {}),
            candidate_ids=data.get('candidate_ids', []),
            search_results=data.get('search_results', []),
            preferences=data.get('preferences', {}),
            current_focus=data.get('current_focus')
        )
    
    def update(self, new_context: Dict[str, Any]) -> None:
        """Update context with new information."""
        if 'job_requirements' in new_context:
            self.job_requirements.update(new_context['job_requirements'])
        if 'candidate_ids' in new_context:
            self.candidate_ids.extend(new_context['candidate_ids'])
        if 'search_results' in new_context:
            self.search_results = new_context['search_results']
        if 'preferences' in new_context:
            self.preferences.update(new_context['preferences'])
        if 'current_focus' in new_context:
            self.current_focus = new_context['current_focus']


@dataclass
class ConversationSession:
    """Represents a conversation session."""
    session_id: str
    user_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    messages: List[ConversationMessage] = field(default_factory=list)
    context: ConversationContext = field(default_factory=ConversationContext)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.message_count += 1
        self.last_message_at = datetime.now()
    
    def get_recent_messages(self, n: int = 10) -> List[ConversationMessage]:
        """Get the n most recent messages."""
        return self.messages[-n:]
    
    def get_history_text(self, n: int = 10) -> str:
        """Get conversation history as formatted text."""
        recent = self.get_recent_messages(n)
        return "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in recent
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'started_at': self.started_at.isoformat(),
            'last_message_at': self.last_message_at.isoformat(),
            'message_count': self.message_count,
            'messages': [msg.to_dict() for msg in self.messages],
            'context': self.context.to_dict(),
            'is_active': self.is_active,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create from dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            started_at=datetime.fromisoformat(data['started_at']),
            last_message_at=datetime.fromisoformat(data['last_message_at']),
            message_count=data['message_count'],
            messages=[ConversationMessage.from_dict(m) for m in data.get('messages', [])],
            context=ConversationContext.from_dict(data.get('context', {})),
            is_active=data.get('is_active', True),
            metadata=data.get('metadata', {})
        )


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""
    intent: ConversationIntent
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    needs_clarification: bool = False
    clarifying_questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'intent': self.intent.value,
            'confidence': self.confidence,
            'context': self.context,
            'needs_clarification': self.needs_clarification,
            'clarifying_questions': self.clarifying_questions
        }
