# NYC Flight Data Chatbot: Agentic Architecture

This directory contains the implementation of an agentic architecture for the NYC Flight Data Chatbot, which provides a more modular, flexible, and powerful approach to handling user queries.

## Overview

The agentic architecture breaks down the chatbot's functionality into specialized tools that can be orchestrated dynamically based on user needs:

- **SQL Generation**: Converts natural language to SQL queries
- **SQL Execution**: Runs SQL queries against the database  
- **Visualization**: Creates data visualizations
- **Follow-up Questions**: Suggests relevant follow-up questions

An Orchestrator Agent coordinates these tools, deciding which to use and in what order based on the user's query.

## Getting Started

### Prerequisites

- Python 3.7+
- Virtual environment (recommended)
- The NYC flights SQLite database (`nycflights13.db`)

### Installation

1. Activate your virtual environment:
   ```
   source flight_venv/bin/activate
   ```

2. Install the required packages:
   ```
   pip install anthropic pandas plotly flask flask-cors
   ```

3. Set your API key:
   ```
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

## Usage

### Starting the API Server

To run the agentic server:

```
python -m integration_example
```

The server will start on port 5002 by default. You can access the API at:
- `http://localhost:5002/agentic-chat` - Process chat messages
- `http://localhost:5002/clear-session` - Clear session history
- `http://localhost:5002/health` - Health check endpoint

### Using the API

To send a chat message:

```
POST /agentic-chat
{
    "query": "Show me the top 5 airlines by number of flights",
    "session_id": "optional-session-id"
}
```

Response:
```
{
    "content": "Response content",
    "tool_results": [
        {
            "tool": "generate_sql",
            "result": { ... }
        },
        {
            "tool": "execute_sql", 
            "result": { ... }
        },
        ...
    ],
    "follow_up_questions": [
        "Question 1?", 
        "Question 2?",
        "Question 3?"
    ],
    "session_id": "session-id"
}
```

### Non-Async Version

If you prefer a simpler, non-async implementation, you can use the `static_agent_example.py` module:

```python
from static_agent_example import SimpleFlightChatbot

# Set your API key
import os
os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"

# Initialize the chatbot
chatbot = SimpleFlightChatbot()

# Process a query
response = chatbot.process_query("Show me the top 5 airlines by number of flights")
```

## Understanding the Agentic Architecture

### Core Components

1. **Base Agent**: Defines the interface for all agents.
2. **Base Tool**: Defines the interface for all tools.
3. **Orchestrator Agent**: Coordinates the workflow between tools.
4. **Specialized Tools**: Each tool focuses on a specific task.

### Workflow

1. User sends a query
2. The Orchestrator determines which tools to use
3. Tools are executed in sequence, with outputs from earlier tools becoming inputs to later ones
4. Results are consolidated into a final response

### Benefits

- **Modularity**: Each component has a specific responsibility
- **Flexibility**: The system can adapt to different query types
- **Robustness**: Errors in one component don't necessarily break the entire system
- **Transparency**: You can see which tools were used and how

## Customization

You can add new tools or modify existing ones by:

1. Creating a new class that inherits from `BaseTool`
2. Implementing the `execute` method with your custom logic
3. Registering the tool with the Orchestrator Agent

## License

This project is licensed under the MIT License - see the LICENSE file for details. 