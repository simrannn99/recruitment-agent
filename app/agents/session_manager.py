"""
Session manager for conversation sessions.

Handles session storage, retrieval, and lifecycle management using Redis.
"""

import json
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using in-memory session storage")

from app.agents.conversation_state import ConversationSession, ConversationMessage

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversation sessions with Redis backend.
    Falls back to in-memory storage if Redis is unavailable.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl_hours: int = 24):
        """
        Initialize session manager.
        
        Args:
            redis_url: Redis connection URL
            ttl_hours: Session TTL in hours (default: 24)
        """
        self.ttl_seconds = ttl_hours * 3600
        self._in_memory_store: Dict[str, ConversationSession] = {}
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"✓ SessionManager initialized with Redis (TTL: {ttl_hours}h)")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
                self.use_redis = False
                self.redis_client = None
        else:
            self.use_redis = False
            self.redis_client = None
            logger.info("SessionManager using in-memory storage")
    
    def create_session(self, user_id: Optional[str] = None) -> ConversationSession:
        """
        Create a new conversation session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            New ConversationSession
        """
        session_id = str(uuid.uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id
        )
        
        self.save_session(session)
        logger.info(f"Created new session: {session_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationSession if found, None otherwise
        """
        try:
            if self.use_redis:
                data = self.redis_client.get(f"session:{session_id}")
                if data:
                    session_dict = json.loads(data)
                    return ConversationSession.from_dict(session_dict)
            else:
                return self._in_memory_store.get(session_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None
    
    def save_session(self, session: ConversationSession) -> bool:
        """
        Save a session.
        
        Args:
            session: ConversationSession to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_redis:
                session_data = json.dumps(session.to_dict())
                self.redis_client.setex(
                    f"session:{session.session_id}",
                    self.ttl_seconds,
                    session_data
                )
            else:
                self._in_memory_store[session.session_id] = session
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_redis:
                self.redis_client.delete(f"session:{session_id}")
            else:
                self._in_memory_store.pop(session_id, None)
            
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def extend_session(self, session_id: str) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_redis:
                self.redis_client.expire(f"session:{session_id}", self.ttl_seconds)
                return True
            else:
                # In-memory sessions don't expire
                return session_id in self._in_memory_store
            
        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False
    
    def list_active_sessions(self, user_id: Optional[str] = None) -> list[str]:
        """
        List active session IDs, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of session IDs
        """
        try:
            if self.use_redis:
                pattern = "session:*"
                session_keys = self.redis_client.keys(pattern)
                session_ids = [key.replace("session:", "") for key in session_keys]
                
                if user_id:
                    # Filter by user_id (requires loading each session)
                    filtered_ids = []
                    for sid in session_ids:
                        session = self.get_session(sid)
                        if session and session.user_id == user_id:
                            filtered_ids.append(sid)
                    return filtered_ids
                
                return session_ids
            else:
                sessions = list(self._in_memory_store.keys())
                if user_id:
                    return [
                        sid for sid, session in self._in_memory_store.items()
                        if session.user_id == user_id
                    ]
                return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (only for in-memory storage).
        Redis handles expiration automatically.
        
        Returns:
            Number of sessions cleaned up
        """
        if self.use_redis:
            return 0  # Redis handles expiration
        
        # Clean up sessions older than TTL
        cutoff_time = datetime.now() - timedelta(seconds=self.ttl_seconds)
        expired = [
            sid for sid, session in self._in_memory_store.items()
            if session.last_message_at < cutoff_time
        ]
        
        for sid in expired:
            del self._in_memory_store[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
