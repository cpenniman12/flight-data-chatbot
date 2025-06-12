import os
import json
import uuid
from typing import Dict, List, Optional
import pandas as pd
import requests
import anthropic
from flask import Flask, request, jsonify, session, send_from_directory, send_file, make_response, abort
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from flask_cors import CORS
import mimetypes

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for sessions
CORS(app)  # Enable CORS for all routes

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None
    print("Warning: ANTHROPIC_API_KEY not found. Set it in Render environment variables for AI responses.")

# Store conversation histories
conversations = {}

def execute_supabase_sql(sql_query):
    """Execute SQL query using Supabase RPC function."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise Exception("Supabase configuration missing")
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }
    data = {"query_text": sql_query}
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    if isinstance(result, dict) and 'error' in result:
        raise Exception(f"SQL Error: {result['error']}")
    
    return result

def get_flight_count():
    """Get count of flight records."""
    try:
        result = execute_supabase_sql("SELECT COUNT(*) as count FROM flights")
        return result[0]['count'] if result and len(result) > 0 else 0
    except Exception as e:
        print(f"Error getting flight count: {e}")
        return 0

# Schema context for the model (hardcoded as you mentioned)
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
   - alt (integer): Altitude
   - tz (integer): Timezone offset from UTC
   - dst (text): Daylight savings time zone
   - tzone (text): IANA time zone

3. planes
   - tailnum (text): Tail number
   - year (integer): Year manufactured
   - type (text): Type of plane
   - manufacturer (text): Manufacturer
   - model (text): Model
   - engines (integer): Number of engines
   - seats (integer): Number of seats
   - speed (integer): Average cruising speed in mph
   - engine (text): Type of engine

4. weather
   - origin (text): Origin airport
   - year, month, day, hour (integer): Date and time
   - temp, dewp (float): Temperature and dewpoint in F
   - humid (float): Relative humidity
   - wind_dir (integer): Wind direction in degrees
   - wind_speed, wind_gust (float): Wind speed and gust speed in mph
   - precip (float): Precipitation in inches
   - pressure (float): Sea level pressure in millibars
   - visib (float): Visibility in miles
   - time_hour (timestamp): Date and hour as POSIXct date

5. flights
   - year, month, day (integer): Date of departure
   - dep_time, arr_time (integer): Actual departure and arrival times (HHMM)
   - sched_dep_time, sched_arr_time (integer): Scheduled departure and arrival times (HHMM)
   - dep_delay, arr_delay (integer): Departure and arrival delays in minutes
   - carrier (text): Two letter carrier abbreviation
   - flight (integer): Flight number
   - tailnum (text): Plane tail number
   - origin, dest (text): Origin and destination airports
   - air_time (integer): Amount of time spent in the air in minutes
   - distance (integer): Distance between airports in miles
   - hour, minute (integer): Time of scheduled departure broken into hour and minutes
   - time_hour (timestamp): Scheduled date and hour of the flight as POSIXct date
"""

def generate_sql_query(user_query: str, conversation_history: List[Dict] = None) -> str:
    """Generate SQL query from natural language using Claude."""
    if not client:
        # Fallback simple queries if no API key
        if 'delay' in user_query.lower():
            return "SELECT carrier, AVG(dep_delay) as avg_delay FROM flights WHERE dep_delay IS NOT NULL GROUP BY carrier ORDER BY avg_delay DESC LIMIT 10;"
        elif 'carrier' in user_query.lower() or 'airline' in user_query.lower():
            return "SELECT a.name, COUNT(*) as flight_count FROM flights f JOIN airlines a ON f.carrier = a.carrier GROUP BY a.name ORDER BY flight_count DESC LIMIT 10;"
        else:
            return "SELECT carrier, COUNT(*) as flights, AVG(dep_delay) as avg_delay FROM flights GROUP BY carrier ORDER BY flights DESC LIMIT 10;"
    
    # Build the prompt with conversation history if available
    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_context = "Previous conversation:\n"
        for msg in conversation_history[-4:]:  # Last 4 messages only
            if msg["role"] == "user":
                conversation_context += f"User: {msg['content']}\n"
            else:
                conversation_context += f"SQL generated: {msg['content']}\n"
        conversation_context += "\n"
    
    prompt = f"""Given the following database schema:
{SCHEMA_CONTEXT}

{conversation_context}
User request: {user_query}

Generate a SQL query that answers the user's request. ONLY return the SQL query with NO markdown formatting,
 NO ```sql tags, and NO explanations.
IMPORTANT RULES:
1. This is a PostgreSQL database
2. Use simple aggregation functions like AVG(), COUNT(), SUM()
3. Always use single SQL statement only, not multiple statements
4. Add LIMIT 20 to prevent large result sets
5. For PostgreSQL, you can use EXTRACT() for date functions
6. All table columns used in the query must be properly listed in the GROUP BY clause
7. Handle NULL values appropriately with IS NOT NULL or COALESCE"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return "SELECT carrier, COUNT(*) as flights FROM flights GROUP BY carrier ORDER BY flights DESC LIMIT 10;"

def execute_query_and_generate_response(sql_query: str, user_query: str) -> Dict:
    """Execute SQL query and generate comprehensive response."""
    try:
        # Execute the SQL query
        data = execute_supabase_sql(sql_query)
        
        if not data or len(data) == 0:
            return {
                'sql': sql_query,
                'data': [],
                'analysis': "No data found for your query.",
                'visualization': None,
                'suggestions': ["Try a different question", "Check your search criteria"]
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)
        
        # Generate analysis and visualization
        analysis = generate_analysis(df, user_query) if client else "Data retrieved successfully."
        visualization = generate_visualization(df, user_query)
        suggestions = generate_suggestions(user_query) if client else [
            "What are the busiest airports?",
            "Show me flight delays by month",
            "Which airlines have the most flights?"
        ]
        
        return {
            'sql': sql_query,
            'data': data,
            'analysis': analysis,
            'visualization': visualization,
            'suggestions': suggestions
        }
        
    except Exception as e:
        error_msg = str(e)
        return {
            'sql': sql_query,
            'data': [],
            'error': f"SQL Error: {error_msg}",
            'analysis': "There was an error executing your query.",
            'visualization': None,
            'suggestions': ["Try rephrasing your question", "Use simpler terms"]
        }

def generate_analysis(df: pd.DataFrame, user_query: str) -> str:
    """Generate qualitative analysis of the query results."""
    if not client:
        return "Data analysis requires AI configuration."
    
    # Convert DataFrame to a summary for the prompt
    summary = f"Query results summary:\n"
    summary += f"- Number of rows: {len(df)}\n"
    summary += f"- Columns: {', '.join(df.columns.tolist())}\n"
    
    if len(df) > 0:
        # Add some sample data
        summary += f"- Sample data:\n{df.head(3).to_string()}\n"
        
        # Add basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary += f"- Numeric column statistics:\n{df[numeric_cols].describe().to_string()}\n"
    
    prompt = f"""Analyze the following query results and provide insights:

Original question: {user_query}
{summary}

Provide a brief, insightful analysis (2-3 sentences) that:
1. Summarizes the key findings
2. Highlights interesting patterns or trends
3. Puts the results in context

Keep it conversational and accessible."""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error generating analysis: {e}")
        return "Analysis generation failed, but your data query was successful."

def generate_visualization(df: pd.DataFrame, user_query: str) -> Optional[str]:
    """Generate appropriate visualization for the data."""
    if df.empty or len(df) == 0:
        return None
    
    try:
        # Determine chart type based on data characteristics
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
        
        if len(numeric_cols) == 0:
            return None
        
        # Simple heuristics for chart selection
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            # Bar chart for categorical vs numeric
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            
            # Limit to top 15 items for readability
            if len(df) > 15:
                df_plot = df.head(15).copy()
            else:
                df_plot = df.copy()
            
            fig = px.bar(df_plot, x=x_col, y=y_col, 
                        title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}")
            fig.update_layout(xaxis_tickangle=-45)
            
        elif len(numeric_cols) >= 2:
            # Scatter plot for numeric vs numeric
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1],
                           title=f"{numeric_cols[1].replace('_', ' ').title()} vs {numeric_cols[0].replace('_', ' ').title()}")
        else:
            # Histogram for single numeric column
            fig = px.histogram(df, x=numeric_cols[0],
                             title=f"Distribution of {numeric_cols[0].replace('_', ' ').title()}")
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        
        return fig.to_json()
    
    except Exception as e:
        print(f"Error generating visualization: {e}")
        return None

def generate_suggestions(user_query: str) -> List[str]:
    """Generate follow-up question suggestions."""
    if not client:
        return [
            "What are the busiest airports?",
            "Show me flight delays by month",
            "Which airlines have the most flights?"
        ]
    
    prompt = f"""Given this flight data query: "{user_query}"

Generate 3 short, interesting follow-up questions that a user might want to ask about NYC flight data.
Make them specific and actionable. Return as a simple list, one question per line."""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        suggestions = [s.strip().lstrip('- ').lstrip('• ') for s in response.content[0].text.strip().split('\n') if s.strip()]
        return suggestions[:3]  # Ensure we only return 3
    except Exception as e:
        print(f"Error generating suggestions: {e}")
        return [
            "What are the busiest airports?",
            "Show me flight delays by month",
            "Which airlines have the most flights?"
        ]

# --- Robust static file serving for Render/production ---
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist'))
INDEX_FILE = os.path.join(STATIC_DIR, 'index.html')

@app.route('/')
def serve_frontend():
    """Serve the main frontend page (index.html)."""
    if not os.path.exists(INDEX_FILE):
        return ("<h1>Frontend build missing</h1><p>Run <code>npm run build</code> in frontend/ to generate dist/.</p>", 500)
    return send_file(INDEX_FILE)

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from the frontend/dist directory with security and caching."""
    requested_path = os.path.abspath(os.path.join(STATIC_DIR, filename))
    if not requested_path.startswith(STATIC_DIR):
        abort(403)  # Directory traversal attempt
    if not os.path.exists(requested_path):
        # SPA routing: serve index.html for unknown paths (except API)
        if not filename.startswith('api') and not filename.startswith('chat'):
            return send_file(INDEX_FILE)
        abort(404)
    # Set cache headers based on file type
    response = make_response(send_file(requested_path))
    mime, _ = mimetypes.guess_type(requested_path)
    if mime and mime.startswith('text/html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    elif mime and (mime.endswith('javascript') or mime.endswith('css')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif mime and mime.startswith('image/'):
        response.headers['Cache-Control'] = 'public, max-age=2592000'
    else:
        response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint."""
    data = request.get_json()
    user_query = data.get('query')
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Get or create conversation history
    if session_id not in conversations:
        conversations[session_id] = []
    
    conversation_history = conversations[session_id]
    
    try:
        # Generate SQL query
        sql_query = generate_sql_query(user_query, conversation_history)
        
        # Execute query and generate response
        result = execute_query_and_generate_response(sql_query, user_query)
        
        # Add to conversation history
        conversation_history.append({"role": "user", "content": user_query})
        conversation_history.append({"role": "assistant", "content": sql_query})
        
        # Keep only last 10 exchanges
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        conversations[session_id] = conversation_history
        
        # Add session_id to response
        result['session_id'] = session_id
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'session_id': session_id,
            'sql_query': sql_query if 'sql_query' in locals() else None
        }), 500

@app.route('/status')
def status():
    """Check system status."""
    flight_count = get_flight_count()
    
    return jsonify({
        'status': 'running',
        'database_type': 'Supabase REST API',
        'anthropic_api': 'configured' if ANTHROPIC_API_KEY else 'missing',
        'database': 'connected' if flight_count > 0 else 'not loaded',
        'flight_records': flight_count,
        'message': f'Using Supabase REST API - Ready to analyze NYC 2013 flight data!' if flight_count > 0 else f'Using Supabase REST API - Data needs to be loaded'
    })

@app.route('/load-data', methods=['POST'])
def load_data_endpoint():
    """Endpoint to check if data is loaded."""
    try:
        flight_count = get_flight_count()
        if flight_count > 0:
            return jsonify({'status': 'success', 'message': f'Data already loaded: {flight_count:,} flight records'})
        else:
            return jsonify({'status': 'success', 'message': 'Data loading not needed with Supabase REST API'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    print(f"Starting server on port {port}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Anthropic API configured: {bool(ANTHROPIC_API_KEY)}")
    app.run(host='0.0.0.0', port=port, debug=False) 