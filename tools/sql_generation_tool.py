"""
SQL Generation Tool

This module implements a tool that generates SQL queries from natural language.
"""

import logging
from typing import Dict, Any, List, Optional

import anthropic

from tools.base_tool import BaseTool, ToolParameter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class SQLGenerationTool(BaseTool):
    """Tool for generating SQL queries from natural language."""

    SCHEMA_CONTEXT = """
The database contains the following tables:

1. airlines
   - carrier (text): Two letter carrier code
   - name (text): Full carrier name

2. airports
   - faa (text): FAA airport code
   - name (text): Airport name
   - lat (float): Latitude
   - lon (float): Longitude
   - alt (int): Altitude
   - tz (int): Timezone offset
   - dst (text): Daylight savings time zone
   - tzone (text): IANA time zone

3. planes
   - tailnum (text): Tail number
   - year (int): Year manufactured
   - type (text): Type of aircraft
   - manufacturer (text): Manufacturer
   - model (text): Model
   - engines (int): Number of engines
   - seats (int): Number of seats
   - speed (int): Average cruising speed
   - engine (text): Engine type

4. weather
   - origin (text): Weather station (FAA code)
   - year (int): Year
   - month (int): Month
   - day (int): Day
   - hour (int): Hour
   - temp (float): Temperature (F)
   - dewp (float): Dew point (F)
   - humid (float): Humidity
   - wind_dir (int): Wind direction
   - wind_speed (float): Wind speed
   - wind_gust (float): Wind gust
   - precip (float): Precipitation
   - pressure (float): Pressure
   - visib (float): Visibility
   - time_hour (timestamp): Date and hour

5. flights
   - year (int): Year
   - month (int): Month
   - day (int): Day
   - dep_time (int): Departure time
   - sched_dep_time (int): Scheduled departure time
   - dep_delay (float): Departure delay
   - arr_time (int): Arrival time
   - sched_arr_time (int): Scheduled arrival time
   - arr_delay (float): Arrival delay
   - carrier (text): Carrier code
   - flight (int): Flight number
   - tailnum (text): Tail number
   - origin (text): Origin airport
   - dest (text): Destination airport
   - air_time (float): Air time
   - distance (float): Distance
   - hour (int): Hour
   - minute (int): Minute
   - time_hour (timestamp): Date and hour
"""

    def __init__(self, client: anthropic.Anthropic):
        """
        Initialize the SQLGenerationTool.
        
        Args:
            client: The Anthropic client
        """
        super().__init__(
            name="generate_sql",
            description="Generates SQL queries from natural language",
            parameters=[
                ToolParameter(
                    name="query",
                    description="The natural language query to convert to SQL",
                    param_type="string",
                    required=True
                ),
                ToolParameter(
                    name="conversation_history",
                    description="Previous conversation for context",
                    param_type="array",
                    required=False,
                    default=[]
                )
            ]
        )
        self.client = client
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the SQL generation tool.
        
        Args:
            **kwargs: The parameters for the tool
                - query: The natural language query to convert to SQL
                - conversation_history: Optional conversation history
                
        Returns:
            A dictionary with the generated SQL query
        """
        # Validate parameters
        params = self.validate_parameters(kwargs)
        user_query = params["query"]
        conversation_history = params.get("conversation_history", [])
        
        # Build the prompt with conversation history
        conversation_context = ""
        if conversation_history:
            conversation_context = "Previous conversation:\n"
            for msg in conversation_history:
                if msg.get("role") == "user":
                    conversation_context += f"User: {msg.get('content')}\n"
                else:
                    conversation_context += f"SQL generated: {msg.get('content')}\n"
            conversation_context += "\n"
        
        # Create the prompt
        prompt = f"""Given the following database schema:
{self.SCHEMA_CONTEXT}

{conversation_context}
User request: {user_query}

Generate a SQL query that answers the user's request. ONLY return the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.
IMPORTANT RULES:
1. Do not use ROUND() function, use CAST() with decimal type instead: "CAST(number AS decimal(10,2))"
2. Always use single SQL statement only, not multiple statements
3. Never use EXTRACT() function, use date_part() instead
4. All table columns used in the query must be properly listed in the GROUP BY clause
5. Never reference time_hour directly in GROUP BY, extract parts from it first"""

        # Call the Claude model
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                temperature=0,
                system="You are a SQL expert. Generate ONLY the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql_query = response.content[0].text.strip()
            
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
            
            return {
                "sql_query": sql_query,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}")
            return {
                "error": f"Failed to generate SQL: {str(e)}",
                "status": "error"
            } 