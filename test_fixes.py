import os
import json
import logging
from dotenv import load_dotenv
import anthropic

from agents.orchestrator_agent import create_orchestrator, OrchestratorAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_visualizations():
    """Test visualizations with direct SQL execution"""
    
    # Use PostgreSQL connection with the correct username and database
    db_path = 'postgresql://cooperpenniman@localhost:5432/nycflights'
    logger.info(f"Using database connection: {db_path}")
    
    # Set up a simple progress callback
    def progress_callback(event_type, data):
        message = data.get("message", "")
        logger.info(f"Progress event: {event_type} - {message}")
    
    # Create orchestrator
    try:
        orchestrator = create_orchestrator(db_path, progress_callback)
        logger.info("Successfully created orchestrator")
        
        # Test a pre-defined sequence of tools with fixed parameters
        session_id = "test_session"
        tool_results = []
        
        # Step 1: Generate SQL
        sql_generation_tool = next((t for t in orchestrator.tools if t.tool_id == "generate_sql"), None)
        if sql_generation_tool:
            sql_result = sql_generation_tool.run(query="Show me the number of flights by month")
            tool_results.append({"tool": "generate_sql", "result": sql_result})
            logger.info(f"Generated SQL: {sql_result}")
        
        # Step 2: Execute SQL with correct columns
        sql_execution_tool = next((t for t in orchestrator.tools if t.tool_id == "execute_sql"), None)
        if sql_execution_tool:
            # Use the actual column names from the flights table
            sql_query = """
            SELECT month, COUNT(*) AS num_flights
            FROM flights
            GROUP BY month
            ORDER BY month
            """
            sql_result = sql_execution_tool.run(sql_query=sql_query)
            tool_results.append({"tool": "execute_sql", "result": sql_result})
            logger.info(f"SQL execution result: {sql_result}")
        
        # Step 3: Generate Visualization
        visualization_tool = next((t for t in orchestrator.tools if t.tool_id == "generate_visualization"), None)
        if visualization_tool:
            # Use the results from SQL execution
            data = sql_result.get("results", [])
            visualization_result = visualization_tool.run(data=data, visualization_type="bar")
            tool_results.append({"tool": "generate_visualization", "result": visualization_result})
            logger.info(f"Visualization result: {visualization_result}")
        
        # Step 4: Generate Follow-up Questions
        question_tool = next((t for t in orchestrator.tools if t.tool_id == "generate_follow_up_questions"), None)
        if question_tool:
            questions_result = question_tool.run(query="Show me the number of flights by month", results=tool_results)
            tool_results.append({"tool": "generate_follow_up_questions", "result": questions_result})
            logger.info(f"Follow-up questions: {questions_result}")
        
        # Generate final response
        response = orchestrator._generate_response("Show me the number of flights by month", tool_results, [])
        
        # Print the final result
        logger.info(f"Final result: {json.dumps(response, indent=2)}")
        return response
    
    except Exception as e:
        logger.error(f"Error testing visualizations: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Test visualizations
    test_visualizations() 