"""
Agent API

This module provides an API for using the agentic architecture in the flight data chatbot.
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List

import anthropic

from agents import OrchestratorAgent
from tools import (
    SQLGenerationTool,
    SQLExecutionTool,
    VisualizationTool,
    QuestionGenerationTool
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Get API key from environment variable
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY environment variable not set")

class AgentAPI:
    """API for using the agentic architecture."""
    
    def __init__(self, db_path: str = "nycflights13.db"):
        """
        Initialize the AgentAPI.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.db_path = db_path
        
        # Initialize tools
        self.sql_generation_tool = SQLGenerationTool(self.client)
        self.sql_execution_tool = SQLExecutionTool(self.db_path)
        self.visualization_tool = VisualizationTool(self.client)
        self.question_generation_tool = QuestionGenerationTool(self.client)
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            client=self.client,
            tools=[
                self.sql_generation_tool,
                self.sql_execution_tool,
                self.visualization_tool,
                self.question_generation_tool
            ]
        )
        
        self.session_id = None
        self.conversation_history = []
        
    async def process_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process a user query.
        
        Args:
            query: The user query
            session_id: Optional session ID for maintaining conversation history
            
        Returns:
            Response from the orchestrator
        """
        # Set or update session ID
        if session_id:
            self.session_id = session_id
        elif not self.session_id:
            self.session_id = f"session_{hash(query + str(asyncio.get_event_loop().time()))}"
        
        # Create message for orchestrator
        message = {
            "role": "user",
            "content": query,
            "session_id": self.session_id
        }
        
        # Process message with orchestrator
        logger.info(f"Processing query: {query}")
        response = await self.orchestrator.process(message)
        
        # Add follow-up questions
        response = await self._add_follow_up_questions(query, response)
        
        return response
    
    async def _add_follow_up_questions(self, query: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add follow-up questions to the response.
        
        Args:
            query: The user query
            response: The response from the orchestrator
            
        Returns:
            Response with follow-up questions added
        """
        # Check if we have tool results with SQL execution
        tool_results = response.get("tool_results", [])
        sql_result = None
        
        for result in tool_results:
            if result.get("tool") == "execute_sql" and result.get("result", {}).get("status") in ["success", "success_with_fallback"]:
                sql_result = result.get("result", {})
                break
        
        # If no SQL result, return the original response
        if not sql_result:
            return response
        
        # Generate follow-up questions
        try:
            follow_up_result = await self.question_generation_tool.execute(
                current_query=query,
                results=sql_result.get("results", [])[:20],  # Limit to avoid token overflow
                columns=sql_result.get("columns", []),
                conversation_history=self.orchestrator.get_history()[-6:]  # Last 3 exchanges
            )
            
            # Add questions to response
            if follow_up_result.get("status") in ["success", "fallback"]:
                response["follow_up_questions"] = follow_up_result.get("questions", [])
            
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
        
        return response
    
    def clear_history(self):
        """Clear the conversation history."""
        self.orchestrator.clear_history()
        self.conversation_history = []

async def example_usage():
    """Example usage of the AgentAPI."""
    # Set API key from environment variable
    os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"
    
    # Initialize the API
    api = AgentAPI()
    
    # Process a query
    response = await api.process_query("Show me the top 5 airlines by number of flights")
    
    # Print the response
    print(json.dumps(response, indent=2))
    
    # Process another query in the same session
    response = await api.process_query("Which airports have the most delays?")
    
    # Print the response
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage()) 