import pytest
import pandas as pd
import numpy as np
from risk_engine.model import (
    train_model,
    predict_failure_probability,
    get_top_contributing_signals,
    get_feature_columns
)

@pytest.fixture
def mock_training_data():
    # Create a small synthetic dataset for training
    np.random.seed(42)
    n_samples = 100
    
    # Healthy assets
    healthy = pd.DataFrame({
        "asset_id": [f"H_{i}" for i in range(80)],
        "temperature_c_latest": np.random.normal(50, 5, 80),
        "vibration_mm_s_latest": np.random.normal(2, 0.5, 80),
        "label_failure_within_14d": 0
    })
    
    # Failing assets (higher temp, higher vibration)
    failing = pd.DataFrame({
        "asset_id": [f"F_{i}" for i in range(20)],
        "temperature_c_latest": np.random.normal(80, 5, 20),
        "vibration_mm_s_latest": np.random.normal(8, 1.0, 20),
        "label_failure_within_14d": 1
    })
    
    df = pd.concat([healthy, failing], ignore_index=True)
    # Shuffle
    return df.sample(frac=1, random_state=42).reset_index(drop=True)

def test_get_feature_columns(mock_training_data):
    cols = get_feature_columns(mock_training_data)
    assert "asset_id" not in cols
    assert "label_failure_within_14d" not in cols
    assert "temperature_c_latest" in cols
    assert "vibration_mm_s_latest" in cols

def test_model_training_and_prediction(mock_training_data):
    # Train
    model = train_model(mock_training_data)
    assert hasattr(model, "feature_names_")
    
    # Predict on the same data
    probs = predict_failure_probability(model, mock_training_data)
    
    # Check that predictions exist for all assets
    assert len(probs) == len(mock_training_data)
    
    # Check that failing assets get higher probability on average
    failing_probs = [probs[asset_id] for asset_id in probs if asset_id.startswith("F_")]
    healthy_probs = [probs[asset_id] for asset_id in probs if asset_id.startswith("H_")]
    
    assert np.mean(failing_probs) > np.mean(healthy_probs)

def test_top_contributing_signals(mock_training_data):
    model = train_model(mock_training_data)
    
    # Get a failing asset
    failing_id = mock_training_data[mock_training_data["label_failure_within_14d"] == 1]["asset_id"].iloc[0]
    
    signals = get_top_contributing_signals(model, mock_training_data, failing_id, top_n=2)
    assert len(signals) <= 2
    
    # The signals returned should be strings
    for signal in signals:
        assert isinstance(signal, str)
