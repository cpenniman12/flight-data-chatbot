"""Base agent class to be extended by specific agent types."""

import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the flight data chatbot."""
    
    def __init__(self, agent_id: str, agent_name: str, description: str):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name for the agent
            description: Description of the agent's purpose
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.state = {}  # State dictionary for maintaining memory between calls
        
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data and return a result.
        
        Args:
            input_data: Dictionary containing input parameters
            
        Returns:
            Dictionary containing the processing results
        """
        pass
    
    def update_state(self, key: str, value: Any) -> None:
        """Update the agent's state.
        
        Args:
            key: State variable name
            value: State variable value
        """
        self.state[key] = value
        logger.debug(f"Agent {self.agent_id} updated state: {key}={value}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a value from the agent's state.
        
        Args:
            key: State variable name
            default: Default value if key doesn't exist
            
        Returns:
            The state value or default
        """
        return self.state.get(key, default)
    
    def clear_state(self) -> None:
        """Clear the agent's state."""
        self.state = {}
        logger.debug(f"Agent {self.agent_id} state cleared")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent metadata to dictionary.
        
        Returns:
            Dictionary with agent metadata
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "description": self.description
        } 