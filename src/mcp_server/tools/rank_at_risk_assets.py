"""
rank_at_risk_assets — MCP Tool
================================

Return the ranked list of grid assets sorted by combined priority score
(failure probability weighted with blast-radius impact).

Backend: risk_engine.rank_assets()
"""

from risk_engine import rank_assets
from risk_engine.model import SIMULATION_CURRENT_DATE


def rank_at_risk_assets(top_n: int = 10) -> dict:
    """
    Get the ranked list of at-risk grid assets by combined priority score.

    Args:
        top_n: Maximum number of assets to return. Default 10.
               Pass a large number (e.g. 100) to get all assets.

    Returns:
        Dict with ranked_assets list (Section 5.5 schema), total_assets count,
        and as_of_date for traceability.

    Raises:
        ValueError: On invalid top_n.
    """
    if top_n < 1:
        raise ValueError(
            f"Invalid top_n: {top_n}. Must be a positive integer (>= 1)."
        )

    # Get all ranked assets first (for total count), then slice
    all_ranked = rank_assets()
    total_assets = len(all_ranked)

    # Apply top_n limit
    ranked_subset = all_ranked[:top_n]

    return {
        "ranked_assets": ranked_subset,
        "total_assets": total_assets,
        "as_of_date": str(SIMULATION_CURRENT_DATE.date()),
    }
