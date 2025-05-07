"""Tools for agents to interact with."""
from typing import Any, Callable, Dict, List, Optional


class Tool:
    """A tool that can be used by an agent."""

    def __init__(
        self,
        tool_id: str,
        description: str,
        run: Callable,
    ):
        """Initialize the tool.
        
        Args:
            tool_id: The ID of the tool
            description: A description of what the tool does
            run: The function to run when the tool is invoked
        """
        self.tool_id = tool_id
        self.description = description
        self.run = run 