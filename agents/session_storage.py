"""Session storage for conversations."""
from typing import Dict, List, Any

class SessionStorage:
    """Base class for session storage implementations."""
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a session.
        
        Args:
            session_id: The ID of the session
        
        Returns:
            The conversation history
        """
        raise NotImplementedError("Subclasses must implement get_conversation")
    
    def add_to_conversation(self, session_id: str, entry: Dict[str, Any]) -> None:
        """
        Add an entry to the conversation history.
        
        Args:
            session_id: The ID of the session
            entry: The entry to add
        """
        raise NotImplementedError("Subclasses must implement add_to_conversation")
    
    def clear_conversation(self, session_id: str) -> None:
        """
        Clear the conversation history for a session.
        
        Args:
            session_id: The ID of the session
        """
        raise NotImplementedError("Subclasses must implement clear_conversation")


class MemorySessionStorage(SessionStorage):
    """In-memory implementation of session storage."""
    
    def __init__(self):
        """Initialize the memory session storage."""
        self.conversations = {}
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a session.
        
        Args:
            session_id: The ID of the session
        
        Returns:
            The conversation history
        """
        return self.conversations.get(session_id, [])
    
    def add_to_conversation(self, session_id: str, entry: Dict[str, Any]) -> None:
        """
        Add an entry to the conversation history.
        
        Args:
            session_id: The ID of the session
            entry: The entry to add
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append(entry)
    
    def clear_conversation(self, session_id: str) -> None:
        """
        Clear the conversation history for a session.
        
        Args:
            session_id: The ID of the session
        """
        if session_id in self.conversations:
            del self.conversations[session_id] 