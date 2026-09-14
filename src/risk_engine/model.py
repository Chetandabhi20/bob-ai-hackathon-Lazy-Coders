"""
Failure-Probability Model for Grid Guardian
============================================

Trains a gradient-boosted tree classifier to predict whether an asset will
fail within the next 14 days, based on the sensor-derived features from
features.py.

Model choice: sklearn GradientBoostingClassifier
-------------------------------------------------
Why not XGBoost/LightGBM?
  - sklearn is already a dependency; no extra install needed.
  - For synthetic data with 25 features and ~2000 training rows, sklearn's
    implementation is more than adequate.
  - Simpler dependency = more reproducible setup for judges.

Class imbalance handling:
  - Only ~2.7% of training rows are positive (label=1). We handle this with
    sample_weight computed from class frequencies, which is equivalent to
    class_weight='balanced' but works with GradientBoostingClassifier
    (which doesn't natively support class_weight).

Feature importance → top_contributing_signals:
  - Uses the model's built-in feature_importances_ (mean decrease in impurity).
  - Maps raw feature names to human-readable signal descriptions for the
    `top_contributing_signals` field in the risk score output (Section 5.5).
"""

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

from data.generate_sensor_data import START_DATE
from risk_engine.features import (
    compute_all_features,
    compute_training_features,
    load_sensor_readings,
    load_topology_ages,
)

# "Now" in our simulation. Set to day 66 of the 90-day sensor window —
# this is before the earliest failure (FDR-013 at day 70) so the model
# can predict approaching failures rather than evaluating post-failure data
# where degradation trends have already plateaued.
# At day 66: FDR-013 (4 days to fail), TX-001 (9 days), FDR-003 (14 days)
# are all actively degrading. TX-005 (19 days) is just starting.
SIMULATION_CURRENT_DATE = START_DATE + timedelta(days=66)


# Feature name → human-readable signal description
# Used to populate top_contributing_signals in the risk output
FEATURE_SIGNAL_MAP = {
    "temperature_c_latest": "elevated_temperature",
    "temperature_c_mean_7d": "sustained_high_temperature",
    "temperature_c_mean_30d": "chronic_high_temperature",
    "temperature_c_slope_14d": "rising_temperature_trend",
    "temperature_c_std_14d": "unstable_temperature",
    "temperature_c_delta_ratio": "temperature_worsening_recently",
    "vibration_mm_s_latest": "elevated_vibration",
    "vibration_mm_s_mean_7d": "sustained_high_vibration",
    "vibration_mm_s_mean_30d": "chronic_high_vibration",
    "vibration_mm_s_slope_14d": "rising_vibration_trend",
    "vibration_mm_s_std_14d": "unstable_vibration",
    "vibration_mm_s_delta_ratio": "vibration_worsening_recently",
    "partial_discharge_pc_latest": "elevated_partial_discharge",
    "partial_discharge_pc_mean_7d": "sustained_high_partial_discharge",
    "partial_discharge_pc_mean_30d": "chronic_high_partial_discharge",
    "partial_discharge_pc_slope_14d": "rising_partial_discharge",
    "partial_discharge_pc_std_14d": "unstable_partial_discharge",
    "partial_discharge_pc_delta_ratio": "partial_discharge_worsening_recently",
    "oil_quality_index_latest": "low_oil_quality",
    "oil_quality_index_mean_7d": "sustained_low_oil_quality",
    "oil_quality_index_mean_30d": "chronic_low_oil_quality",
    "oil_quality_index_slope_14d": "declining_oil_quality",
    "oil_quality_index_std_14d": "unstable_oil_quality",
    "oil_quality_index_delta_ratio": "oil_quality_worsening_recently",
    "asset_age_years": "aging_equipment",
}

# Columns that are NOT features (metadata / label)
NON_FEATURE_COLS = {"asset_id", "label_failure_within_14d"}

# Default model hyperparameters — tuned for small synthetic dataset
MODEL_PARAMS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "min_samples_leaf": 5,
    "random_state": 42,
}

# Path for the serialized trained model
MODEL_PATH = Path(__file__).parent / "trained_model.pkl"


def get_feature_columns(df) -> list[str]:
    """Get the ordered list of feature column names from a DataFrame."""
    return [c for c in df.columns if c not in NON_FEATURE_COLS]


def train_model(train_df) -> GradientBoostingClassifier:
    """
    Train the failure-probability model.

    Args:
        train_df: DataFrame from compute_training_features() with feature
            columns + asset_id + label_failure_within_14d.

    Returns:
        Trained GradientBoostingClassifier.
    """
    feature_cols = get_feature_columns(train_df)
    X = train_df[feature_cols].values
    y = train_df["label_failure_within_14d"].values.astype(int)

    # Compute sample weights to handle class imbalance
    # Equivalent to class_weight='balanced'
    n_samples = len(y)
    n_positive = y.sum()
    n_negative = n_samples - n_positive
    weight_positive = n_samples / (2.0 * n_positive) if n_positive > 0 else 1.0
    weight_negative = n_samples / (2.0 * n_negative) if n_negative > 0 else 1.0
    sample_weights = np.where(y == 1, weight_positive, weight_negative)

    model = GradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(X, y, sample_weight=sample_weights)

    # Store feature column names on the model for later use
    model.feature_names_ = feature_cols

    return model


def predict_failure_probability(model: GradientBoostingClassifier, features_df) -> dict[str, float]:
    """
    Predict failure probability for each asset.

    Args:
        model: Trained model from train_model().
        features_df: DataFrame from compute_all_features() with one row
            per asset.

    Returns:
        Dict of asset_id -> failure_probability (0.0 to 1.0).
    """
    feature_cols = model.feature_names_
    X = features_df[feature_cols].values
    probabilities = model.predict_proba(X)[:, 1]  # probability of class 1

    return dict(zip(features_df["asset_id"], probabilities))


def get_top_contributing_signals(
    model: GradientBoostingClassifier,
    features_df,
    asset_id: str,
    top_n: int = 3,
) -> list[str]:
    """
    Get the top contributing signals for a specific asset's prediction.

    Uses the model's feature importances weighted by how far each feature
    value deviates from the dataset mean (in standard deviations). This
    gives asset-specific explanations, not just global importances.

    Args:
        model: Trained model.
        features_df: DataFrame with features for all assets.
        asset_id: Which asset to explain.
        top_n: Number of top signals to return.

    Returns:
        List of human-readable signal names (from FEATURE_SIGNAL_MAP).
    """
    feature_cols = model.feature_names_
    importances = model.feature_importances_

    # Get this asset's feature values
    asset_row = features_df[features_df["asset_id"] == asset_id]
    if asset_row.empty:
        return []

    asset_values = asset_row[feature_cols].values[0]

    # Compute how much each feature deviates from the mean
    means = features_df[feature_cols].mean().values
    stds = features_df[feature_cols].std().values
    stds = np.where(stds == 0, 1.0, stds)  # avoid division by zero

    deviations = np.abs((asset_values - means) / stds)

    # Combined score: global importance * local deviation
    scores = importances * deviations

    # Get top N feature indices
    top_indices = np.argsort(scores)[::-1][:top_n]

    # Map to human-readable names
    signals = []
    for idx in top_indices:
        feat_name = feature_cols[idx]
        signal = FEATURE_SIGNAL_MAP.get(feat_name, feat_name)
        signals.append(signal)

    return signals


def save_model(model: GradientBoostingClassifier, path: Path = MODEL_PATH) -> None:
    """Serialize the trained model to disk."""
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"[OK] Model saved to: {path}")


def load_model(path: Path = MODEL_PATH) -> GradientBoostingClassifier:
    """Load a trained model from disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {path}. Run model training first."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# CLI entry point: train, evaluate, save
# ---------------------------------------------------------------------------
def main():
    data_dir = Path(__file__).parent.parent / "data"
    topology_path = data_dir / "generated" / "grid_topology.json"
    readings_path = data_dir / "generated" / "sensor_readings.csv"

    print("Loading data...")
    asset_ages = load_topology_ages(topology_path)
    readings_df = load_sensor_readings(readings_path)

    print("Computing training features...")
    train_df = compute_training_features(readings_df, asset_ages)
    feature_cols = get_feature_columns(train_df)
    print(f"Training set: {train_df.shape[0]} rows, {len(feature_cols)} features")

    print("\nTraining model...")
    model = train_model(train_df)

    # Cross-validation sanity check
    X = train_df[feature_cols].values
    y = train_df["label_failure_within_14d"].values.astype(int)
    cv_scores = cross_val_score(model, X, y, cv=3, scoring="roc_auc")
    print(f"Cross-validation ROC AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    # Predict on features at simulation "now" (one row per asset)
    print(f"\nComputing features at simulation date: {SIMULATION_CURRENT_DATE.date()}...")
    features_df = compute_all_features(readings_df, asset_ages, as_of_date=SIMULATION_CURRENT_DATE)
    probs = predict_failure_probability(model, features_df)

    # Display results
    failing_ids = {"TX-001", "FDR-003", "TX-005", "FDR-013"}
    print("\n--- Predicted failure probabilities ---")
    print(f"{'Asset':<12} {'Prob':>9} {'Actual':>8} {'Signals'}")
    print("-" * 75)
    for asset_id in sorted(probs, key=probs.get, reverse=True):
        prob = probs[asset_id]
        actual = "FAIL" if asset_id in failing_ids else "healthy"
        signals = get_top_contributing_signals(model, features_df, asset_id, top_n=3)
        print(f"{asset_id:<12} {prob:>9.4f} {actual:>8}   {', '.join(signals)}")

    # Verify: failing assets should have higher mean probability
    fail_probs = [probs[a] for a in failing_ids]
    healthy_probs = [probs[a] for a in probs if a not in failing_ids]
    print(f"\nMean prob (failing):  {np.mean(fail_probs):.3f}")
    print(f"Mean prob (healthy): {np.mean(healthy_probs):.3f}")
    assert np.mean(fail_probs) > np.mean(healthy_probs), (
        "Failing assets should have higher mean probability!"
    )
    print("[OK] Failing assets have meaningfully higher probabilities")

    # Feature importance
    print("\n--- Top 10 feature importances ---")
    imp_indices = np.argsort(model.feature_importances_)[::-1][:10]
    for idx in imp_indices:
        name = feature_cols[idx]
        imp = model.feature_importances_[idx]
        signal = FEATURE_SIGNAL_MAP.get(name, name)
        print(f"  {imp:.4f}  {signal} ({name})")

    # Save the trained model
    save_model(model)
    print("\n[OK] Training complete.")


if __name__ == "__main__":
    main()
