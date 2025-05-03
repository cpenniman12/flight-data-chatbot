"""
Base Agent Module

This module defines the BaseAgent class that all specialized agents will inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(self, name: str, description: str):
        """
        Initialize a new BaseAgent.

        Args:
            name: The name of the agent
            description: A description of what the agent does
        """
        self.name = name
        self.description = description
        self.conversation_history = []

    @abstractmethod
    async def process(self, message: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message and return a response.

        Args:
            message: The input message to process
            context: Optional context information

        Returns:
            The agent's response
        """
        pass

    def add_to_history(self, message: Dict[str, Any]):
        """
        Add a message to the conversation history.

        Args:
            message: The message to add to history
        """
        self.conversation_history.append(message)
        # Keep only the most recent messages to avoid context overflow
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.

        Returns:
            The conversation history
        """
        return self.conversation_history

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.name}: {self.description}" 