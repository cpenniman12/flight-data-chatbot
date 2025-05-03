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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NYC Flights 2013 dataset
- Anthropic's Claude 3.7 API for natural language understanding
- Plotly for interactive visualizations 