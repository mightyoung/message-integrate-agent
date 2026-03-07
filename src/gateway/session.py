"""
Session management for gateway
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger


class Session:
    """Represents a user session."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        platform: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.platform = platform
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.context: Dict[str, Any] = {}

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired."""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


class SessionManager:
    """Manages user sessions."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def create_session(
        self,
        session_id: str,
        user_id: str,
        platform: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a new session."""
        session = Session(session_id, user_id, platform, metadata)
        self.sessions[session_id] = session
        logger.info(f"Session created: {session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session removed: {session_id}")

    def update_session_context(self, session_id: str, key: str, value: Any):
        """Update session context."""
        session = self.get_session(session_id)
        if session:
            session.context[key] = value
            session.update_activity()

    def get_session_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get session context value."""
        session = self.get_session(session_id)
        if session:
            return session.context.get(key, default)
        return default

    def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """Remove expired sessions."""
        expired = [
            sid
            for sid, session in self.sessions.items()
            if session.is_expired(timeout_minutes)
        ]
        for sid in expired:
            self.remove_session(sid)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "platform": s.platform,
                "created_at": s.created_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
            }
            for s in self.sessions.values()
        ]
