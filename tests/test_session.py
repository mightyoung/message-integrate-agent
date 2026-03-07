"""
Tests for session manager
"""
import pytest

from src.gateway.session import SessionManager, Session


def test_session_creation():
    """Test creating a session."""
    session = Session("sess1", "user1", "telegram")
    assert session.session_id == "sess1"
    assert session.user_id == "user1"
    assert session.platform == "telegram"


def test_session_is_expired():
    """Test session expiration check."""
    from datetime import datetime, timedelta
    session = Session("s1", "u1", "telegram")
    # Set last activity to 1 hour ago
    session.last_activity = datetime.now() - timedelta(hours=1)
    assert session.is_expired(timeout_minutes=30) is True


def test_session_not_expired():
    """Test active session is not expired."""
    session = Session("s1", "u1", "telegram")
    assert session.is_expired(timeout_minutes=30) is False


def test_session_manager_create():
    """Test session manager creates sessions."""
    manager = SessionManager()
    session = manager.create_session("s1", "user1", "telegram")
    assert session is not None
    assert session.session_id == "s1"


def test_session_manager_get():
    """Test getting session by ID."""
    manager = SessionManager()
    manager.create_session("s1", "user1", "telegram")
    session = manager.get_session("s1")
    assert session is not None
    assert session.user_id == "user1"


def test_session_manager_remove():
    """Test removing session."""
    manager = SessionManager()
    manager.create_session("s1", "user1", "telegram")
    manager.remove_session("s1")
    session = manager.get_session("s1")
    assert session is None


def test_session_manager_list():
    """Test listing sessions."""
    manager = SessionManager()
    manager.create_session("s1", "user1", "telegram")
    manager.create_session("s2", "user2", "feishu")
    sessions = manager.list_sessions()
    assert len(sessions) == 2
