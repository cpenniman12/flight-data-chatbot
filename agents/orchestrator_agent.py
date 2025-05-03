"""
Orchestrator Agent Module

This module implements the OrchestratorAgent that coordinates interactions
between specialized agents and tools.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple

import anthropic

from agents.base_agent import BaseAgent
from tools.base_tool import BaseTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating the workflow between specialized agents and tools.
    
    The orchestrator determines which tools to use based on the user's query and
    manages the execution flow between them.
    """

    def __init__(self, client: anthropic.Anthropic, tools: List[BaseTool] = None):
        """
        Initialize the OrchestratorAgent.
        
        Args:
            client: The Anthropic client
            tools: List of available tools
        """
        super().__init__(
            name="Orchestrator",
            description="Coordinates workflow between specialized agents and tools"
        )
        self.client = client
        self.tools = tools or []
        self.tool_registry = {tool.name: tool for tool in self.tools}
        self.execution_history = []
        
    async def process(self, message: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message to determine and execute the appropriate tools.
        
        Args:
            message: The user message
            context: Optional context information
            
        Returns:
            The final response
        """
        user_query = message.get("content", "")
        if not user_query:
            return {"error": "No user query provided"}
            
        # Add user message to history
        self.add_to_history({"role": "user", "content": user_query})
        
        # Determine which tools to use
        tools_to_use = await self._plan_tools(user_query, context)
        logger.info(f"Planned tools: {[tool['name'] for tool in tools_to_use]}")
        
        # Execute tools in sequence
        results = []
        for tool_info in tools_to_use:
            tool_name = tool_info["name"]
            tool_params = tool_info.get("parameters", {})
            
            if tool_name not in self.tool_registry:
                logger.warning(f"Tool not found: {tool_name}")
                continue
                
            tool = self.tool_registry[tool_name]
            
            try:
                # Record the tool execution start
                execution_record = {
                    "tool": tool_name,
                    "parameters": tool_params,
                    "status": "started"
                }
                self.execution_history.append(execution_record)
                
                # Execute the tool
                result = await tool.execute(**tool_params)
                
                # Update execution record
                execution_record["status"] = "completed"
                execution_record["result"] = result
                
                results.append({
                    "tool": tool_name,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {str(e)}")
                execution_record["status"] = "failed"
                execution_record["error"] = str(e)
                
                results.append({
                    "tool": tool_name,
                    "error": str(e)
                })
        
        # Generate final response based on tool results
        final_response = await self._generate_response(user_query, results, context)
        
        # Add response to history
        self.add_to_history({"role": "assistant", "content": final_response["content"]})
        
        return final_response
    
    async def _plan_tools(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Determine which tools to use based on the user query.
        
        Args:
            query: The user query
            context: Optional context information
            
        Returns:
            List of tools to use with their parameters
        """
        # Get tools schema for the model
        tools_schema = [tool.get_schema() for tool in self.tools]
        
        # Create the prompt for the model
        history_text = ""
        if self.conversation_history:
            for msg in self.conversation_history:
                role = msg["role"]
                content = msg["content"]
                history_text += f"{role.capitalize()}: {content}\n\n"
        
        prompt = f"""You are an orchestrator that plans which tools to use based on a user query.
Given the following tools:

{json.dumps(tools_schema, indent=2)}

And the following conversation history:
{history_text}

User query: {query}

Determine which tools to use and in what order. Return a JSON array of tool invocations.
Each tool invocation should include the tool name and parameters.

For example:
[
  {{
    "name": "generate_sql",
    "parameters": {{
      "query": "Show me top 5 airlines"
    }}
  }},
  {{
    "name": "execute_sql",
    "parameters": {{
      "sql_query": "<SQL from previous step>"
    }}
  }}
]

Only include tools that are necessary to answer the query. Be specific with parameter values.
"""

        # Call the Claude model to determine the tools
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0,
            system="You plan which tools to use based on a user query. Always return a valid JSON array.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract and parse JSON response
        try:
            content = response.content[0].text
            # Find JSON array in response if there's any text around it
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Error parsing tools to use: {str(e)}")
            return []
    
    async def _generate_response(self, query: str, results: List[Dict[str, Any]], 
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a final response based on the tool results.
        
        Args:
            query: The original user query
            results: Results from tool executions
            context: Optional context information
            
        Returns:
            The final response
        """
        # Create a summary of the tool results
        results_summary = ""
        for result in results:
            tool_name = result.get("tool", "")
            if "error" in result:
                results_summary += f"{tool_name}: Error - {result['error']}\n"
            else:
                result_data = result.get("result", {})
                # Truncate large results
                result_str = json.dumps(result_data)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "... [truncated]"
                results_summary += f"{tool_name}: {result_str}\n"
        
        # Create the prompt for the model
        prompt = f"""You are an AI assistant helping with flight data analysis.
User query: {query}

I executed the following tools to answer this query:
{results_summary}

Based on these results, provide a helpful, concise response to the user's query.
Focus on the key insights and results. If there were errors, explain what went wrong.
"""

        # Call the Claude model to generate the response
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.2,
            system="You are a helpful assistant responding to questions about flight data.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            "content": response.content[0].text,
            "tool_results": results
        }
    
    def register_tool(self, tool: BaseTool):
        """
        Register a new tool with the orchestrator.
        
        Args:
            tool: The tool to register
        """
        self.tools.append(tool)
        self.tool_registry[tool.name] = tool
        
    def unregister_tool(self, tool_name: str):
        """
        Unregister a tool from the orchestrator.
        
        Args:
            tool_name: The name of the tool to unregister
        """
        if tool_name in self.tool_registry:
            tool = self.tool_registry[tool_name]
            self.tools.remove(tool)
            del self.tool_registry[tool_name]
            
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get the history of tool executions.
        
        Returns:
            The execution history
        """
        return self.execution_history 