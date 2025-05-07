"""SQL Generation Agent for converting natural language to SQL."""

import logging
import anthropic
from typing import Dict, List, Any, Optional

from agents.base.base_agent import BaseAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLGenerationAgent(BaseAgent):
    """Agent for generating SQL queries from natural language."""

    def __init__(self, client: anthropic.Anthropic, schema_context: str):
        """Initialize the SQL generation agent.
        
        Args:
            client: The Anthropic client
            schema_context: Database schema description
        """
        super().__init__(
            agent_id="sql_generation",
            agent_name="SQL Generation Agent",
            description="Converts natural language queries to SQL"
        )
        self.client = client
        self.schema_context = schema_context
        self.generation_history = []  # Store history of generated queries
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a SQL query from natural language.
        
        Args:
            input_data: Dictionary containing:
                - query: The user's natural language query
                - conversation_history: Optional conversation history
                - error_feedback: Optional error feedback from execution
                
        Returns:
            Dictionary containing the SQL query and metadata
        """
        try:
            # Extract input parameters
            user_query = input_data.get("query", "")
            conversation_history = input_data.get("conversation_history", [])
            error_feedback = input_data.get("error_feedback", None)
            
            # Update state
            self.update_state("last_query", user_query)
            
            # Build the prompt with conversation history if available
            conversation_context = ""
            if conversation_history and len(conversation_history) > 0:
                conversation_context = "Previous conversation:\n"
                for msg in conversation_history:
                    if msg["role"] == "user":
                        conversation_context += f"User: {msg['content']}\n"
                    else:
                        conversation_context += f"SQL generated: {msg['content']}\n"
                conversation_context += "\n"
            
            # Add error feedback if available
            error_context = ""
            if error_feedback:
                error_context = f"""
The previous SQL query failed with the following error:
{error_feedback}

Please fix the SQL query to avoid this error.
"""
                # Add to state for future reference
                self.update_state("last_error", error_feedback)
            
            # Create the prompt
            prompt = f"""Given the following database schema:
{self.schema_context}

{conversation_context}
{error_context}
User request: {user_query}

Generate a SQL query that answers the user's request. ONLY return the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.
IMPORTANT RULES:
1. Do not use ROUND() function, use CAST() with decimal type instead: "CAST(number AS decimal(10,2))"
2. Always use single SQL statement only, not multiple statements
3. Never use EXTRACT() function, use date_part() instead
4. All table columns used in the query must be properly listed in the GROUP BY clause
5. Never reference time_hour directly in GROUP BY, extract parts from it first"""

            # Call the Claude model
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                temperature=0,
                system="You are a SQL expert. Generate ONLY the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql_query = response.content[0].text.strip()
            
            # Clean up the SQL query
            sql_query = self._clean_sql_query(sql_query)
            
            # Update generation history
            self.generation_history.append({
                "query": user_query,
                "sql": sql_query,
                "error_feedback": error_feedback
            })
            self.update_state("generation_history", self.generation_history)
            
            # Log the generation
            logger.info(f"Generated SQL: {sql_query}")
            
            return {
                "sql_query": sql_query,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "error": f"Failed to generate SQL: {str(e)}",
                "status": "error"
            }
            
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean and format the SQL query.
        
        Args:
            sql_query: The raw SQL query from the model
            
        Returns:
            Cleaned SQL query
        """
        # Remove any markdown formatting or sql tags if they exist
        if sql_query.startswith("```"):
            sql_query = sql_query.split("\n", 1)[1]
        if sql_query.endswith("```"):
            sql_query = sql_query.rsplit("\n", 1)[0]
        
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Make sure query doesn't have multiple statements
        if ";" in sql_query and not sql_query.endswith(";"):
            sql_query = sql_query.split(";")[0] + ";"
        
        # Replace problematic functions
        sql_query = sql_query.replace("EXTRACT(", "date_part(")
        sql_query = sql_query.replace("ROUND(", "CAST(")
        
        return sql_query 