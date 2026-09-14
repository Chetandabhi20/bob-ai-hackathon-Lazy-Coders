"""
Risk Engine — Grid Guardian
============================

Package-level API combining failure probability (model.py) and blast-radius
impact scoring (blast_radius.py) into a unified ranked risk output matching
PROJECT_GUIDE Section 5.5.

Combined Priority Score Formula:
  combined_priority_score = (failure_probability_14d * 40) + (blast_radius_score * 0.6)

  - Probability component: 0–40 points (40% weight)
  - Blast radius component: 0–60 points (60% weight)
  - Total: 0–100

  Why 40/60? The project's core differentiator is that blast radius matters
  more than probability alone. An asset with 30% failure probability but a
  blast radius of 80 (hospital, no backup, many customers) should outrank
  one with 90% probability but a blast radius of 5 (small redundant feeder).
"""

from datetime import datetime
from pathlib import Path

from risk_engine.blast_radius import (
    compute_all_blast_radii,
    compute_blast_radius,
    load_topology,
)
from risk_engine.model import (
    SIMULATION_CURRENT_DATE,
    get_top_contributing_signals,
    load_model,
    predict_failure_probability,
)
from risk_engine.features import (
    compute_all_features,
    load_sensor_readings,
    load_topology_ages,
)


# Weight split: probability vs blast radius
PROB_WEIGHT = 40.0    # max 40 points from probability
BLAST_WEIGHT = 0.6    # blast_radius_score * 0.6, max 60 points


def rank_assets(
    topology_path: Path | None = None,
    readings_path: Path | None = None,
    as_of_date: datetime | None = None,
    top_n: int | None = None,
) -> list[dict]:
    """
    Produce the full ranked risk output for all assets.

    Each entry matches PROJECT_GUIDE Section 5.5 schema:
    {
      "asset_id": str,
      "failure_probability_14d": float,
      "blast_radius_score": float,
      "customers_at_risk": int,
      "critical_loads_at_risk": list[str],
      "has_backup_path": bool,
      "combined_priority_score": float,
      "top_contributing_signals": list[str]
    }

    Args:
        topology_path: Path to grid_topology.json. Defaults to generated data.
        readings_path: Path to sensor_readings.csv. Defaults to generated data.
        as_of_date: Evaluation date for features. Defaults to SIMULATION_CURRENT_DATE.
        top_n: If set, return only top N assets. None = return all.

    Returns:
        List of dicts sorted by combined_priority_score descending.
    """
    # Default paths
    data_dir = Path(__file__).parent.parent / "data" / "generated"
    if topology_path is None:
        topology_path = data_dir / "grid_topology.json"
    if readings_path is None:
        readings_path = data_dir / "sensor_readings.csv"
    if as_of_date is None:
        as_of_date = SIMULATION_CURRENT_DATE

    # Load data
    topology = load_topology(topology_path)
    asset_ages = load_topology_ages(topology_path)
    readings_df = load_sensor_readings(readings_path)

    # Compute failure probabilities
    model = load_model()
    features_df = compute_all_features(readings_df, asset_ages, as_of_date=as_of_date)
    probabilities = predict_failure_probability(model, features_df)

    # Compute blast radii
    blast_results = {
        r["node_id"]: r for r in compute_all_blast_radii(topology)
    }

    # Build the ranked output
    ranked = []
    for asset_id in sorted(probabilities.keys()):
        prob = probabilities[asset_id]
        blast = blast_results[asset_id]

        # Combined priority score
        combined = (prob * PROB_WEIGHT) + (blast["blast_radius_score"] * BLAST_WEIGHT)
        combined = min(100.0, round(combined, 1))

        # Top contributing signals from the ML model
        signals = get_top_contributing_signals(model, features_df, asset_id, top_n=3)

        # Add contextual signals based on blast radius
        if not blast["has_backup_path"]:
            signals.append("no_backup_path")
        if blast["critical_loads_at_risk"]:
            for load in blast["critical_loads_at_risk"]:
                signals.append(f"serves_{load}")

        # Deduplicate while preserving order
        seen = set()
        unique_signals = []
        for s in signals:
            if s not in seen:
                seen.add(s)
                unique_signals.append(s)

        ranked.append({
            "asset_id": asset_id,
            "failure_probability_14d": round(prob, 4),
            "blast_radius_score": blast["blast_radius_score"],
            "customers_at_risk": blast["total_customers_at_risk"],
            "critical_loads_at_risk": blast["critical_loads_at_risk"],
            "has_backup_path": blast["has_backup_path"],
            "combined_priority_score": combined,
            "top_contributing_signals": unique_signals,
        })

    # Sort by combined score descending
    ranked.sort(key=lambda r: r["combined_priority_score"], reverse=True)

    if top_n is not None:
        ranked = ranked[:top_n]

    return ranked


# ---------------------------------------------------------------------------
# CLI entry point for verification
# ---------------------------------------------------------------------------
def main():
    print("Computing ranked risk scores for all assets...\n")
    ranked = rank_assets()

    print(f"{'Rank':<5} {'Asset':<10} {'Combined':>9} {'Prob':>6} {'Blast':>6} "
          f"{'Customers':>10} {'Backup':>7} {'Signals'}")
    print("-" * 100)

    for i, r in enumerate(ranked, 1):
        backup = "YES" if r["has_backup_path"] else "no"
        signals = ", ".join(r["top_contributing_signals"][:4])
        print(
            f"{i:<5} {r['asset_id']:<10} {r['combined_priority_score']:>9.1f} "
            f"{r['failure_probability_14d']:>6.3f} {r['blast_radius_score']:>6.1f} "
            f"{r['customers_at_risk']:>10,} {backup:>7}   {signals}"
        )

    # Verify schema compliance
    required_keys = {
        "asset_id", "failure_probability_14d", "blast_radius_score",
        "customers_at_risk", "critical_loads_at_risk", "has_backup_path",
        "combined_priority_score", "top_contributing_signals",
    }
    for r in ranked:
        missing = required_keys - set(r.keys())
        assert not missing, f"Missing keys in {r['asset_id']}: {missing}"

    print(f"\n[OK] Schema verified for all {len(ranked)} assets")
    print(f"[OK] Top asset: {ranked[0]['asset_id']} "
          f"(combined={ranked[0]['combined_priority_score']}, "
          f"prob={ranked[0]['failure_probability_14d']}, "
          f"blast={ranked[0]['blast_radius_score']})")


if __name__ == "__main__":
    main()
