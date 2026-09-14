"""
get_asset_health — MCP Tool
=============================

Retrieve the current health assessment for a single grid asset, including
its most recent sensor readings, failure probability, blast radius impact
score, and top contributing risk signals.

Backend: rank_assets() + sensor CSV + topology JSON
"""

import json
from pathlib import Path

import pandas as pd

from risk_engine import rank_assets
from risk_engine.model import SIMULATION_CURRENT_DATE


# Paths to generated data
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "generated"
_TOPOLOGY_PATH = _DATA_DIR / "grid_topology.json"
_READINGS_PATH = _DATA_DIR / "sensor_readings.csv"


def get_asset_health(asset_id: str) -> dict:
    """
    Retrieve a full health assessment for a single grid asset.

    Args:
        asset_id: The grid asset identifier (e.g. "TX-001", "FDR-003", "SUB-002").
                  Must exist in grid_topology.json.

    Returns:
        Dict with asset metadata, latest sensor readings, failure probability,
        blast radius score, and top contributing signals.

    Raises:
        ValueError: If asset_id is not found in the grid topology.
    """
    # Validate asset_id exists in topology
    with open(_TOPOLOGY_PATH, "r", encoding="utf-8") as f:
        topology = json.load(f)

    node_map = {n["id"]: n for n in topology["nodes"]}
    if asset_id not in node_map:
        valid_ids = sorted(node_map.keys())
        raise ValueError(
            f"Asset '{asset_id}' not found in grid topology. "
            f"Valid asset IDs: {valid_ids}"
        )

    node = node_map[asset_id]

    # Get ranked risk data (includes probability, blast radius, signals)
    ranked = rank_assets()
    asset_risk = None
    for entry in ranked:
        if entry["asset_id"] == asset_id:
            asset_risk = entry
            break

    if asset_risk is None:
        raise ValueError(
            f"Asset '{asset_id}' exists in topology but was not scored by "
            f"the risk engine. This is unexpected — check sensor data."
        )

    # Get latest sensor reading for this asset (up to SIMULATION_CURRENT_DATE)
    readings_df = pd.read_csv(_READINGS_PATH)
    readings_df["timestamp"] = pd.to_datetime(readings_df["timestamp"])

    asset_readings = readings_df[
        (readings_df["asset_id"] == asset_id)
        & (readings_df["timestamp"] <= pd.Timestamp(SIMULATION_CURRENT_DATE))
    ].sort_values("timestamp", ascending=False)

    latest_readings = None
    if not asset_readings.empty:
        row = asset_readings.iloc[0]
        latest_readings = {
            "timestamp": row["timestamp"].isoformat(),
            "temperature_c": round(float(row["temperature_c"]), 1),
            "vibration_mm_s": round(float(row["vibration_mm_s"]), 2),
            "partial_discharge_pc": round(float(row["partial_discharge_pc"]), 1),
            "oil_quality_index": round(float(row["oil_quality_index"]), 1),
        }

    return {
        "asset_id": asset_id,
        "asset_name": node["name"],
        "asset_type": node["type"],
        "latest_readings": latest_readings,
        "failure_probability_14d": asset_risk["failure_probability_14d"],
        "blast_radius_score": asset_risk["blast_radius_score"],
        "customers_at_risk": asset_risk["customers_at_risk"],
        "critical_loads_at_risk": asset_risk["critical_loads_at_risk"],
        "has_backup_path": asset_risk["has_backup_path"],
        "combined_priority_score": asset_risk["combined_priority_score"],
        "top_contributing_signals": asset_risk["top_contributing_signals"],
    }
