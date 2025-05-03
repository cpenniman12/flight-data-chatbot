# Flight Data Chat Application Setup Instructions

## Virtual Environment Setup

1. Create the virtual environment (one-time setup):
```bash
python3 -m venv flight_venv
```

2. Activate the virtual environment:
- On macOS/Linux:
  ```bash
  source flight_venv/bin/activate
  ```
- On Windows:
  ```bash
  flight_venv\Scripts\activate
  ```

You'll know the virtual environment is active when you see `(flight_venv)` at the beginning of your terminal prompt.

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. To deactivate the virtual environment when you're done:
```bash
deactivate
```

## Environment Variables

Make sure to create a `.env` file in the project root with your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Application

With the virtual environment activated:
```bash
python flight_chat.py
```

The application will be available at http://localhost:5001 