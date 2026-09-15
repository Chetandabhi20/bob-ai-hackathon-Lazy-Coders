"""
Grid Guardian MCP Server
=========================

Exposes Phase 2's risk engine functionality as callable MCP tools, so Bob
(or any MCP-aware chat interface) can invoke them.

Tools registered:
  - get_asset_health(asset_id)      -> single-asset health assessment
  - get_weather_risk(lat, lon)      -> real-time weather forecast + risk flag
  - rank_at_risk_assets(top_n)      -> ranked list by combined priority score
  - generate_crew_plan(...)         -> crew pre-positioning assignments
  - generate_incident_brief(top_n)  -> end-to-end narrative brief (Phase 4)

Run modes:
  python -m mcp_server              (stdio transport — for local Bob)
  Mounted at /mcp via api/server.py (Streamable HTTP — for remote Bob)

The `mcp` instance is exported so api/server.py can mount it as an ASGI
app at the /mcp path, enabling remote Bob connections over HTTP.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load src/.env before any tool module is imported so that WATSONX_API_KEY
# and friends are available when the MCP server process is spawned by Bob.
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP

from mcp_server.tools.get_asset_health import (
    get_asset_health as _get_asset_health,
)
from mcp_server.tools.get_weather_risk import (
    get_weather_risk as _get_weather_risk,
)
from mcp_server.tools.rank_at_risk_assets import (
    rank_at_risk_assets as _rank_at_risk_assets,
)
from mcp_server.tools.generate_crew_plan import (
    generate_crew_plan as _generate_crew_plan,
)
from mcp_server.tools.generate_incident_brief import (
    generate_incident_brief as _generate_incident_brief,
)


# Create the MCP server instance.
# Exported as `mcp` so api/server.py can call mcp.http_app() to mount
# the Streamable HTTP transport at /mcp for remote Bob connections.
mcp = FastMCP(
    "Grid Guardian",
    instructions=(
        "You are connected to Grid Guardian, an AI-powered electrical grid "
        "risk-assessment system. Use the available tools to query real-time "
        "asset health, weather risk, ranked failure predictions, crew deployment "
        "plans, and generate natural-language incident briefs for grid operators."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: get_asset_health
# ---------------------------------------------------------------------------
@mcp.tool
def get_asset_health(asset_id: str) -> dict:
    """Retrieve the current health assessment for a single grid asset.

    Returns the asset's most recent sensor readings, 14-day failure
    probability, blast-radius impact score, and top contributing risk
    signals.

    Args:
        asset_id: The grid asset identifier (e.g. "TX-001", "FDR-003",
                  "SUB-002"). Must exist in the grid topology.
    """
    return _get_asset_health(asset_id)


# ---------------------------------------------------------------------------
# Tool 2: get_weather_risk
# ---------------------------------------------------------------------------
@mcp.tool
def get_weather_risk(lat: float, lon: float, days: int = 7) -> dict:
    """Fetch a real-time weather forecast and assess storm risk for a location.

    Returns the forecast for the next N days plus an overall risk flag
    (low/moderate/high) indicating the worst expected weather conditions.

    Args:
        lat: Latitude of the location (e.g. 22.31).
        lon: Longitude of the location (e.g. 73.18).
        days: Number of forecast days, 1-16. Default 7.
    """
    return _get_weather_risk(lat, lon, days)


# ---------------------------------------------------------------------------
# Tool 3: rank_at_risk_assets
# ---------------------------------------------------------------------------
@mcp.tool
def rank_at_risk_assets(top_n: int = 10) -> dict:
    """Get the ranked list of at-risk grid assets by combined priority score.

    Combines 14-day failure probability with blast-radius impact to produce
    a priority-ordered list. Higher scores mean greater risk to the grid.

    Args:
        top_n: Maximum number of assets to return. Default 10.
    """
    return _rank_at_risk_assets(top_n)


# ---------------------------------------------------------------------------
# Tool 4: generate_crew_plan
# ---------------------------------------------------------------------------
@mcp.tool
def generate_crew_plan(crew_locations: list[dict] | None = None) -> dict:
    """Generate an optimized crew pre-positioning plan for at-risk assets.

    Assigns maintenance crews to the highest-priority assets using greedy
    nearest-crew assignment. Returns crew assignments with ETAs and
    human-readable reasons.

    Args:
        crew_locations: Optional list of crew starting positions. Each must
            have keys: crew_id, lat, lon (and optionally name). If omitted,
            uses the 4 default depot locations around Vadodara.
    """
    return _generate_crew_plan(crew_locations)


# ---------------------------------------------------------------------------
# Tool 5: generate_incident_brief
# ---------------------------------------------------------------------------
@mcp.tool
def generate_incident_brief(top_n: int = 5) -> dict:
    """Generate a natural-language incident brief from live risk data.

    Runs the full pipeline end-to-end: risk ranking -> crew deployment ->
    narrative summary via watsonx.ai (or a structured stub if watsonx
    credentials are not yet configured).

    Args:
        top_n: Number of top-ranked assets to include in the brief. Default 5.
    """
    return _generate_incident_brief(top_n)
