"""
Synthetic Sensor Data Generator for Grid Guardian
==================================================

Generates realistic sensor readings for all assets in the grid topology.
90 days of daily readings per asset.

DEGRADATION SIGNATURES (injected for ~16% of assets):
------------------------------------------------------
Assets chosen to fail are deliberately picked to create interesting
blast-radius contrasts in Phase 2:

  - TX-001 (Riverside North Transformer, hospital area, installed 1998)
    Failure date: day 75. Degradation starts day 50.
    Pattern: aging transformer — slow temperature rise, vibration increase,
    partial discharge spike, oil quality decline.

  - FDR-003 (Water Plant Feeder, water_treatment, installed 2003)
    Failure date: day 80. Degradation starts day 58.
    Pattern: insulation breakdown — partial discharge rises sharply,
    temperature moderately elevated, vibration steady then spikes late.

  - TX-005 (Industrial East Transformer, data_center, installed 2010)
    Failure date: day 85. Degradation starts day 65.
    Pattern: mechanical wear — vibration climbs steadily, temperature
    follows, oil quality drops, partial discharge rises last.

  - FDR-013 (School Zone Feeder, school, installed 2009)
    Failure date: day 70. Degradation starts day 48.
    Pattern: weather-accelerated aging — all sensors degrade together
    over a longer window, simulating cumulative weather stress.

Healthy assets get baseline readings with realistic daily noise (Gaussian)
around stable means. Means vary slightly per asset to avoid all healthy
assets looking identical.

Schema: see PROJECT_GUIDE.md Section 5.2
  asset_id, timestamp, temperature_c, vibration_mm_s, partial_discharge_pc,
  oil_quality_index, label_failure_within_14d
"""

import csv
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


# Reproducible output
RANDOM_SEED = 42

# Simulation window
NUM_DAYS = 90
START_DATE = datetime(2026, 6, 15)

# Healthy baseline ranges (mean, noise_std)
HEALTHY_BASELINES = {
    "temperature_c": (55.0, 3.0),
    "vibration_mm_s": (2.5, 0.4),
    "partial_discharge_pc": (15.0, 3.0),
    "oil_quality_index": (85.0, 2.0),
}

# Which assets will fail, with their degradation parameters
FAILING_ASSETS = {
    "TX-001": {
        "failure_day": 75,
        "degradation_start_day": 50,
        "description": "aging transformer — slow multi-sensor degradation",
        # How much each sensor deviates at failure point (added to baseline)
        "temp_rise": 25.0,       # reaches ~80C
        "vibration_rise": 6.0,   # reaches ~8.5 mm/s
        "pd_rise": 45.0,         # reaches ~60 pC
        "oil_drop": 40.0,        # drops to ~45
    },
    "FDR-003": {
        "failure_day": 80,
        "degradation_start_day": 58,
        "description": "insulation breakdown — partial discharge leads",
        "temp_rise": 15.0,
        "vibration_rise": 3.5,
        "pd_rise": 60.0,         # PD dominates
        "oil_drop": 30.0,
    },
    "TX-005": {
        "failure_day": 85,
        "degradation_start_day": 65,
        "description": "mechanical wear — vibration leads",
        "temp_rise": 18.0,
        "vibration_rise": 8.0,   # vibration dominates
        "pd_rise": 30.0,
        "oil_drop": 35.0,
    },
    "FDR-013": {
        "failure_day": 70,
        "degradation_start_day": 48,
        "description": "weather-accelerated aging — all sensors degrade together",
        "temp_rise": 20.0,
        "vibration_rise": 5.0,
        "pd_rise": 40.0,
        "oil_drop": 38.0,
    },
}


def load_asset_ids(topology_path: Path) -> list[str]:
    """Load all asset IDs from the grid topology JSON."""
    with open(topology_path, "r", encoding="utf-8") as f:
        topology = json.load(f)
    return [node["id"] for node in topology["nodes"]]


def _sigmoid(x: float) -> float:
    """Sigmoid function for smooth degradation curves."""
    return 1.0 / (1.0 + math.exp(-x))


def _degradation_factor(day: int, start_day: int, failure_day: int) -> float:
    """
    Returns a value between 0.0 (no degradation) and 1.0 (full degradation).
    Uses a sigmoid curve centered at the midpoint of the degradation window
    for a realistic gradual-then-accelerating pattern.
    """
    if day < start_day:
        return 0.0
    if day >= failure_day:
        return 1.0

    window = failure_day - start_day
    midpoint = start_day + window / 2.0
    # Scale so sigmoid goes from ~0.05 at start to ~0.95 at failure
    x = 6.0 * (day - midpoint) / window
    return _sigmoid(x)


def generate_healthy_reading(
    rng: random.Random,
    asset_id: str,
    base_offset: dict[str, float],
) -> dict[str, float]:
    """Generate one day of healthy sensor readings with noise."""
    return {
        "temperature_c": round(
            HEALTHY_BASELINES["temperature_c"][0]
            + base_offset["temperature_c"]
            + rng.gauss(0, HEALTHY_BASELINES["temperature_c"][1]),
            1,
        ),
        "vibration_mm_s": round(
            max(
                0.1,
                HEALTHY_BASELINES["vibration_mm_s"][0]
                + base_offset["vibration_mm_s"]
                + rng.gauss(0, HEALTHY_BASELINES["vibration_mm_s"][1]),
            ),
            2,
        ),
        "partial_discharge_pc": round(
            max(
                1.0,
                HEALTHY_BASELINES["partial_discharge_pc"][0]
                + base_offset["partial_discharge_pc"]
                + rng.gauss(0, HEALTHY_BASELINES["partial_discharge_pc"][1]),
            ),
            1,
        ),
        "oil_quality_index": round(
            min(
                100.0,
                max(
                    50.0,
                    HEALTHY_BASELINES["oil_quality_index"][0]
                    + base_offset["oil_quality_index"]
                    + rng.gauss(0, HEALTHY_BASELINES["oil_quality_index"][1]),
                ),
            ),
            1,
        ),
    }


def generate_degrading_reading(
    rng: random.Random,
    day: int,
    params: dict,
    base_offset: dict[str, float],
) -> dict[str, float]:
    """Generate one day of sensor readings with degradation applied."""
    factor = _degradation_factor(
        day, params["degradation_start_day"], params["failure_day"]
    )

    # Start from healthy baseline + per-asset offset, then add degradation
    temp = (
        HEALTHY_BASELINES["temperature_c"][0]
        + base_offset["temperature_c"]
        + factor * params["temp_rise"]
        + rng.gauss(0, HEALTHY_BASELINES["temperature_c"][1])
    )
    vib = (
        HEALTHY_BASELINES["vibration_mm_s"][0]
        + base_offset["vibration_mm_s"]
        + factor * params["vibration_rise"]
        + rng.gauss(0, HEALTHY_BASELINES["vibration_mm_s"][1])
    )
    pd = (
        HEALTHY_BASELINES["partial_discharge_pc"][0]
        + base_offset["partial_discharge_pc"]
        + factor * params["pd_rise"]
        + rng.gauss(0, HEALTHY_BASELINES["partial_discharge_pc"][1])
    )
    oil = (
        HEALTHY_BASELINES["oil_quality_index"][0]
        + base_offset["oil_quality_index"]
        - factor * params["oil_drop"]
        + rng.gauss(0, HEALTHY_BASELINES["oil_quality_index"][1])
    )

    return {
        "temperature_c": round(temp, 1),
        "vibration_mm_s": round(max(0.1, vib), 2),
        "partial_discharge_pc": round(max(1.0, pd), 1),
        "oil_quality_index": round(min(100.0, max(10.0, oil)), 1),
    }


def generate_sensor_data(asset_ids: list[str]) -> list[dict]:
    """Generate the full sensor readings dataset."""
    rng = random.Random(RANDOM_SEED)
    rows = []

    # Give each asset a small random baseline offset so they don't all look
    # identical when healthy. Seeded per-asset for reproducibility.
    asset_offsets = {}
    for asset_id in asset_ids:
        asset_rng = random.Random(hash(asset_id) + RANDOM_SEED)
        asset_offsets[asset_id] = {
            "temperature_c": asset_rng.uniform(-5, 5),
            "vibration_mm_s": asset_rng.uniform(-0.5, 0.5),
            "partial_discharge_pc": asset_rng.uniform(-4, 4),
            "oil_quality_index": asset_rng.uniform(-5, 5),
        }

    for asset_id in asset_ids:
        is_failing = asset_id in FAILING_ASSETS
        params = FAILING_ASSETS.get(asset_id)
        offset = asset_offsets[asset_id]

        for day in range(NUM_DAYS):
            timestamp = (START_DATE + timedelta(days=day)).strftime(
                "%Y-%m-%dT08:00:00"
            )

            if is_failing:
                readings = generate_degrading_reading(rng, day, params, offset)
                # Label: 1 if this reading is within 14 days of failure
                days_to_failure = params["failure_day"] - day
                label = 1 if 0 < days_to_failure <= 14 else 0
            else:
                readings = generate_healthy_reading(rng, asset_id, offset)
                label = 0

            rows.append(
                {
                    "asset_id": asset_id,
                    "timestamp": timestamp,
                    "temperature_c": readings["temperature_c"],
                    "vibration_mm_s": readings["vibration_mm_s"],
                    "partial_discharge_pc": readings["partial_discharge_pc"],
                    "oil_quality_index": readings["oil_quality_index"],
                    "label_failure_within_14d": label,
                }
            )

    return rows


def validate_sensor_data(rows: list[dict], asset_ids: list[str]) -> None:
    """Run validation checks on the generated sensor data."""

    # Check all asset_ids present
    generated_ids = {r["asset_id"] for r in rows}
    missing = set(asset_ids) - generated_ids
    if missing:
        raise ValueError(f"Missing asset_ids in sensor data: {missing}")

    # Check row count
    expected_rows = len(asset_ids) * NUM_DAYS
    assert len(rows) == expected_rows, (
        f"Expected {expected_rows} rows, got {len(rows)}"
    )

    # Check failure rate
    assets_with_failures = {
        r["asset_id"] for r in rows if r["label_failure_within_14d"] == 1
    }
    failure_pct = len(assets_with_failures) / len(asset_ids) * 100
    assert failure_pct >= 15, (
        f"Need >=15% assets with failures, got {failure_pct:.1f}%"
    )

    # Sanity check: failing assets should have higher mean sensor values
    # in their pre-failure window vs healthy assets
    failing_pre = [
        r for r in rows
        if r["asset_id"] in assets_with_failures
        and r["label_failure_within_14d"] == 1
    ]
    healthy = [
        r for r in rows
        if r["asset_id"] not in assets_with_failures
    ]

    def mean_val(data: list[dict], key: str) -> float:
        return sum(r[key] for r in data) / len(data)

    fail_temp = mean_val(failing_pre, "temperature_c")
    healthy_temp = mean_val(healthy, "temperature_c")
    fail_vib = mean_val(failing_pre, "vibration_mm_s")
    healthy_vib = mean_val(healthy, "vibration_mm_s")
    fail_oil = mean_val(failing_pre, "oil_quality_index")
    healthy_oil = mean_val(healthy, "oil_quality_index")

    print("[OK] Validation passed:")
    print(f"  Total rows: {len(rows)}")
    print(f"  Assets: {len(asset_ids)}")
    print(f"  Assets with failures: {len(assets_with_failures)} ({failure_pct:.0f}%)")
    print(f"  Failing assets: {sorted(assets_with_failures)}")
    print(f"  Sensor contrast (pre-failure vs healthy):")
    print(f"    Temperature: {fail_temp:.1f} vs {healthy_temp:.1f}")
    print(f"    Vibration:   {fail_vib:.2f} vs {healthy_vib:.2f}")
    print(f"    Oil quality:  {fail_oil:.1f} vs {healthy_oil:.1f}")

    # These should show clear separation
    assert fail_temp > healthy_temp, "Failing assets should be hotter"
    assert fail_vib > healthy_vib, "Failing assets should vibrate more"
    assert fail_oil < healthy_oil, "Failing assets should have worse oil"


def main():
    """Generate and save the sensor readings dataset."""

    topology_path = Path(__file__).parent / "generated" / "grid_topology.json"
    if not topology_path.exists():
        raise FileNotFoundError(
            f"Grid topology not found at {topology_path}. "
            "Run generate_grid_topology.py first."
        )

    asset_ids = load_asset_ids(topology_path)
    print(f"Loaded {len(asset_ids)} assets from topology")

    rows = generate_sensor_data(asset_ids)
    validate_sensor_data(rows, asset_ids)

    # Write CSV
    output_path = Path(__file__).parent / "generated" / "sensor_readings.csv"
    fieldnames = [
        "asset_id",
        "timestamp",
        "temperature_c",
        "vibration_mm_s",
        "partial_discharge_pc",
        "oil_quality_index",
        "label_failure_within_14d",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    file_size = output_path.stat().st_size
    print(f"\n[OK] Sensor readings written to: {output_path}")
    print(f"  File size: {file_size:,} bytes")
    print(f"  Rows: {len(rows):,}")


if __name__ == "__main__":
    main()
