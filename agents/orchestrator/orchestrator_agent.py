"""Orchestrator Agent for coordinating the flow between agents."""

import logging
from typing import Dict, List, Any, Optional, Callable
import anthropic
import json
import os

from agents.base.base_agent import BaseAgent
from agents.sql_generation.sql_generation_agent import SQLGenerationAgent
from agents.sql_execution.sql_execution_agent import SQLExecutionAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that coordinates other agents."""

    def __init__(
            self, 
            client: anthropic.Anthropic, 
            schema_context: str, 
            db_connection_string: str,
            progress_callback: Optional[Callable] = None
        ):
        """Initialize the orchestrator agent.
        
        Args:
            client: The Anthropic client
            schema_context: Database schema description
            db_connection_string: Database connection string
            progress_callback: Optional callback for progress updates
        """
        super().__init__(
            agent_id="orchestrator",
            agent_name="Orchestrator Agent",
            description="Coordinates the flow between agents"
        )
        self.client = client
        self.schema_context = schema_context
        self.db_connection_string = db_connection_string
        self.progress_callback = progress_callback
        
        # Initialize sub-agents
        self.sql_generation_agent = SQLGenerationAgent(client, schema_context)
        self.sql_execution_agent = SQLExecutionAgent(db_connection_string)
        
        # Initialize conversation history
        self.conversation_history = []
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the user query and coordinate other agents.
        
        Args:
            input_data: Dictionary containing:
                - query: The user's natural language query
                - session_id: Optional session ID
                
        Returns:
            Dictionary containing the final response with SQL and data
        """
        try:
            # Extract input parameters
            user_query = input_data.get("query", "")
            session_id = input_data.get("session_id", "")
            
            # Log the received query
            logger.info(f"Processing query: {user_query}")
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            
            # Report progress
            self._report_progress("start", {"message": "Processing your query..."})
            
            # Step 1: Generate SQL from the query
            self._report_progress("sql_generation", {"message": "Generating SQL query..."})
            
            sql_generation_result = self.sql_generation_agent.process({
                "query": user_query,
                "conversation_history": self.conversation_history
            })
            
            # Check for generation errors
            if sql_generation_result.get("status") != "success":
                logger.error(f"SQL generation failed: {sql_generation_result.get('error')}")
                return {
                    "error": sql_generation_result.get("error", "SQL generation failed"),
                    "status": "error"
                }
            
            # Extract the generated SQL
            sql_query = sql_generation_result.get("sql_query", "")
            
            # Step 2: Execute the SQL query
            self._report_progress("sql_execution", {"message": "Executing SQL query..."})
            
            sql_execution_result = self.sql_execution_agent.process({
                "sql_query": sql_query
            })
            
            # Check for execution errors
            if sql_execution_result.get("status") != "success":
                logger.error(f"SQL execution failed: {sql_execution_result.get('error')}")
                
                # If there's an error, try to regenerate the SQL query with the error feedback
                error_message = sql_execution_result.get("error", "Unknown error")
                self._report_progress("sql_regeneration", {"message": "Fixing SQL query based on error..."})
                
                # Regenerate SQL with error feedback
                sql_regeneration_result = self.sql_generation_agent.process({
                    "query": user_query,
                    "conversation_history": self.conversation_history,
                    "error_feedback": error_message
                })
                
                # Check for regeneration errors
                if sql_regeneration_result.get("status") != "success":
                    logger.error(f"SQL regeneration failed: {sql_regeneration_result.get('error')}")
                    return {
                        "error": sql_regeneration_result.get("error", "SQL regeneration failed"),
                        "status": "error"
                    }
                
                # Extract the regenerated SQL
                regenerated_sql_query = sql_regeneration_result.get("sql_query", "")
                
                # Try to execute the regenerated SQL
                self._report_progress("sql_execution_retry", {"message": "Executing fixed SQL query..."})
                
                sql_execution_result = self.sql_execution_agent.process({
                    "sql_query": regenerated_sql_query
                })
                
                # If the regenerated SQL still fails, return the error
                if sql_execution_result.get("status") != "success":
                    logger.error(f"Regenerated SQL execution failed: {sql_execution_result.get('error')}")
                    return {
                        "error": f"Failed to execute SQL after regeneration: {sql_execution_result.get('error')}",
                        "original_query": user_query,
                        "sql_query": regenerated_sql_query,
                        "status": "error"
                    }
                
                # Update the SQL query if regeneration was successful
                sql_query = regenerated_sql_query
            
            # Step 3: Prepare the final response
            self._report_progress("finishing", {"message": "Preparing results..."})
            
            # Update conversation history with SQL
            self.conversation_history.append({"role": "assistant", "content": sql_query})
            
            # Keep conversation history limited to last 5 exchanges
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            # Prepare the final result
            final_result = {
                "sql_query": sql_query,
                "data": sql_execution_result.get("results", []),
                "column_names": sql_execution_result.get("column_names", []),
                "row_count": sql_execution_result.get("row_count", 0),
                "session_id": session_id,
                "status": "success"
            }
            
            # Report completion
            self._report_progress("complete", {"message": "Query processed successfully"})
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}")
            self._report_progress("error", {"message": f"Error: {str(e)}"})
            return {
                "error": f"Orchestration error: {str(e)}",
                "status": "error"
            }
    
    def _report_progress(self, event_type: str, data: Dict[str, Any]) -> None:
        """Report progress via the callback if available.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        if self.progress_callback:
            try:
                self.progress_callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")

def create_orchestrator(
        db_connection_string: str, 
        progress_callback: Optional[Callable] = None
    ) -> OrchestratorAgent:
    """Create and initialize the orchestrator agent.
    
    Args:
        db_connection_string: Database connection string
        progress_callback: Optional callback for progress updates
        
    Returns:
        Initialized orchestrator agent
    """
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Load schema context
    schema_context = """
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
    
    # Create and return the orchestrator
    return OrchestratorAgent(
        client=client,
        schema_context=schema_context,
        db_connection_string=db_connection_string,
        progress_callback=progress_callback
    ) 