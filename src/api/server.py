"""
Grid Guardian — Unified Server
================================

Single process that serves:
  1. REST API      — /api/*      (React dashboard backend)
  2. MCP HTTP      — /mcp        (Streamable HTTP for remote Bob connections)
  3. Static files  — /           (pre-built Vite/React frontend)

This unified layout means one Railway service, one URL, handles everything:
  - Judges visit https://<app>.up.railway.app  → see the React dashboard
  - Judges point Bob at https://<app>.up.railway.app/mcp → use all 5 tools

Endpoints:
  GET  /api/topology           → grid topology + risk scores
  GET  /api/ranked-assets      → ranked asset list
  GET  /api/asset/{id}/health  → single-asset health assessment
  GET  /api/weather            → weather forecast + risk
  GET  /api/crew-plan          → crew pre-positioning plan
  POST /api/chat               → conversational AI with intent routing
  ANY  /mcp                    → FastMCP Streamable HTTP transport (Bob)
  GET  /                       → React SPA (production build)

Run locally:
  python -m api.server
"""

import json
import logging
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mcp_server.tools.get_asset_health import get_asset_health
from mcp_server.tools.get_weather_risk import get_weather_risk
from mcp_server.tools.rank_at_risk_assets import rank_at_risk_assets
from mcp_server.tools.generate_crew_plan import generate_crew_plan
from mcp_server.tools.generate_incident_brief import generate_incident_brief
from data.weather_client import WeatherClientError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Grid Guardian API",
    description=(
        "REST API + MCP Streamable HTTP server for Grid Guardian. "
        "Connect IBM Bob to /mcp for live grid intelligence tools."
    ),
    version="1.0.0",
)

# CORS: allow Vite dev server locally AND any Railway/deployed origin
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8001",
]
_RAILWAY_URL = os.environ.get("RAILWAY_STATIC_URL", "")
if _RAILWAY_URL:
    _ALLOWED_ORIGINS.append(f"https://{_RAILWAY_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.up\.railway\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to generated data
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

# Path to Vite production build — served as static files in production
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


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


# ── Intent routing helpers ────────────────────────────────────────────────

# Known asset ID patterns present in grid_topology.json
_ASSET_ID_RE = re.compile(
    r'\b((?:TX|FDR|SUB)-\d{3})\b', re.IGNORECASE
)

# Lat/lon for the Vadodara grid (used as default for weather queries)
_DEFAULT_LAT = 22.31
_DEFAULT_LON = 73.18

def _route_intent(message: str) -> dict:
    """
    Parse the user message and return the appropriate tool response.

    Intents (checked in order):
      1. Asset health  — message contains a valid asset ID (e.g. "TX-001")
      2. Weather risk  — message contains weather/storm/temperature keywords
      3. Crew plan     — message contains crew/deploy/dispatch keywords
      4. Incident brief (default fallback)
    """
    text = message.strip()

    # ── Intent 1: specific asset health ──────────────────────────────────
    match = _ASSET_ID_RE.search(text)
    if match:
        asset_id = match.group(1).upper()
        try:
            data = get_asset_health(asset_id)
        except ValueError as exc:
            return {
                "intent": "asset_health",
                "asset_id": asset_id,
                "error": str(exc),
                "brief": str(exc),
            }
        prob_pct = round(data["failure_probability_14d"] * 100, 1)
        backup = "no backup path — fully exposed" if not data["has_backup_path"] else "backup path available"
        critical = ", ".join(data["critical_loads_at_risk"]) or "none"
        signals = ", ".join(data["top_contributing_signals"][:4])
        brief = (
            f"**{data['asset_name']} ({asset_id})** — {data['asset_type'].capitalize()}\n\n"
            f"**Combined Priority Score:** {data['combined_priority_score']:.1f} / 100\n"
            f"**Failure Probability (14d):** {prob_pct}%\n"
            f"**Blast Radius Score:** {data['blast_radius_score']:.1f}\n"
            f"**Customers at Risk:** {data['customers_at_risk']:,}\n"
            f"**Critical Loads:** {critical}\n"
            f"**Backup Path:** {backup}\n\n"
            f"**Top Risk Signals:** {signals}\n\n"
        )
        if data.get("latest_readings"):
            r = data["latest_readings"]
            brief += (
                f"**Latest Readings** (as of {r['timestamp'][:10]}):\n"
                f"- Temperature: {r['temperature_c']}°C\n"
                f"- Vibration: {r['vibration_mm_s']} mm/s\n"
                f"- Partial Discharge: {r['partial_discharge_pc']} pC\n"
                f"- Oil Quality Index: {r['oil_quality_index']}\n"
            )
        return {
            "intent": "asset_health",
            "asset_id": asset_id,
            "brief": brief,
            "data": data,
        }

    # ── Intent 2: weather risk ────────────────────────────────────────────
    weather_keywords = {"weather", "storm", "wind", "rain", "temperature", "forecast", "heatwave", "heat"}
    if any(kw in text.lower() for kw in weather_keywords):
        try:
            data = get_weather_risk(_DEFAULT_LAT, _DEFAULT_LON, days=7)
        except WeatherClientError as exc:
            return {"intent": "weather", "error": str(exc), "brief": f"Weather API error: {exc}"}
        risk = data["overall_risk"].upper()
        days_summary = []
        for d in data["forecast"][:5]:
            days_summary.append(
                f"- {d['date']}: max {d['temp_max_c']}°C, "
                f"wind {d['wind_speed_kph']} kph, "
                f"precip {d['precip_mm']} mm — **{d['storm_risk']}** risk"
            )
        brief = (
            f"**Weather Risk for Grid Area** (Lat {_DEFAULT_LAT}, Lon {_DEFAULT_LON})\n\n"
            f"**Overall 7-Day Risk: {risk}**\n\n"
            + "\n".join(days_summary)
            + "\n\n"
            + (
                "⚠️ **High storm risk detected.** Assets without backup paths are especially "
                "vulnerable — consider pre-positioning crews now."
                if data["overall_risk"] == "high"
                else "Storm conditions are within normal operational tolerance."
            )
        )
        return {"intent": "weather", "brief": brief, "data": data}

    # ── Intent 3: crew deployment plan ───────────────────────────────────
    crew_keywords = {"crew", "deploy", "dispatch", "assignment", "eta", "maintenance", "send", "position"}
    if any(kw in text.lower() for kw in crew_keywords):
        data = generate_crew_plan()
        lines = []
        for a in data["assignments"]:
            lines.append(
                f"- **{a['crew_id']}** → **{a['assigned_asset_id']}** "
                f"(rank #{a['priority_rank']}, ETA {a['eta_minutes']} min)\n"
                f"  _{a['reason']}_"
            )
        unassigned = data.get("unassigned_high_risk_assets", [])
        brief = (
            f"**Current Crew Deployment Plan**\n\n"
            + "\n".join(lines)
        )
        if unassigned:
            brief += (
                f"\n\n⚠️ **Unassigned High-Risk Assets:** {', '.join(unassigned)}\n"
                f"Additional crew resources are needed to cover these assets."
            )
        return {
            "intent": "crew_plan",
            "brief": brief,
            "crew_assignments": len(data["assignments"]),
            "data": data,
        }

    # ── Intent 4: default — full incident brief ───────────────────────────
    result = generate_incident_brief(5)
    result["intent"] = "incident_brief"
    return result


@app.post("/api/chat")
def api_chat(body: dict = None):
    """
    Conversational AI endpoint with intent routing.

    Accepts a JSON body with a 'message' field (the user's typed query).
    Routes to the correct tool based on intent detected in the message:
      - Asset ID mentioned  → get_asset_health
      - Weather keywords    → get_weather_risk
      - Crew keywords       → generate_crew_plan
      - Anything else       → generate_incident_brief (full brief)
    """
    try:
        message = ""
        if body and "message" in body:
            message = str(body["message"])
        return _route_intent(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in chat routing")
        raise HTTPException(status_code=500, detail=str(e))


# ── MCP Streamable HTTP endpoint ──────────────────────────────────────────
# Mount FastMCP's ASGI app at /mcp so remote Bob clients can connect via:
#   { "type": "streamable-http", "url": "https://<host>/mcp" }

def _build_mcp_asgi():
    """Build the FastMCP ASGI app that handles Streamable HTTP transport."""
    from mcp_server.server import mcp
    return mcp.http_app(path="/")   # path is relative to the mount point

try:
    _mcp_asgi = _build_mcp_asgi()
    app.mount("/mcp", _mcp_asgi)
    logger.info("MCP Streamable HTTP endpoint mounted at /mcp")
except Exception as _mcp_err:
    logger.warning("Could not mount MCP ASGI app: %s", _mcp_err)


# ── Static files (production React build) ─────────────────────────────────
# Only mounted when the Vite dist folder exists (i.e. in production on Railway
# or after running `npm run build` locally). In local dev, Vite's own dev
# server handles the frontend.

if _FRONTEND_DIST.exists():
    # Mount static assets (JS/CSS chunks) BEFORE the catch-all route
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):
        """Serve the React SPA for any non-API, non-MCP route."""
        # Don't intercept API or MCP routes
        if full_path.startswith("api/") or full_path.startswith("mcp"):
            raise HTTPException(status_code=404)
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        raise HTTPException(status_code=404, detail="Frontend not built. Run: cd src/frontend && npm run build")

    logger.info("Serving React SPA from %s", _FRONTEND_DIST)
else:
    logger.info(
        "Frontend dist not found at %s — serving API only. "
        "Run `cd src/frontend && npm run build` to enable the dashboard.",
        _FRONTEND_DIST,
    )


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", os.environ.get("MCP_SERVER_PORT", "8001")))
    print(f"Starting Grid Guardian unified server on http://0.0.0.0:{port}")
    print(f"  Dashboard : http://localhost:{port}/")
    print(f"  API docs  : http://localhost:{port}/docs")
    print(f"  MCP (Bob) : http://localhost:{port}/mcp")
    uvicorn.run(app, host="0.0.0.0", port=port)
