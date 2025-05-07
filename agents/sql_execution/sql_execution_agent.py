"""SQL Execution Agent for executing SQL queries against the database."""

import logging
import os
import pandas as pd
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
import traceback

from agents.base.base_agent import BaseAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLExecutionAgent(BaseAgent):
    """Agent for executing SQL queries against the database."""

    def __init__(self, db_connection_string: str):
        """Initialize the SQL execution agent.
        
        Args:
            db_connection_string: Database connection string
        """
        super().__init__(
            agent_id="sql_execution",
            agent_name="SQL Execution Agent",
            description="Executes SQL queries against the database"
        )
        self.db_connection_string = db_connection_string
        self.engine = create_engine(db_connection_string)
        self.execution_history = []  # Store history of executed queries
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a SQL query against the database.
        
        Args:
            input_data: Dictionary containing:
                - sql_query: The SQL query to execute
                
        Returns:
            Dictionary containing the execution results or error
        """
        try:
            # Extract the SQL query from input data
            sql_query = input_data.get("sql_query", "")
            if not sql_query:
                return {
                    "error": "No SQL query provided",
                    "status": "error"
                }
            
            # Update state with the SQL query
            self.update_state("last_query", sql_query)
            
            # Execute the SQL query
            logger.info(f"Executing SQL: {sql_query}")
            try:
                df = self._execute_query(sql_query)
                
                # Convert to records for JSON serialization
                result_data = df.head(100).to_dict(orient='records') if len(df) > 100 else df.to_dict(orient='records')
                
                # Update execution history
                self.execution_history.append({
                    "sql": sql_query,
                    "success": True,
                    "result_count": len(df)
                })
                self.update_state("execution_history", self.execution_history)
                
                return {
                    "results": result_data,
                    "column_names": df.columns.tolist(),
                    "row_count": len(df),
                    "status": "success"
                }
                
            except Exception as exec_error:
                # Log the error
                error_message = str(exec_error)
                error_traceback = traceback.format_exc()
                logger.error(f"SQL execution error: {error_message}\n{error_traceback}")
                
                # Update execution history
                self.execution_history.append({
                    "sql": sql_query,
                    "success": False,
                    "error": error_message
                })
                self.update_state("execution_history", self.execution_history)
                self.update_state("last_error", error_message)
                
                return {
                    "error": error_message,
                    "status": "error"
                }
                
        except Exception as e:
            logger.error(f"Error in SQL execution agent: {str(e)}")
            return {
                "error": f"Failed to process SQL execution: {str(e)}",
                "status": "error"
            }
            
    def _execute_query(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            DataFrame containing query results
        """
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql_query), conn)
            
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get the schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table schema information
        """
        try:
            schema_query = f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            """
            with self.engine.connect() as conn:
                df = pd.read_sql(text(schema_query), conn)
                return {
                    "table_name": table_name,
                    "columns": df.to_dict(orient='records'),
                    "status": "success"
                }
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {str(e)}")
            return {
                "error": f"Failed to get schema: {str(e)}",
                "status": "error"
            } 