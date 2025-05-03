"""
Integration Example

This module shows how to integrate the agentic architecture with Flask.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

from agent_api import AgentAPI
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize agent API
agent_api = AgentAPI(db_path="nycflights13.db")

# Store active sessions
active_sessions = {}

@app.route('/agentic-chat', methods=['POST'])
async def agentic_chat():
    """
    Process a chat message using the agentic architecture.
    
    Request body:
    {
        "query": "User query",
        "session_id": "Optional session ID"
    }
    
    Response:
    {
        "content": "Response content",
        "tool_results": [
            {
                "tool": "Tool name",
                "result": { ... }
            },
            ...
        ],
        "follow_up_questions": [
            "Question 1?",
            "Question 2?",
            "Question 3?"
        ],
        "session_id": "Session ID"
    }
    """
    try:
        # Get request data
        data = request.json
        query = data.get('query', '')
        session_id = data.get('session_id', None)
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        # Process query
        response = await agent_api.process_query(query, session_id)
        
        # Store session ID if not already stored
        if session_id:
            active_sessions[session_id] = True
        elif 'session_id' in response:
            active_sessions[response['session_id']] = True
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear-session', methods=['POST'])
def clear_session():
    """
    Clear a session's conversation history.
    
    Request body:
    {
        "session_id": "Session ID to clear"
    }
    
    Response:
    {
        "status": "success"
    }
    """
    try:
        # Get request data
        data = request.json
        session_id = data.get('session_id', None)
        
        if not session_id:
            return jsonify({"error": "No session ID provided"}), 400
        
        # Clear history for the session
        if session_id in active_sessions:
            agent_api.clear_history()
            del active_sessions[session_id]
        
        return jsonify({"status": "success"})
    
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

def run_app():
    """Run the Flask app."""
    # Ensure ANTHROPIC_API_KEY is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
    
    # Run the app
    app.run(host='0.0.0.0', port=5002, debug=True)

if __name__ == '__main__':
    run_app() 