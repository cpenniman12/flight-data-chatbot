"""
Static Agent Example

This module provides a simpler, non-async implementation for users who don't want
to use async/await.
"""

import os
import json
import logging
from typing import Dict, Any, List

import anthropic

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

class SimpleFlightChatbot:
    """
    A simpler implementation of the NYC Flight Data Chatbot.
    
    This class uses direct Claude 3.7 calls instead of the agentic architecture,
    but it's structured to mimic the workflow of the agentic architecture.
    """
    
    def __init__(self, db_path: str = "nycflights13.db"):
        """
        Initialize the SimpleFlightChatbot.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.db_path = db_path
        self.conversation_history = []
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query.
        
        Args:
            query: The user query
            
        Returns:
            Response from Claude
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": query})
        
        # Generate SQL
        sql_query = self._generate_sql(query)
        logger.info(f"Generated SQL query: {sql_query}")
        
        # Execute SQL
        sql_results = self._execute_sql(sql_query)
        
        # Generate response
        response_content = self._generate_response(query, sql_query, sql_results)
        
        # Generate visualization code
        viz_code = self._generate_visualization(query, sql_results)
        
        # Generate follow-up questions
        follow_up_questions = self._generate_follow_up_questions(query, sql_results)
        
        # Add assistant message to history
        self.conversation_history.append({"role": "assistant", "content": response_content})
        
        # Prepare final response
        response = {
            "content": response_content,
            "sql_query": sql_query,
            "results": sql_results.get("results", [])[:20],  # Limit to first 20 rows
            "visualization_code": viz_code,
            "follow_up_questions": follow_up_questions
        }
        
        return response
    
    def _generate_sql(self, query: str) -> str:
        """
        Generate a SQL query from a natural language query.
        
        Args:
            query: The natural language query
            
        Returns:
            Generated SQL query
        """
        # Create the prompt
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
        
        prompt = f"""Given the following database schema:
{schema_context}

User request: {query}

Generate a SQL query that answers the user's request. ONLY return the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.
IMPORTANT RULES:
1. Do not use ROUND() function, use CAST() with decimal type instead: "CAST(number AS decimal(10,2))"
2. Always use single SQL statement only, not multiple statements
3. Never use EXTRACT() function, use date_part() instead
4. All table columns used in the query must be properly listed in the GROUP BY clause
5. Never reference time_hour directly in GROUP BY, extract parts from it first"""
        
        # Call Claude to generate SQL
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0,
            system="You are a SQL expert. Generate ONLY the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract SQL query
        sql_query = response.content[0].text.strip()
        
        # Clean up the SQL query
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
    
    def _execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL query.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Results of the SQL query
        """
        import sqlite3
        import pandas as pd
        
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            
            # Execute query
            df = pd.read_sql_query(sql_query, conn, params={})
            
            # Close connection
            conn.close()
            
            # Convert to dictionary
            results = df.to_dict(orient="records")
            
            # Get column information
            columns = [
                {"name": col, "type": str(df[col].dtype)} 
                for col in df.columns
            ]
            
            return {
                "results": results,
                "columns": columns,
                "total_rows": len(results),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            
            # Try a simpler fallback query if the main query fails
            fallback_query = "SELECT * FROM flights LIMIT 10;"
            
            try:
                # Connect to database
                conn = sqlite3.connect(self.db_path)
                
                # Execute fallback query
                df = pd.read_sql_query(fallback_query, conn, params={})
                
                # Close connection
                conn.close()
                
                # Convert to dictionary
                results = df.to_dict(orient="records")
                
                # Get column information
                columns = [
                    {"name": col, "type": str(df[col].dtype)} 
                    for col in df.columns
                ]
                
                return {
                    "results": results,
                    "columns": columns,
                    "total_rows": len(results),
                    "error": str(e),
                    "status": "fallback"
                }
                
            except Exception as fallback_error:
                return {
                    "error": f"Primary query failed: {str(e)}\nFallback query failed: {str(fallback_error)}",
                    "status": "error"
                }
    
    def _generate_response(self, query: str, sql_query: str, sql_results: Dict[str, Any]) -> str:
        """
        Generate a response based on the SQL results.
        
        Args:
            query: The original user query
            sql_query: The SQL query that was executed
            sql_results: The results of the SQL query
            
        Returns:
            Generated response
        """
        # Prepare the data for Claude
        results_str = json.dumps(sql_results.get("results", [])[:5])  # Limit to first 5 rows
        columns_str = json.dumps(sql_results.get("columns", []))
        
        # Create the prompt
        prompt = f"""You are an AI assistant helping with flight data analysis.

User query: {query}

I executed the following SQL query:
{sql_query}

Here are up to 5 rows from the results:
{results_str}

Column information:
{columns_str}

Based on these results, provide a helpful, concise response to the user's query.
Focus on the key insights and results. If there were errors, explain what went wrong.
Keep your response under 150 words.
"""
        
        # Call Claude to generate response
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            temperature=0.2,
            system="You are a helpful assistant responding to questions about flight data.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text.strip()
    
    def _generate_visualization(self, query: str, sql_results: Dict[str, Any]) -> str:
        """
        Generate visualization code based on the SQL results.
        
        Args:
            query: The original user query
            sql_results: The results of the SQL query
            
        Returns:
            Generated visualization code
        """
        # Check if we have results to visualize
        if not sql_results.get("results"):
            return ""
        
        # Prepare the data for Claude
        results_str = json.dumps(sql_results.get("results", [])[:5])  # Limit to first 5 rows
        columns_str = json.dumps(sql_results.get("columns", []))
        
        # Create the prompt
        prompt = f"""Generate visualization code using Plotly Express for the following data:

User Query: "{query}"

Column Information:
{columns_str}

Data Sample (first 5 rows):
{results_str}

Please generate simple Python code that creates an appropriate visualization for this data using Plotly Express.
The visualization should help answer the user's query effectively.

IMPORTANT RULES:
1. The code should ONLY use Plotly Express (px)
2. Return ONLY the Python code with no explanations or markdown
3. The code must be executable as-is
4. Make all imports explicit (import plotly.express as px)
5. Avoid complex code with conditionals or functions
6. Keep it under 10 lines of code
7. No figure.show() in the code

Use this template:
```python
import plotly.express as px
fig = px.chart_type(df, x='x_column', y='y_column', title='Descriptive title')
```"""
        
        # Call Claude to generate visualization code
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            temperature=0,
            system="You are a data visualization expert. Generate ONLY Python code using Plotly Express with no explanations or markdown.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract visualization code
        viz_code = response.content[0].text.strip()
        
        # Clean up the code
        if viz_code.startswith("```python"):
            viz_code = viz_code.split("```python", 1)[1]
        if viz_code.startswith("```"):
            viz_code = viz_code.split("```", 1)[1]
        if viz_code.endswith("```"):
            viz_code = viz_code.rsplit("```", 1)[0]
        
        viz_code = viz_code.strip()
        
        # Ensure required imports are present
        if "import plotly.express as px" not in viz_code:
            viz_code = "import plotly.express as px\n" + viz_code
        
        # Ensure there's no figure.show() call
        viz_code = viz_code.replace("fig.show()", "")
        
        return viz_code
    
    def _generate_follow_up_questions(self, query: str, sql_results: Dict[str, Any]) -> List[str]:
        """
        Generate follow-up questions based on the SQL results.
        
        Args:
            query: The original user query
            sql_results: The results of the SQL query
            
        Returns:
            List of follow-up questions
        """
        # Check if we have results to analyze
        if not sql_results.get("results"):
            return [
                "What aspects of NYC flights would you like to explore?",
                "Would you like to see information about flight delays?",
                "Are you interested in airline performance data?"
            ]
        
        # Prepare the data for Claude
        results_str = json.dumps(sql_results.get("results", [])[:5])  # Limit to first 5 rows
        columns_str = ", ".join([col["name"] for col in sql_results.get("columns", [])])
        
        # Create the prompt
        prompt = f"""Generate 3 insightful follow-up questions based on the following user query and data:

User query: {query}

Available columns: {columns_str}

Sample results (first 5 rows):
{results_str}

Generate 3 follow-up questions that would:
1. Deepen the analysis of the current data
2. Explore related aspects not covered in the current query
3. Offer a different perspective or comparison

IMPORTANT RULES:
1. Questions must be different from the current query
2. Questions should be clear and specific
3. Focus on questions that can be answered with SQL queries on this flight data
4. Questions should be natural, conversational, and not too technical
5. Return ONLY a JSON array of strings with NO additional text
6. Each question should be 2-15 words long

Return a JSON array in exactly this format:
["Question 1?", "Question 2?", "Question 3?"]"""
        
        # Call Claude to generate follow-up questions
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            temperature=0.7,  # Higher temperature for more variety
            system="You are a data analyst. Generate ONLY a JSON array of follow-up questions with NO additional text.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract follow-up questions
        questions_text = response.content[0].text.strip()
        
        # Clean up the response
        questions_text = questions_text.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        try:
            questions = json.loads(questions_text)
            
            # Ensure we have a list of strings
            if not isinstance(questions, list):
                raise ValueError("Not a list")
            
            # Ensure we have exactly 3 questions
            while len(questions) < 3:
                questions.append(f"Would you like to explore more about {sql_results.get('columns', [{}])[0].get('name', 'flights')}?")
            
            if len(questions) > 3:
                questions = questions[:3]
            
            # Ensure questions end with question marks
            questions = [q if q.endswith("?") else f"{q}?" for q in questions]
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing follow-up questions: {str(e)}")
            
            # Fallback questions
            return [
                "What other aspects of NYC flights would you like to explore?",
                "Would you like to see trends in flight delays by month?",
                "How do flight patterns vary between different airlines?"
            ]
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

def example_usage():
    """Example usage of the SimpleFlightChatbot."""
    # Set API key from environment variable
    os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"
    
    # Initialize the chatbot
    chatbot = SimpleFlightChatbot()
    
    # Process a query
    response = chatbot.process_query("Show me the top 5 airlines by number of flights")
    
    # Print the response
    print("Response:", response["content"])
    print("\nSQL Query:", response["sql_query"])
    print("\nVisualization Code:", response["visualization_code"])
    print("\nFollow-up Questions:", response["follow_up_questions"])
    
    # Process another query
    response = chatbot.process_query("Which airports have the most delays?")
    
    # Print the response
    print("\n\nResponse:", response["content"])
    print("\nSQL Query:", response["sql_query"])
    print("\nVisualization Code:", response["visualization_code"])
    print("\nFollow-up Questions:", response["follow_up_questions"])

if __name__ == "__main__":
    # Run the example
    example_usage() 