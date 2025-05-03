import os
import json
import uuid
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import create_engine, text
import anthropic
from flask import Flask, request, jsonify, session
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for sessions
CORS(app)  # Enable CORS for all routes

# Database connection
DB_USER = 'cooperpenniman'
DB_PASSWORD = ''
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nycflights'

conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(conn_string)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Store conversation histories
conversations = {}

# Schema context for the model
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

def generate_sql(user_query: str, conversation_history: List[Dict] = None) -> str:
    """Generate SQL query based on user's natural language request and conversation history."""
    
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
    
    prompt = f"""Given the following database schema:
{SCHEMA_CONTEXT}

{conversation_context}
User request: {user_query}

Generate a SQL query that answers the user's request. ONLY return the SQL query with NO markdown formatting, NO ```sql tags, and NO explanations.
IMPORTANT RULES:
1. Do not use ROUND() function, use CAST() with decimal type instead: "CAST(number AS decimal(10,2))"
2. Always use single SQL statement only, not multiple statements
3. Never use EXTRACT() function, use date_part() instead
4. All table columns used in the query must be properly listed in the GROUP BY clause
5. Never reference time_hour directly in GROUP BY, extract parts from it first"""

    response = client.messages.create(
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
    
    return sql_query

def execute_sql(sql_query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(text(sql_query), conn)

def generate_visualization(df: pd.DataFrame, user_query: str) -> str:
    """Generate visualization code based on the DataFrame and user query."""
    # Determine column types for better visualization code
    dtypes = {col: str(df[col].dtype) for col in df.columns}
    numeric_cols = [col for col, dtype in dtypes.items() if 'int' in dtype or 'float' in dtype]
    categorical_cols = [col for col, dtype in dtypes.items() if 'object' in dtype or 'str' in dtype]
    
    # Limit data sample to prevent context overflow
    data_preview = df.head(3).to_string()
    
    # Simplified prompt focused on basic visualization types
    prompt = f"""Given this DataFrame with columns and their types:
{dtypes}

And this sample of data:
{data_preview}

Create a SIMPLE visualization using Plotly Express for this query: "{user_query}"

ONLY use the following:
- For bar charts: px.bar(df, x='{categorical_cols[0] if categorical_cols else numeric_cols[0]}', y='{numeric_cols[0] if numeric_cols else df.columns[0]}')
- For line charts: px.line(df, x='{categorical_cols[0] if categorical_cols else numeric_cols[0]}', y='{numeric_cols[0] if numeric_cols else df.columns[0]}')
- For pie charts: px.pie(df, names='{categorical_cols[0] if categorical_cols else df.columns[0]}', values='{numeric_cols[0] if numeric_cols else df.columns[1]}')

Return ONLY valid executable Python code using Plotly Express (px). No explanation."""

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=500,
        temperature=0,
        system="You are a data visualization expert. Generate ONLY Python code with NO markdown, NO tags, NO explanations.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    viz_code = response.content[0].text.strip()
    
    # Remove any markdown formatting if it exists
    if viz_code.startswith("```"):
        viz_code = viz_code.split("\n", 1)[1]
    if viz_code.endswith("```"):
        viz_code = viz_code.rsplit("\n", 1)[0]
    
    viz_code = viz_code.replace("```python", "").replace("```", "").strip()
    
    # Fallback to simplest visualization if code looks complex
    if len(viz_code.split("\n")) > 10:
        if numeric_cols and len(df) > 0:
            x_col = categorical_cols[0] if categorical_cols else df.columns[0]
            y_col = numeric_cols[0] if numeric_cols else df.columns[1] if len(df.columns) > 1 else df.columns[0]
            viz_code = f"import plotly.express as px\nfig = px.bar(df, x='{x_col}', y='{y_col}', title='Results')"
    
    # Add import if missing
    if "import plotly.express as px" not in viz_code:
        viz_code = "import plotly.express as px\n" + viz_code
    
    # Ensure the code returns a figure object
    if "fig =" not in viz_code and "fig=" not in viz_code:
        viz_code += "\nfig = px.bar(df, x='{}', y='{}')".format(
            df.columns[0], 
            df.columns[1] if len(df.columns) > 1 else df.columns[0]
        )
    
    return viz_code

def generate_analysis(df: pd.DataFrame, user_query: str, sql_query: str) -> str:
    """Generate qualitative analysis of the data using Claude 3.7."""
    # Determine column types for better analysis
    dtypes = {col: str(df[col].dtype) for col in df.columns}
    
    # Get a summary of the data
    data_summary = ""
    if not df.empty:
        # Basic stats for numeric columns
        numeric_cols = [col for col, dtype in dtypes.items() if 'int' in dtype or 'float' in dtype]
        if numeric_cols:
            data_summary += "Numeric column statistics:\n"
            for col in numeric_cols[:3]:  # Limit to first 3 numeric columns to avoid context overflow
                data_summary += f"{col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}\n"
        
        # Value counts for categorical columns
        categorical_cols = [col for col, dtype in dtypes.items() if 'object' in dtype or 'str' in dtype]
        if categorical_cols:
            data_summary += "\nCategorical column value counts:\n"
            for col in categorical_cols[:2]:  # Limit to first 2 categorical columns
                top_values = df[col].value_counts().head(3)
                data_summary += f"{col} top values: {dict(top_values)}\n"
        
        # Row count
        data_summary += f"\nTotal rows: {len(df)}"
    else:
        data_summary = "No data returned from the query."
    
    # Create prompt for analysis
    prompt = f"""User query: "{user_query}"

SQL query executed:
{sql_query}

DataFrame columns and types:
{dtypes}

Data summary:
{data_summary}

Please provide a brief, concise qualitative analysis of this data in relation to the user's question. Include insights that aren't obvious from just looking at the raw numbers.

If the user is asking about data availability, methodology, or other non-quantitative aspects, focus your response on addressing those questions.

Keep your analysis to 2-3 sentences at most. Be direct and informative, avoiding unnecessary explanations or qualifiers."""

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=300,
        temperature=0.2,
        system="You are a data analyst expert specializing in flight data. Provide concise, insightful qualitative analysis of data. Never use more than 2-3 sentences in your response.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    analysis = response.content[0].text.strip()
    return analysis

def generate_follow_up_questions(user_query: str, df: pd.DataFrame, sql_query: str) -> List[str]:
    """Generate compelling follow-up questions based on the current query and results."""
    # Determine column types for better suggestions
    dtypes = {col: str(df[col].dtype) for col in df.columns}
    
    # Get a summary of the data to inform follow-up suggestions
    data_summary = ""
    if not df.empty:
        # Create a brief summary of the data
        data_summary = f"The returned data has {len(df)} rows with columns: {', '.join(df.columns)}."
        
        # Include sample values from key columns (limit to first 3 rows)
        data_sample = df.head(3).to_dict(orient='records')
        data_summary += f"\nSample data: {data_sample}"
    else:
        data_summary = "No data was returned from the query."
    
    # Create prompt for follow-up questions
    prompt = f"""User's original query: "{user_query}"

SQL query executed:
{sql_query}

Data summary: 
{data_summary}

Database schema:
{SCHEMA_CONTEXT}

Based on the user's original query and the data returned, generate 3-4 compelling and fascinating follow-up questions that would provide additional insights or explore related aspects.

These follow-up questions should:
1. Be natural, conversational, and specific
2. Explore different aspects of the data than the original query
3. Reveal interesting patterns or relationships
4. Each question should be self-contained (no need for explanations)
5. Questions should be distinctly different from each other

Format your response as a numbered list with ONLY the follow-up questions, no explanations or additional text."""

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=400,
        temperature=0.7,  # Higher temperature for more creative suggestions
        system="You are a curious data analyst generating compelling follow-up questions. Provide ONLY 3-4 numbered questions with no additional text.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Process the response to extract just the questions
    questions_text = response.content[0].text.strip()
    
    # Split by numbered list indicators and clean up
    # This handles formats like "1. Question", "1) Question", etc.
    import re
    questions = re.split(r'\d+[\.\)]?\s+', questions_text)
    questions = [q.strip() for q in questions if q.strip()]
    
    # Limit to 4 questions maximum
    return questions[:4]

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.json
        user_query = data.get('query')
        session_id = data.get('session_id')
        
        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Create a new session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get or create conversation history
        if session_id not in conversations:
            conversations[session_id] = []
        
        # Add user message to history
        conversations[session_id].append({"role": "user", "content": user_query})
        
        # Keep only the last 3 messages to limit context size
        if len(conversations[session_id]) > 3:
            conversations[session_id] = conversations[session_id][-3:]
        
        # Generate SQL using conversation history
        sql_query = generate_sql(user_query, conversations[session_id])
        print(f"Generated SQL query: {sql_query}")
        
        # Add SQL to conversation history
        conversations[session_id].append({"role": "assistant", "content": sql_query})
        
        try:
            # Execute SQL query with error handling
            try:
                df = execute_sql(sql_query)
            except Exception as sql_exec_error:
                print(f"First SQL execution error: {str(sql_exec_error)}")
                # Try simplifying the query if it fails
                simplified_query = sql_query.split("GROUP BY")[0] + " LIMIT 10;"
                try:
                    df = execute_sql(simplified_query)
                    sql_query = simplified_query
                except Exception:
                    # If that also fails, try a very basic query
                    backup_query = f"SELECT * FROM flights LIMIT 5;"
                    df = execute_sql(backup_query)
                    sql_query = backup_query
            
            if df.empty:
                return jsonify({
                    'sql_query': sql_query,
                    'data': [],
                    'visualization': None,
                    'analysis': "No data found for your query.",
                    'follow_up_questions': [
                        "What airlines operated flights in 2013?",
                        "How many airports were served by NYC flights?",
                        "What was the average flight distance?",
                        "Which months had the most flights?"
                    ],
                    'session_id': session_id
                })
            
            # Generate analysis of the data
            analysis = generate_analysis(df, user_query, sql_query)
            print(f"Generated analysis: {analysis}")
            
            # Generate follow-up questions
            follow_up_questions = generate_follow_up_questions(user_query, df, sql_query)
            print(f"Generated follow-up questions: {follow_up_questions}")
            
            # Generate visualization
            viz_json = None
            try:
                # Limit dataframe size to prevent memory issues
                viz_df = df.head(100) if len(df) > 100 else df
                viz_code = generate_visualization(viz_df, user_query)
                print(f"Generated visualization code: {viz_code}")
                
                # Define the local variables for the eval context
                eval_locals = {'df': viz_df, 'px': px}
                
                # Execute the visualization code
                exec(viz_code, globals(), eval_locals)
                
                # Get the figure from the locals
                viz_fig = eval_locals.get('fig')
                if viz_fig:
                    viz_json = json.loads(viz_fig.to_json())
            except Exception as viz_error:
                print(f"Visualization error: {str(viz_error)}")
                # Try a simpler fallback visualization
                try:
                    if len(df.columns) >= 2:
                        # Simple fallback: bar chart of the first two columns
                        x_col = df.columns[0]
                        y_col = df.columns[1]
                        fig = px.bar(df, x=x_col, y=y_col, title='Results')
                        viz_json = json.loads(fig.to_json())
                        print("Used fallback visualization")
                except Exception as fallback_error:
                    print(f"Fallback visualization error: {str(fallback_error)}")
                    viz_json = None
            
            # Limit data returned to prevent large response
            return_data = df.head(100).to_dict(orient='records') if len(df) > 100 else df.to_dict(orient='records')
            
            return jsonify({
                'sql_query': sql_query,
                'data': return_data,
                'visualization': viz_json,
                'analysis': analysis,
                'follow_up_questions': follow_up_questions,
                'session_id': session_id
            })
            
        except Exception as sql_error:
            print(f"SQL execution error: {str(sql_error)}")
            return jsonify({
                'error': f"SQL Error: {str(sql_error)}",
                'sql_query': sql_query,
                'session_id': session_id
            }), 500
            
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True) 