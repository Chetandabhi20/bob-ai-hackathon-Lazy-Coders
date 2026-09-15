# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Live Deployment (Fastest — No Setup Required)

The application is deployed on Railway. Judges can use it immediately:

| Resource | URL |
|---|---|
| **Live Dashboard** | https://grid-guardian-production.up.railway.app |
| **Remote MCP (Bob)** | https://grid-guardian-production.up.railway.app/mcp |
| **API Docs** | https://grid-guardian-production.up.railway.app/docs |

### Connect IBM Bob to the live MCP server (30 seconds)

Create or edit `.bob/mcp.json` in your Bob IDE workspace and add:

```json
{
  "mcpServers": {
    "grid-guardian": {
      "type": "streamable-http",
      "url": "https://grid-guardian-production.up.railway.app/mcp",
      "alwaysAllow": [
        "get_asset_health",
        "get_weather_risk",
        "rank_at_risk_assets",
        "generate_crew_plan",
        "generate_incident_brief"
      ]
    }
  }
}
```

Then ask Bob: *"Give me a full incident brief for the duty manager"*

---

## Local Setup Prerequisites

Only needed if running locally. The live deployment above requires nothing.

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

### Option A — IBM Bob (Primary Interface)

Bob is the primary interface. Start the MCP server and talk to the grid
using natural language.

**Step 1: Configure Bob Integration**
Because `.bob` folders are ignored in the repository template, you must manually create the Bob configuration file on your machine:
```bash
# In the root of the project:
mkdir .bob
cp mcp.example.json .bob/mcp.json
```
*CRITICAL:* Open `.bob/mcp.json` and replace `<ABSOLUTE_PATH_TO_YOUR_CLONED_REPO>` with the actual absolute path to where you cloned this repository on your machine. Also ensure the `command` correctly points to your python executable (e.g., `python`, `python3`, or the absolute path to your virtual environment's python).

**Step 2: Start the MCP server**
```bash
cd src
# (Ensure venv is activated)
python -m mcp_server
```

**Step 3: Open IBM Bob** in the repo root directory.
The `grid-guardian` MCP server in `.bob/mcp.json` will now register automatically.

**Sample queries to try:**
```
"What assets are at risk right now?"
"Give me the full health report for TX-001"
"What is the current weather risk for the grid?"
"Deploy crews to the highest-risk assets"
"Give me a full incident brief for the duty manager"
```

> See [`docs/bob-demo.md`](../docs/bob-demo.md) for the full live session
> transcript with real output from all 5 MCP tools.

---

### Option B — React Dashboard (Visual Interface, Local Dev)

You will need two terminal windows.

**Terminal 1: Start the Unified Backend Server**
```bash
cd src
# (Ensure venv is activated)
python -m api.server
# Serves: REST API at :8001/api/*, MCP at :8001/mcp
```

**Terminal 2: Start the React Frontend (dev mode)**
```bash
cd src/frontend
npm run dev
```

The dashboard will be available at: `http://localhost:5173`

**To test the full production layout locally** (FastAPI serving built React):
```bash
# Build the frontend first
cd src/frontend && npm run build && cd ..
# Then start the unified server — it auto-detects the dist folder
python -m api.server
# Visit http://localhost:8001 — dashboard + /mcp + /api/* all on one port
```

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
| Chat Panel says "STUB MODE" | Expected when `WATSONX_API_KEY` is not set. Add real credentials to `src/.env` for live Granite generation. |
| Connection Refused in UI | Ensure `python -m api.server` is running on port 8001. |
| Bob says "No tools found" | Check `.bob/mcp.json` exists and uses the correct URL or local path. |
| Railway deploy fails | Check build logs — ensure `nixpacks.toml` is present and `npm run build` succeeds. |
| MCP /mcp returns 404 | FastMCP version must be ≥ 2.0.0; run `pip install fastmcp --upgrade` |
