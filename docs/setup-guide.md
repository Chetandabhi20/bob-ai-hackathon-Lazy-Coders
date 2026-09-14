# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

Before you begin, ensure you have the following installed:

- [x] Python 3.11+
- [x] Node.js 20+
- [x] An IBM Cloud account with watsonx.ai access (Optional: runs in STUB mode without credentials)

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cd src
cp .env.example .env
```

| Variable | Description | Required |
|---|---|---|
| `WATSONX_API_KEY` | Your IBM watsonx.ai API key | No (Uses STUB mode if omitted) |
| `WATSONX_PROJECT_ID` | Your watsonx.ai project ID | No (Uses STUB mode if omitted) |
| `WATSONX_URL` | e.g. https://us-south.ml.cloud.ibm.com | No |
| `WEATHER_API_BASE` | Open-Meteo URL (default in .env.example) | Yes |
| `MCP_SERVER_PORT` | Port for the backend API (default 8001) | Yes |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Chetandabhi20/-bob-ai-hackathon-Lazy-Coders.git
cd -bob-ai-hackathon-Lazy-Coders

# 2. Set up Python backend
cd src
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Install frontend dependencies
cd src/frontend
npm install
cd ../..
```

## Data Generation (Optional)

The repository comes with pre-generated mock data. If you want to regenerate it:
```bash
cd src
# (Ensure venv is activated)
python -m data.generate_sensor_data
cd ..
```

## Running the Application

You will need two terminal windows.

**Terminal 1: Start the Backend API Server**
```bash
cd src
# (Ensure venv is activated)
python -m api.server
```

**Terminal 2: Start the React Frontend**
```bash
cd src/frontend
npm run dev
```

The application will be available at: `http://localhost:5173`

*(Note: The MCP stdio server for Bob integration can be run via `cd src && python -m mcp_server`)*

## Running Tests

```bash
cd src
# (Ensure venv is activated)
pytest tests/ -v
```

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` | Ensure your virtual environment is activated and `pip install -r requirements.txt` was run. |
| Chat Panel says "STUB MODE" | This is expected if `WATSONX_API_KEY` is not set. To use live watsonx generation, add real credentials to `src/.env`. |
| Connection Refused in UI | Ensure the Python backend (`python -m api.server`) is running on port 8001. |
