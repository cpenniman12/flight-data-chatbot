import os
import json
import uuid
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import create_engine, text
import anthropic
from flask import Flask, request, jsonify, session
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
                print(f"SQL execution error: {str(sql_exec_error)}")
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
            
            # Limit data returned to prevent large response
            return_data = df.head(100).to_dict(orient='records') if len(df) > 100 else df.to_dict(orient='records')
            
            return jsonify({
                'sql_query': sql_query,
                'data': return_data,
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