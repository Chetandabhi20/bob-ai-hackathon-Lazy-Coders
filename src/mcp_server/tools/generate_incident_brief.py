"""
generate_incident_brief — MCP Tool
=====================================

Combines risk ranking with the watsonx narrative layer to produce a
natural-language incident brief in a single tool call.

Backend: rank_assets() → generate_crew_plan() → summarize_risk_brief()
"""

from risk_engine import rank_assets
from risk_engine.crew_planner import generate_crew_plan
from mcp_server.watsonx_client import summarize_risk_brief


def generate_incident_brief(top_n: int = 5) -> dict:
    """
    Generate a complete incident brief combining risk ranking, crew
    deployment, and natural-language summary.

    This is the end-to-end tool: it runs the full pipeline from risk
    assessment through crew planning to narrative generation in a single
    call.

    Args:
        top_n: Number of top-ranked assets to include in the brief.
               Default 5.

    Returns:
        Dict with the narrative brief, source data, and metadata.

    Raises:
        ValueError: On invalid top_n.
        RuntimeError: If watsonx credentials are configured but the
            API call fails.
    """
    if top_n < 1:
        raise ValueError(
            f"Invalid top_n: {top_n}. Must be a positive integer (>= 1)."
        )

    # Step 1: Get ranked risk assessment
    ranked = rank_assets()
    top_assets = ranked[:top_n]

    # Step 2: Generate crew plan
    crew_plan = generate_crew_plan()

    # Step 3: Generate natural-language brief
    brief = summarize_risk_brief(ranked, crew_plan)

    return {
        "brief": brief,
        "top_assets_used": len(top_assets),
        "total_assets_assessed": len(ranked),
        "crew_assignments": len(crew_plan.get("assignments", [])),
        "generated_at": crew_plan.get("generated_at", ""),
    }
