"""
Grid Guardian — REST API Backend
==================================

Thin FastAPI layer that wraps the MCP tool functions as HTTP endpoints
for the React frontend. This is separate from the MCP server (stdio) —
both call the same underlying Python functions.

Endpoints:
  GET  /api/topology           → grid topology + risk scores
  GET  /api/ranked-assets      → ranked asset list
  GET  /api/asset/{id}/health  → single-asset health assessment
  GET  /api/weather            → weather forecast + risk
  GET  /api/crew-plan          → crew pre-positioning plan
  POST /api/chat               → incident brief (narrative)

Run:
  python -m api.server
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.tools.get_asset_health import get_asset_health
from mcp_server.tools.get_weather_risk import get_weather_risk
from mcp_server.tools.rank_at_risk_assets import rank_at_risk_assets
from mcp_server.tools.generate_crew_plan import generate_crew_plan
from mcp_server.tools.generate_incident_brief import generate_incident_brief
from data.weather_client import WeatherClientError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Grid Guardian API",
    description="REST API for the Grid Guardian frontend dashboard",
    version="1.0.0",
)

# Allow CORS from the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to generated data
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/topology")
def api_topology():
    """Return grid topology with risk scores merged in."""
    try:
        # Load raw topology
        with open(DATA_DIR / "grid_topology.json", "r", encoding="utf-8") as f:
            topology = json.load(f)

        # Get risk scores for all assets
        risk_data = rank_at_risk_assets(top_n=100)
        risk_by_id = {
            a["asset_id"]: a for a in risk_data["ranked_assets"]
        }

        # Merge risk scores into nodes
        for node in topology["nodes"]:
            risk = risk_by_id.get(node["id"], {})
            node["combined_priority_score"] = risk.get("combined_priority_score", 0)
            node["failure_probability_14d"] = risk.get("failure_probability_14d", 0)
            node["blast_radius_score"] = risk.get("blast_radius_score", 0)

        return topology

    except Exception as e:
        logger.exception("Error loading topology")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ranked-assets")
def api_ranked_assets(top_n: int = Query(default=25, ge=1)):
    """Return ranked asset list."""
    try:
        return rank_at_risk_assets(top_n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error ranking assets")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/asset/{asset_id}/health")
def api_asset_health(asset_id: str):
    """Return health details for a single asset."""
    try:
        return get_asset_health(asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting health for {asset_id}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather")
def api_weather(
    lat: float = Query(default=22.31),
    lon: float = Query(default=73.18),
    days: int = Query(default=7, ge=1, le=16),
):
    """Return weather forecast for a location."""
    try:
        return get_weather_risk(lat, lon, days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WeatherClientError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Error fetching weather")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crew-plan")
def api_crew_plan():
    """Return crew pre-positioning plan."""
    try:
        return generate_crew_plan()
    except Exception as e:
        logger.exception("Error generating crew plan")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def api_chat(body: dict = None):
    """Generate an incident brief (narrative response)."""
    try:
        top_n = 5
        if body and "top_n" in body:
            top_n = int(body["top_n"])
        return generate_incident_brief(top_n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error generating brief")
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("MCP_SERVER_PORT", "8001"))
    print(f"Starting Grid Guardian API on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
