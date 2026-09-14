"""
Crew Pre-Positioning Planner for Grid Guardian
===============================================

Given a ranked list of at-risk assets and crew starting locations, produces
an optimized crew assignment plan matching PROJECT_GUIDE Section 5.6.

Algorithm: greedy nearest-available-crew assignment
---------------------------------------------------
1. Sort assets by combined_priority_score descending (from rank_assets).
2. For each asset in priority order:
   a. Find the nearest AVAILABLE crew (not yet assigned).
   b. Compute ETA based on straight-line distance * road factor / speed.
   c. Assign that crew to this asset with a human-readable reason.
3. Any high-priority assets that couldn't be covered (no crews left) go
   into unassigned_high_risk_assets.

Travel time estimation:
  - Straight-line (Haversine) distance x 1.4 road factor / 30 km/h urban speed.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from risk_engine import rank_assets


# Crew depot locations around Vadodara
DEFAULT_CREW_LOCATIONS = [
    {"crew_id": "CREW-A", "name": "Central Depot", "lat": 22.3050, "lon": 73.1900},
    {"crew_id": "CREW-B", "name": "North Industrial Depot", "lat": 22.3500, "lon": 73.2100},
    {"crew_id": "CREW-C", "name": "East University Depot", "lat": 22.2900, "lon": 73.2500},
    {"crew_id": "CREW-D", "name": "Mobile Reserve Unit", "lat": 22.3200, "lon": 73.2200},
]

HIGH_RISK_THRESHOLD = 5.0
ROAD_FACTOR = 1.4
URBAN_SPEED_KPH = 30.0
EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute straight-line distance between two lat/lon points in km."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def _estimate_eta_minutes(crew_lat, crew_lon, asset_lat, asset_lon) -> int:
    """Estimate travel time in minutes from crew to asset."""
    straight_km = _haversine_km(crew_lat, crew_lon, asset_lat, asset_lon)
    road_km = straight_km * ROAD_FACTOR
    hours = road_km / URBAN_SPEED_KPH
    return max(1, round(hours * 60))


def _build_reason(asset: dict, rank: int) -> str:
    """Generate a human-readable reason for the crew assignment."""
    parts = []
    if rank == 1:
        parts.append("Highest combined_priority_score")
    else:
        parts.append(f"Priority rank #{rank}")

    prob = asset["failure_probability_14d"]
    if prob > 0.8:
        parts.append("active failure signature detected")
    elif prob > 0.3:
        parts.append("elevated failure risk")

    if not asset["has_backup_path"]:
        parts.append("no backup path")

    if asset["critical_loads_at_risk"]:
        loads = " and ".join(asset["critical_loads_at_risk"])
        parts.append(f"serves {loads}")

    if asset["customers_at_risk"] > 5000:
        parts.append(f"{asset['customers_at_risk']:,} customers at risk")

    return "; ".join(parts)


def generate_crew_plan(
    crew_locations: list[dict] | None = None,
    ranked_assets: list[dict] | None = None,
    max_assignments: int | None = None,
) -> dict:
    """
    Generate a crew pre-positioning plan matching Section 5.6 schema.

    Returns:
        Dict with generated_at, assignments, unassigned_high_risk_assets.
    """
    if crew_locations is None:
        crew_locations = DEFAULT_CREW_LOCATIONS
    if ranked_assets is None:
        ranked_assets = rank_assets()
    if max_assignments is None:
        max_assignments = len(crew_locations)

    # Load topology for asset coordinates
    topology_path = Path(__file__).parent.parent / "data" / "generated" / "grid_topology.json"
    with open(topology_path, "r", encoding="utf-8") as f:
        topology = json.load(f)
    asset_coords = {n["id"]: (n["lat"], n["lon"]) for n in topology["nodes"]}

    available_crews = list(crew_locations)
    assignments = []
    assigned_asset_ids = set()

    # Greedy: iterate assets in priority order, assign nearest available crew
    for rank_idx, asset in enumerate(ranked_assets):
        if not available_crews or len(assignments) >= max_assignments:
            break

        asset_id = asset["asset_id"]
        asset_lat, asset_lon = asset_coords[asset_id]

        best_crew = None
        best_eta = float("inf")
        best_crew_idx = -1

        for idx, crew in enumerate(available_crews):
            eta = _estimate_eta_minutes(crew["lat"], crew["lon"], asset_lat, asset_lon)
            if eta < best_eta:
                best_eta = eta
                best_crew = crew
                best_crew_idx = idx

        if best_crew is None:
            continue

        assignments.append({
            "crew_id": best_crew["crew_id"],
            "assigned_asset_id": asset_id,
            "priority_rank": rank_idx + 1,
            "eta_minutes": best_eta,
            "reason": _build_reason(asset, rank_idx + 1),
        })

        assigned_asset_ids.add(asset_id)
        available_crews.pop(best_crew_idx)

    # High-risk assets that couldn't be covered
    unassigned = [
        asset["asset_id"]
        for asset in ranked_assets
        if asset["asset_id"] not in assigned_asset_ids
        and asset["combined_priority_score"] >= HIGH_RISK_THRESHOLD
    ]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assignments": assignments,
        "unassigned_high_risk_assets": unassigned,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    print("Generating crew pre-positioning plan...\n")
    plan = generate_crew_plan()

    print(f"Generated at: {plan['generated_at']}")
    print(f"\n--- Crew Assignments ({len(plan['assignments'])}) ---")
    print(f"{'Crew':<10} {'Asset':<10} {'Rank':>5} {'ETA':>5} {'Reason'}")
    print("-" * 90)

    for a in plan["assignments"]:
        print(
            f"{a['crew_id']:<10} {a['assigned_asset_id']:<10} "
            f"#{a['priority_rank']:<4} {a['eta_minutes']:>4}m  {a['reason']}"
        )

    print(f"\n--- Unassigned High-Risk Assets ---")
    if plan["unassigned_high_risk_assets"]:
        for asset_id in plan["unassigned_high_risk_assets"]:
            print(f"  {asset_id}")
    else:
        print("  (none)")

    # Verify: no duplicate crews or assets
    crew_ids = [a["crew_id"] for a in plan["assignments"]]
    assert len(crew_ids) == len(set(crew_ids)), "Duplicate crew assignment!"
    asset_ids = [a["assigned_asset_id"] for a in plan["assignments"]]
    assert len(asset_ids) == len(set(asset_ids)), "Duplicate asset assignment!"

    # Verify schema compliance
    required_keys = {"crew_id", "assigned_asset_id", "priority_rank", "eta_minutes", "reason"}
    for a in plan["assignments"]:
        missing = required_keys - set(a.keys())
        assert not missing, f"Missing keys: {missing}"

    print(f"\n[OK] Plan verified: {len(plan['assignments'])} assignments, "
          f"{len(plan['unassigned_high_risk_assets'])} unassigned high-risk assets")


if __name__ == "__main__":
    main()
