# NYC Flight Data Chatbot

An interactive chatbot that allows users to query and visualize flight data from NYC airports in 2013 using natural language. 

## Features

- Natural language interface to query flight data
- SQL query generation from natural language using Claude 3.7
- Data visualization with Plotly
- Qualitative analysis of query results
- Smart follow-up question suggestions
- Clean, dark-themed UI with responsive design

## Architecture

### Backend (Python/Flask)
- SQL generation from natural language using Claude 3.7
- Data retrieval from PostgreSQL database
- Data analysis and visualization code generation
- REST API for frontend communication

### Frontend (React/Vite)
- Clean, minimalist UI with dark theme
- Interactive chat interface
- Visualization rendering with Plotly
- Suggestion bubbles for easy querying
- Collapsible SQL display

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL database with NYC flights data

### Installation

1. Clone the repository
```bash
git clone https://github.com/cpenniman12/flight-data-chatbot.git
cd flight-data-chatbot
```

2. Set up Python environment
```bash
python -m venv flight_venv
source flight_venv/bin/activate  # On Windows: flight_venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables
Create a .env file with your database and API credentials:
```
ANTHROPIC_API_KEY=your_claude_api_key
```

4. Install frontend dependencies
```bash
cd frontend
npm install
```

### Running the application

1. Start the backend server
```bash
source flight_venv/bin/activate
python flight_chat.py
```

2. Start the frontend development server
```bash
cd frontend
npm run dev
```

3. Open the application in your browser
Navigate to http://localhost:5173 (or the URL shown in your terminal)

## Example Questions

- "What are the top 5 carriers by number of flights?"
- "Show me average delays by month"
- "Which destinations have the most flights from JFK?"
- "What days had the highest number of flights?"
- "Show flights with the longest distance"
- "Compare departure delays across airlines"

## Future Development

The next phase of development (to be implemented in a separate branch) will transform the application into a fully agentic architecture with modular tools and multi-agent orchestration.

### Agentic Architecture

Instead of always following the fixed pipeline of SQL generation → execution → visualization, the system will employ specialized agents that can be called on-demand:

1. **Orchestrator Agent**: The primary agent that decides which tools to use based on the user's query
2. **SQL Generation Agent**: Specialized in converting natural language to SQL
3. **Query Execution Agent**: Handles database connections and query execution
4. **Visualization Agent**: Creates appropriate visualizations based on result data
5. **Analysis Agent**: Provides qualitative insights about the data

### Tool-Based Execution

Each capability will be implemented as a "tool" that can be called by the orchestrator:

- `generate_sql(query)`: Converts natural language to SQL
- `execute_sql(sql_query)`: Runs SQL against the database
- `create_visualization(data)`: Generates appropriate charts
- `analyze_data(data, query)`: Provides insights and analysis
- `refine_sql(query, feedback)`: Improves SQL based on feedback

### Interactive Workflow

The new system will feature:

- **Visible Tool Execution**: Users see which tools are being called in real-time
- **Iterative Refinement**: If SQL doesn't match user intent, the orchestrator can direct the SQL agent to refine it
- **Selective Execution**: Skip visualization for simple queries or focus on analysis for complex ones
- **Reasoning Transparency**: Show the orchestrator's decision-making process
- **Feedback Loop**: Learn from user interactions to improve future responses

### Technical Considerations

The implementation will explore:
- Claude's Function Calling API
- OpenAI's Assistants API with Function Calling
- Multi-agent frameworks like LangGraph or CrewAI
- State management for complex agent interactions
- Streaming responses to show real-time progress

This architecture will not only improve the user experience but also create a more modular and maintainable codebase that can be extended with additional tools and capabilities in the future.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NYC Flights 2013 dataset
- Anthropic's Claude 3.7 API for natural language understanding
- Plotly for interactive visualizations 