"""
Feature Engineering for Grid Guardian Risk Model
=================================================

Transforms raw sensor time series into model-ready features per asset.

Feature design rationale:
-------------------------
The failure-probability model needs to distinguish assets heading toward
failure from healthy ones, using only sensor readings available at prediction
time (no future-looking). Each feature is computed from a trailing window
of readings up to a given "as of" date.

Feature groups:
  1. LATEST VALUES — most recent reading for each sensor. Captures current state.
  2. ROLLING MEANS — 7-day and 30-day means. Captures short vs long-term baselines.
  3. TREND SLOPES — linear regression slope over trailing 14 days for each sensor.
     This is the most important feature group: a rising slope in temperature,
     vibration, or partial discharge (or falling slope in oil quality) is the
     primary degradation signature we injected in the synthetic data.
  4. VOLATILITY — standard deviation over trailing 14 days. Unstable readings
     can indicate intermittent faults.
  5. DELTA RATIOS — ratio of 7-day mean to 30-day mean. Values > 1 for temp/
     vibration/PD (or < 1 for oil quality) indicate recent worsening.
  6. ASSET AGE — years since installation, from topology. Older equipment
     has higher base failure risk.

Total: 4 sensors x 6 features + 1 age = 25 features per asset.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


SENSOR_COLUMNS = [
    "temperature_c",
    "vibration_mm_s",
    "partial_discharge_pc",
    "oil_quality_index",
]

# How many trailing days to use for each window
WINDOW_SHORT = 7
WINDOW_LONG = 30
WINDOW_TREND = 14


def _linear_slope(values: np.ndarray) -> float:
    """
    Compute the slope of a simple linear regression over the values.
    Values are assumed to be evenly spaced in time (one per day).
    Returns slope in units-per-day.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    # Use least-squares: slope = cov(x,y) / var(x)
    x_mean = x.mean()
    y_mean = values.mean()
    numerator = ((x - x_mean) * (values - y_mean)).sum()
    denominator = ((x - x_mean) ** 2).sum()
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def compute_features_for_asset(
    asset_readings: pd.DataFrame,
    as_of_date: datetime,
    asset_age_years: float,
) -> dict[str, float]:
    """
    Compute features for a single asset using readings up to as_of_date.

    Args:
        asset_readings: DataFrame with sensor columns, sorted by timestamp,
            filtered to one asset.
        as_of_date: Compute features using readings on or before this date.
        asset_age_years: Age of the asset in years (from topology install_year).

    Returns:
        Dict of feature_name -> float. Never contains NaN; missing windows
        are filled with the available data or sensible defaults.
    """
    # Filter to readings up to as_of_date
    mask = asset_readings["timestamp"] <= as_of_date
    available = asset_readings.loc[mask].copy()

    features = {}

    for sensor in SENSOR_COLUMNS:
        values = available[sensor].values

        # Latest value
        features[f"{sensor}_latest"] = float(values[-1]) if len(values) > 0 else 0.0

        # Short-term mean (7 days)
        short_window = values[-WINDOW_SHORT:] if len(values) >= WINDOW_SHORT else values
        features[f"{sensor}_mean_7d"] = float(short_window.mean()) if len(short_window) > 0 else 0.0

        # Long-term mean (30 days)
        long_window = values[-WINDOW_LONG:] if len(values) >= WINDOW_LONG else values
        features[f"{sensor}_mean_30d"] = float(long_window.mean()) if len(long_window) > 0 else 0.0

        # Trend slope (14-day linear regression)
        trend_window = values[-WINDOW_TREND:] if len(values) >= WINDOW_TREND else values
        features[f"{sensor}_slope_14d"] = _linear_slope(trend_window)

        # Volatility (14-day std)
        features[f"{sensor}_std_14d"] = (
            float(trend_window.std()) if len(trend_window) > 1 else 0.0
        )

        # Delta ratio: short-term mean / long-term mean
        long_mean = features[f"{sensor}_mean_30d"]
        short_mean = features[f"{sensor}_mean_7d"]
        if long_mean != 0:
            features[f"{sensor}_delta_ratio"] = short_mean / long_mean
        else:
            features[f"{sensor}_delta_ratio"] = 1.0

    # Asset age
    features["asset_age_years"] = asset_age_years

    return features


def load_topology_ages(topology_path: Path) -> dict[str, float]:
    """Load install years from topology and compute asset ages."""
    with open(topology_path, "r", encoding="utf-8") as f:
        topology = json.load(f)

    current_year = datetime.now().year
    return {
        node["id"]: float(current_year - node["install_year"])
        for node in topology["nodes"]
    }


def load_sensor_readings(csv_path: Path) -> pd.DataFrame:
    """Load sensor readings CSV into a DataFrame with parsed timestamps."""
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["asset_id", "timestamp"]).reset_index(drop=True)
    return df


def compute_all_features(
    readings_df: pd.DataFrame,
    asset_ages: dict[str, float],
    as_of_date: datetime | None = None,
) -> pd.DataFrame:
    """
    Compute features for all assets using the latest available data.

    Args:
        readings_df: Full sensor readings DataFrame.
        asset_ages: Dict of asset_id -> age_in_years.
        as_of_date: Optional cutoff date. If None, uses the latest timestamp
            in the data.

    Returns:
        DataFrame with one row per asset, columns = feature names + asset_id.
    """
    if as_of_date is None:
        as_of_date = readings_df["timestamp"].max()

    rows = []
    for asset_id in sorted(readings_df["asset_id"].unique()):
        asset_data = readings_df[readings_df["asset_id"] == asset_id]
        age = asset_ages.get(asset_id, 0.0)

        features = compute_features_for_asset(asset_data, as_of_date, age)
        features["asset_id"] = asset_id
        rows.append(features)

    result = pd.DataFrame(rows)

    # Verify no NaNs
    nan_cols = result.columns[result.isna().any()].tolist()
    if nan_cols:
        raise ValueError(f"NaN found in feature columns: {nan_cols}")

    return result


def compute_training_features(
    readings_df: pd.DataFrame,
    asset_ages: dict[str, float],
) -> pd.DataFrame:
    """
    Compute features for every labeled timestep in the data, for model training.

    For each (asset_id, timestamp) row, computes features using only readings
    up to that timestamp (no future data leakage).

    Returns:
        DataFrame with features + asset_id + label_failure_within_14d.
    """
    rows = []
    grouped = readings_df.groupby("asset_id")

    for asset_id, asset_data in grouped:
        age = asset_ages.get(asset_id, 0.0)
        asset_sorted = asset_data.sort_values("timestamp")

        # Only compute features for rows where we have enough history
        # (at least WINDOW_SHORT days)
        for idx in range(WINDOW_SHORT, len(asset_sorted)):
            row = asset_sorted.iloc[idx]
            as_of = row["timestamp"]
            label = int(row["label_failure_within_14d"])

            features = compute_features_for_asset(asset_sorted, as_of, age)
            features["asset_id"] = asset_id
            features["label_failure_within_14d"] = label
            rows.append(features)

    result = pd.DataFrame(rows)

    # Verify no NaNs in feature columns (label can't be NaN by construction)
    feature_cols = [c for c in result.columns if c not in ("asset_id", "label_failure_within_14d")]
    nan_cols = result[feature_cols].columns[result[feature_cols].isna().any()].tolist()
    if nan_cols:
        raise ValueError(f"NaN found in training feature columns: {nan_cols}")

    return result


# ---------------------------------------------------------------------------
# CLI entry point for verification
# ---------------------------------------------------------------------------
def main():
    """Compute and display features for verification."""
    data_dir = Path(__file__).parent.parent / "data"
    topology_path = data_dir / "generated" / "grid_topology.json"
    readings_path = data_dir / "generated" / "sensor_readings.csv"

    print("Loading data...")
    asset_ages = load_topology_ages(topology_path)
    readings_df = load_sensor_readings(readings_path)

    print(f"Assets: {len(asset_ages)}, Readings: {len(readings_df)}")

    # Compute latest features (one row per asset)
    print("\n--- Latest features (one row per asset) ---")
    features_df = compute_all_features(readings_df, asset_ages)
    print(f"Shape: {features_df.shape}")
    print(f"Columns: {list(features_df.columns)}")
    print(f"NaN count: {features_df.isna().sum().sum()}")

    # Compare failing vs healthy assets
    failing_ids = {"TX-001", "FDR-003", "TX-005", "FDR-013"}
    fail_df = features_df[features_df["asset_id"].isin(failing_ids)]
    healthy_df = features_df[~features_df["asset_id"].isin(failing_ids)]

    numeric_cols = [c for c in features_df.columns if c != "asset_id"]

    print("\n--- Feature means: FAILING vs HEALTHY ---")
    print(f"{'Feature':<35} {'Failing':>10} {'Healthy':>10} {'Ratio':>8}")
    print("-" * 65)
    for col in numeric_cols:
        f_mean = fail_df[col].mean()
        h_mean = healthy_df[col].mean()
        ratio = f_mean / h_mean if h_mean != 0 else float("inf")
        print(f"{col:<35} {f_mean:>10.2f} {h_mean:>10.2f} {ratio:>8.2f}")

    # Compute training features
    print("\n--- Training features ---")
    train_df = compute_training_features(readings_df, asset_ages)
    print(f"Shape: {train_df.shape}")
    pos = train_df["label_failure_within_14d"].sum()
    neg = len(train_df) - pos
    print(f"Positive labels: {pos}, Negative: {neg}, Ratio: {pos/(pos+neg)*100:.1f}%")


if __name__ == "__main__":
    main()
