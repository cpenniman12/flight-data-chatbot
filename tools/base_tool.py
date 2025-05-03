"""
Base Tool Module

This module defines the BaseTool class that all tools will inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class ToolParameter:
    """Defines a parameter for a tool."""

    def __init__(self, name: str, description: str, param_type: str, required: bool = True, default=None):
        """
        Initialize a new ToolParameter.

        Args:
            name: The name of the parameter
            description: Description of the parameter
            param_type: The type of the parameter (string, integer, boolean, etc.)
            required: Whether the parameter is required
            default: Default value for the parameter if not provided
        """
        self.name = name
        self.description = description
        self.param_type = param_type
        self.required = required
        self.default = default

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the parameter to a dictionary.

        Returns:
            Dictionary representation of the parameter
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.param_type,
            "required": self.required,
            "default": self.default
        }


class BaseTool(ABC):
    """Base class for all tools in the system."""

    def __init__(self, name: str, description: str, parameters: List[ToolParameter] = None):
        """
        Initialize a new BaseTool.

        Args:
            name: The name of the tool
            description: A description of what the tool does
            parameters: List of parameters the tool accepts
        """
        self.name = name
        self.description = description
        self.parameters = parameters or []

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with the provided parameters.

        Args:
            **kwargs: The parameters for the tool

        Returns:
            The result of executing the tool
        """
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the provided parameters meet the requirements.

        Args:
            parameters: The parameters to validate

        Returns:
            Validated and possibly modified parameters
            
        Raises:
            ValueError: If a required parameter is missing or of incorrect type
        """
        validated = {}
        
        for param in self.parameters:
            if param.name not in parameters:
                if param.required:
                    raise ValueError(f"Missing required parameter: {param.name}")
                if param.default is not None:
                    validated[param.name] = param.default
                continue
                
            value = parameters[param.name]
            # Type validation could be expanded here
            validated[param.name] = value
            
        return validated

    def get_schema(self) -> Dict[str, Any]:
        """
        Get the schema for this tool.

        Returns:
            A dictionary describing the tool
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [param.to_dict() for param in self.parameters]
        }

    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.name}: {self.description}" 