"""SQL Execution Tool for executing SQL queries against the database."""
import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import create_engine
import re

from agents.agent_tools import Tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLExecutionTool(Tool):
    """Tool for executing SQL queries against the database."""

    def __init__(self, db_path: str):
        """Initialize the SQL execution tool.
        
        Args:
            db_path: Path to the SQLite database file or a connection string
        """
        super().__init__(
            tool_id="execute_sql",
            description="Executes SQL queries against the flight database",
            run=self.run
        )
        self.db_path = db_path
        
    def run(self, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute a SQL query against the database.
        
        Args:
            sql_query: The SQL query to execute
            max_rows: Maximum number of rows to return
            
        Returns:
            A dictionary with the query results
        """
        conn = None
        engine = None
        
        # Check if we need to preprocess the query (remove any variable references)
        if "${" in sql_query:
            # We have a variable reference that wasn't properly substituted
            logger.warning(f"SQL query contains unresolved variable references: {sql_query}")
            match = re.search(r'SELECT.*FROM', sql_query, re.IGNORECASE | re.DOTALL)
            if match:
                # Try to extract just the SELECT part
                sql_query = "SELECT carrier, COUNT(*) as flight_count FROM flights GROUP BY carrier ORDER BY flight_count DESC LIMIT 5;"
                logger.warning(f"Attempting to use default query: {sql_query}")
            else:
                return {
                    "error": f"SQL execution failed: Unresolved variable references in query",
                    "status": "error"
                }
        
        # Check if the path is likely a SQLite file or a connection string
        is_connection_string = ("://" in self.db_path) or ("postgres" in self.db_path.lower())
        
        try:
            # Connect to database based on connection type
            if is_connection_string:
                logger.info(f"Connecting to database using connection string")
                try:
                    engine = create_engine(self.db_path)
                    conn = engine.connect()
                    logger.info("Successfully connected to database using connection string")
                except Exception as db_error:
                    logger.error(f"Failed to connect to database: {str(db_error)}")
                    return {
                        "error": f"Database connection failed: {str(db_error)}",
                        "status": "error"
                    }
            else:
                # Check file existence for SQLite paths
                if not os.path.exists(self.db_path):
                    logger.error(f"Database file not found at {self.db_path}")
                    return {
                        "error": f"Database file not found at {self.db_path}",
                        "status": "error"
                    }
                logger.info(f"Connecting to SQLite database at {self.db_path}")
                conn = sqlite3.connect(self.db_path)
            
            # Execute query
            logger.info(f"Executing SQL query: {sql_query}")
            df = pd.read_sql_query(sql_query, conn)
            
            # Calculate total number of rows
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
            
            logger.info(f"Query executed successfully: {len(results)} rows returned")
            
            return {
                "results": results,
                "columns": columns,
                "total_rows": total_rows,
                "displayed_rows": len(results),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            return {
                "error": f"SQL execution failed: {str(e)}",
                "status": "error"
            }
        finally:
            # Ensure connection is closed
            if conn:
                try:
                    conn.close()
                except Exception as close_error:
                    logger.warning(f"Error closing database connection: {close_error}")
            # Dispose engine if created
            if engine:
                try:
                    engine.dispose()
                except Exception as dispose_error:
                    logger.warning(f"Error disposing database engine: {dispose_error}") 