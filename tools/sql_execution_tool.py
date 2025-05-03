"""
SQL Execution Tool

This module implements a tool that executes SQL queries against the database.
"""

import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional
import pandas as pd

from tools.base_tool import BaseTool, ToolParameter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class SQLExecutionTool(BaseTool):
    """Tool for executing SQL queries against the database."""

    def __init__(self, db_path: str = "nycflights13.db"):
        """
        Initialize the SQLExecutionTool.
        
        Args:
            db_path: Path to the SQLite database file
        """
        super().__init__(
            name="execute_sql",
            description="Executes SQL queries against the NYC flights database",
            parameters=[
                ToolParameter(
                    name="sql_query",
                    description="The SQL query to execute",
                    param_type="string",
                    required=True
                ),
                ToolParameter(
                    name="fallback_query",
                    description="A simpler fallback query if the main query fails",
                    param_type="string",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="max_rows",
                    description="Maximum number of rows to return in the result",
                    param_type="integer",
                    required=False,
                    default=100
                )
            ]
        )
        self.db_path = db_path
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the SQL query tool.
        
        Args:
            **kwargs: The parameters for the tool
                - sql_query: The SQL query to execute
                - fallback_query: Optional simpler fallback query
                - max_rows: Maximum number of rows to return
                
        Returns:
            A dictionary with the query results or error message
        """
        # Validate parameters
        params = self.validate_parameters(kwargs)
        sql_query = params["sql_query"]
        fallback_query = params.get("fallback_query", "")
        max_rows = params.get("max_rows", 100)
        
        # Check if the database file exists
        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found at {self.db_path}")
            return {
                "error": f"Database file not found at {self.db_path}",
                "status": "error"
            }
        
        # Try executing the SQL query
        try:
            # Connect to database
            logger.info(f"Connecting to database at {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            
            # Execute query
            logger.info(f"Executing SQL query: {sql_query}")
            df = pd.read_sql_query(sql_query, conn, params={})
            
            # Close connection
            conn.close()
            
            # Calculate total number of rows before limiting
            total_rows = len(df)
            
            # Limit number of rows returned
            if len(df) > max_rows:
                df = df.head(max_rows)
            
            # Convert to dictionary for JSON serialization
            results = df.to_dict(orient="records")
            
            # Get column names and types
            columns = [
                {"name": col, "type": str(df[col].dtype)} 
                for col in df.columns
            ]
            
            return {
                "results": results,
                "columns": columns,
                "total_rows": total_rows,
                "displayed_rows": len(results),
                "status": "success"
            }
            
        except Exception as primary_error:
            logger.error(f"Error executing primary SQL query: {str(primary_error)}")
            
            # Try fallback query if provided
            if fallback_query:
                try:
                    logger.info(f"Attempting fallback query: {fallback_query}")
                    conn = sqlite3.connect(self.db_path)
                    df = pd.read_sql_query(fallback_query, conn, params={})
                    conn.close()
                    
                    total_rows = len(df)
                    if len(df) > max_rows:
                        df = df.head(max_rows)
                    
                    results = df.to_dict(orient="records")
                    columns = [
                        {"name": col, "type": str(df[col].dtype)}
                        for col in df.columns
                    ]
                    
                    return {
                        "results": results,
                        "columns": columns,
                        "total_rows": total_rows,
                        "displayed_rows": len(results),
                        "fallback_used": True,
                        "primary_error": str(primary_error),
                        "status": "success_with_fallback"
                    }
                
                except Exception as fallback_error:
                    logger.error(f"Error executing fallback SQL query: {str(fallback_error)}")
                    return {
                        "error": f"Primary query failed: {str(primary_error)}\nFallback query failed: {str(fallback_error)}",
                        "status": "error"
                    }
            
            return {
                "error": f"SQL execution failed: {str(primary_error)}",
                "status": "error"
            } 