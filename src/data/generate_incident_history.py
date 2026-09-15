"""
Historical Incident Generator for Grid Guardian
===============================================

Generates synthetic historical incident (outage) records.

CRITICAL: Internal Consistency
This script reads the failure definitions from generate_sensor_data.py
so that the four assets that experience sensor degradation (TX-001, FDR-003,
TX-005, FDR-013) have matching incident records exactly on the day their
sensor data hits the failure point.

It also generates background historical incidents for other assets to simulate
past outages (weather, vegetation, equipment, unknown).

Schema: see PROJECT_GUIDE.md Section 5.3
  incident_id, asset_id, date, cause, duration_minutes, customers_affected,
  weather_condition_at_time
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Import the exact failure timings from the sensor generator
from data.generate_sensor_data import START_DATE, FAILING_ASSETS, load_asset_ids

RANDOM_SEED = 42

BACKGROUND_INCIDENT_COUNT = 35
CAUSES = ["weather_storm", "vegetation_contact", "equipment_failure", "animal_contact", "unknown"]
WEATHER_CONDITIONS = ["clear", "rain", "heavy_rain", "windy", "thunderstorm"]

def generate_incident_history(topology_path: Path) -> list[dict]:
    rng = random.Random(RANDOM_SEED)
    asset_ids = load_asset_ids(topology_path)
    
    rows = []
    
    # 1. Generate the EXACT incidents corresponding to the sensor failures
    for asset_id, params in FAILING_ASSETS.items():
        failure_date = START_DATE + timedelta(days=params["failure_day"])
        
        # Match the cause to the description from sensor data
        desc = params["description"]
        if "weather" in desc:
            cause = "weather_storm"
            weather = "thunderstorm"
        elif "insulation" in desc:
            cause = "equipment_failure"
            weather = "rain" # Rain often triggers insulation failure
        else:
            cause = "equipment_failure"
            weather = "clear"
            
        rows.append({
            "incident_id": f"INC-{rng.randint(10000, 99999)}",
            "asset_id": asset_id,
            "date": failure_date.strftime("%Y-%m-%d"),
            "cause": cause,
            "duration_minutes": rng.randint(180, 720), # Major failures take longer
            "customers_affected": rng.randint(500, 5000), # Rough estimate, blast_radius calculates exact later
            "weather_condition_at_time": weather
        })
        
    # 2. Generate random background historical incidents
    # Spread these out over the 2 years prior to the simulation window
    for _ in range(BACKGROUND_INCIDENT_COUNT):
        asset_id = rng.choice(asset_ids)
        # Random day between 730 days ago and 10 days before START_DATE
        days_ago = rng.randint(10, 730)
        hist_date = START_DATE - timedelta(days=days_ago)
        
        cause = rng.choice(CAUSES)
        
        # Correlate weather with cause
        if cause == "weather_storm":
            weather = rng.choice(["heavy_rain", "thunderstorm"])
        elif cause == "vegetation_contact":
            weather = rng.choice(["windy", "thunderstorm", "rain"])
        else:
            weather = rng.choice(WEATHER_CONDITIONS)
            
        rows.append({
            "incident_id": f"INC-{rng.randint(10000, 99999)}",
            "asset_id": asset_id,
            "date": hist_date.strftime("%Y-%m-%d"),
            "cause": cause,
            "duration_minutes": rng.randint(30, 240), # Routine incidents are shorter
            "customers_affected": rng.randint(50, 1500),
            "weather_condition_at_time": weather
        })
        
    # Sort by date
    rows.sort(key=lambda x: x["date"])
    return rows

def validate_incident_history(rows: list[dict], topology_path: Path):
    asset_ids = set(load_asset_ids(topology_path))
    
    # Check all asset_ids exist in topology
    for r in rows:
        assert r["asset_id"] in asset_ids, f"Unknown asset_id {r['asset_id']} in incident history"
        
    # Check sensor failure alignment
    for asset_id, params in FAILING_ASSETS.items():
        failure_date = (START_DATE + timedelta(days=params["failure_day"])).strftime("%Y-%m-%d")
        
        # Verify an incident exists for this asset on this exact date
        matching = [r for r in rows if r["asset_id"] == asset_id and r["date"] == failure_date]
        assert len(matching) == 1, f"Failed to find consistent incident record for {asset_id} on {failure_date}"
        
    print(f"[OK] Validation passed: {len(rows)} incidents generated. Sensor failures perfectly aligned.")

def main():
    topology_path = Path(__file__).parent / "generated" / "grid_topology.json"
    if not topology_path.exists():
        raise FileNotFoundError("Run generate_grid_topology.py first.")
        
    rows = generate_incident_history(topology_path)
    validate_incident_history(rows, topology_path)
    
    output_path = Path(__file__).parent / "generated" / "incident_history.csv"
    fieldnames = [
        "incident_id", "asset_id", "date", "cause", "duration_minutes", 
        "customers_affected", "weather_condition_at_time"
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"[OK] Incident history written to: {output_path}")

if __name__ == "__main__":
    main()
