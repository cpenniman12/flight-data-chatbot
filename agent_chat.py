"""Agent-based chat application for querying flight data."""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
import anthropic
from flask import Flask, request, jsonify, session
from dotenv import load_dotenv
from flask_cors import CORS

from agents.orchestrator import create_orchestrator

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for sessions
CORS(app)  # Enable CORS for all routes

# Database connection settings
DB_USER = 'cooperpenniman'
DB_PASSWORD = ''
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nycflights'

conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Session storage for orchestrator agents
orchestrators = {}

# Progress events for frontend
progress_events = {}

def progress_callback(event_type: str, data: Dict[str, Any]) -> None:
    """Callback function for progress updates.
    
    Args:
        event_type: Type of event
        data: Event data
    """
    global progress_events
    
    # Store the progress event by session ID
    session_id = data.get("session_id", "default")
    if session_id not in progress_events:
        progress_events[session_id] = []
    
    # Add the event to the list
    progress_events[session_id].append({
        "type": event_type,
        "data": data
    })
    
    # Limit the number of events stored
    if len(progress_events[session_id]) > 50:
        progress_events[session_id] = progress_events[session_id][-50:]
    
    # Log the event
    print(f"Progress event: {event_type} - {data.get('message', '')}")

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests using the agent architecture."""
    try:
        data = request.json
        user_query = data.get('query')
        session_id = data.get('session_id')
        
        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Create a new session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get or create an orchestrator for this session
        if session_id not in orchestrators:
            orchestrators[session_id] = create_orchestrator(
                db_connection_string=conn_string,
                progress_callback=lambda event_type, data: progress_callback(
                    event_type, {**data, "session_id": session_id}
                )
            )
        
        # Process the query using the orchestrator
        orchestrator = orchestrators[session_id]
        result = orchestrator.process({
            "query": user_query,
            "session_id": session_id
        })
        
        # Check for errors
        if result.get("status") != "success":
            return jsonify({
                'error': result.get("error", "Unknown error"),
                'session_id': session_id
            }), 500
        
        # Return the results
        return jsonify({
            'sql_query': result.get("sql_query", ""),
            'data': result.get("data", []),
            'session_id': session_id,
            'column_names': result.get("column_names", []),
            'row_count': result.get("row_count", 0)
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Get progress events for a session."""
    session_id = request.args.get('session_id', 'default')
    
    # Return the progress events for this session
    events = progress_events.get(session_id, [])
    
    # Clear the events after returning them
    progress_events[session_id] = []
    
    return jsonify({'events': events})

if __name__ == '__main__':
    app.run(port=5001, debug=True) 