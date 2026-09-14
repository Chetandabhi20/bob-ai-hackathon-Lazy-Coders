"""
Blast-Radius Graph Scoring for Grid Guardian
=============================================

THE KEY DIFFERENTIATOR of this project.

Most failure-prediction systems rank assets by probability alone. We add a
second dimension: if this asset fails, how bad is it? An asset with a 40%
failure probability that would black out a hospital with no backup path should
outrank an asset with 60% probability that only affects a small, redundant
feeder.

Algorithm overview:
-------------------
1. Build a directed graph from the grid topology, following power flow
   direction (substation → transformer → feeder). Tie edges are excluded
   from the main flow — they represent backup paths.

2. For each asset, compute the "blast radius" — what happens if it fails:
   a. DOWNSTREAM CUSTOMERS: BFS/DFS from the failed node to find all
      downstream nodes that lose power. Sum their customers_served.
   b. UNPROTECTED CUSTOMERS: Of those downstream, how many are on nodes
      with has_backup_path=False? These are fully exposed.
   c. CRITICAL LOADS: Collect all criticality_flags from affected nodes.
   d. BACKUP DISCOUNT: If the failing node itself has a backup path,
      the entire outage severity is reduced (power can be re-routed,
      though with switching delay).

3. Combine into a blast_radius_score (0–100 scale):

   FORMULA (documented here for docs/solution-overview.md):
   -------------------------------------------------------
   customer_impact = unprotected_customers / total_grid_customers * 70

   criticality_impact = sum of:
     - 10 points per "hospital" flag downstream
     - 8  points per "water_treatment" flag downstream
     - 5  points per "data_center" flag downstream
     - 3  points per "school" flag downstream

   raw_score = customer_impact + criticality_impact

   If the failing node has has_backup_path=True:
     blast_radius_score = raw_score * BACKUP_DISCOUNT_FACTOR (0.3)
   Else:
     blast_radius_score = raw_score

   Final score is capped at 100.

   Why this formula?
   - The 70/30 split between customer count and criticality ensures that
     sheer number of affected people matters most, but critical infrastructure
     provides meaningful differentiation when customer counts are similar.
   - The backup discount (0.3 = 70% reduction) reflects that backup paths
     don't eliminate impact (switching takes 15-60 minutes, backup may have
     reduced capacity) but dramatically reduce duration and severity.
"""

import json
from collections import defaultdict
from pathlib import Path


# Criticality weights — points added per flag type found downstream
CRITICALITY_WEIGHTS = {
    "hospital": 10.0,
    "water_treatment": 8.0,
    "data_center": 5.0,
    "school": 3.0,
}

# If the failing node has a backup path, multiply score by this factor
# (0.3 = 70% reduction in severity)
BACKUP_DISCOUNT_FACTOR = 0.3

# Customer impact is scaled to this many points (out of 100)
CUSTOMER_IMPACT_MAX_POINTS = 70.0


def load_topology(topology_path: Path) -> dict:
    """Load the grid topology from JSON."""
    with open(topology_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_power_flow_graph(topology: dict) -> dict:
    """
    Build a directed adjacency list representing power flow.

    Only includes "primary" and "feeder" edges (the main power delivery
    structure). "tie" edges are backup paths and are excluded — they don't
    carry power under normal operation.

    Returns:
        Dict mapping each node_id to a list of downstream node_ids.
    """
    children = defaultdict(list)
    for edge in topology["edges"]:
        if edge["type"] in ("primary", "feeder"):
            children[edge["from"]].append(edge["to"])
    return dict(children)


def get_node_map(topology: dict) -> dict[str, dict]:
    """Build a lookup dict from node_id to node data."""
    return {node["id"]: node for node in topology["nodes"]}


def find_downstream_nodes(
    node_id: str,
    children_graph: dict,
) -> list[str]:
    """
    BFS to find all nodes downstream of node_id (excluding node_id itself).

    These are the nodes that would lose power if node_id fails.
    """
    downstream = []
    queue = list(children_graph.get(node_id, []))
    visited = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        downstream.append(current)
        queue.extend(children_graph.get(current, []))

    return downstream


def compute_blast_radius(
    node_id: str,
    topology: dict,
    children_graph: dict | None = None,
    node_map: dict | None = None,
) -> dict:
    """
    Compute the blast radius for a single asset.

    Args:
        node_id: The asset that hypothetically fails.
        topology: Full topology dict.
        children_graph: Optional pre-built power flow graph.
        node_map: Optional pre-built node lookup.

    Returns:
        Dict with:
          - downstream_node_ids: list of affected node IDs
          - total_customers_at_risk: all customers downstream + self
          - unprotected_customers: customers on nodes without backup
          - critical_loads_at_risk: list of unique criticality flags
          - has_backup_path: whether the failing node has backup
          - blast_radius_score: float 0–100
    """
    if children_graph is None:
        children_graph = build_power_flow_graph(topology)
    if node_map is None:
        node_map = get_node_map(topology)

    if node_id not in node_map:
        raise ValueError(f"Unknown node_id: {node_id}")

    failing_node = node_map[node_id]
    downstream_ids = find_downstream_nodes(node_id, children_graph)

    # Include the failing node itself in the affected set
    affected_nodes = [failing_node] + [node_map[nid] for nid in downstream_ids]

    # Total customers at risk
    total_customers = sum(n["customers_served"] for n in affected_nodes)

    # Unprotected customers (no backup path)
    unprotected_customers = sum(
        n["customers_served"] for n in affected_nodes if not n["has_backup_path"]
    )

    # Critical loads at risk (unique flags across all affected nodes)
    critical_loads = set()
    for n in affected_nodes:
        critical_loads.update(n["criticality_flags"])
    critical_loads = sorted(critical_loads)

    # Total grid customers (for normalization)
    total_grid_customers = sum(n["customers_served"] for n in topology["nodes"])

    # --- Compute blast_radius_score ---

    # Customer impact component (0 to CUSTOMER_IMPACT_MAX_POINTS)
    customer_impact = (
        unprotected_customers / total_grid_customers * CUSTOMER_IMPACT_MAX_POINTS
        if total_grid_customers > 0
        else 0.0
    )

    # Criticality impact component
    criticality_impact = sum(
        CRITICALITY_WEIGHTS.get(flag, 1.0) for flag in critical_loads
    )

    raw_score = customer_impact + criticality_impact

    # Apply backup discount if the failing node itself has backup
    if failing_node["has_backup_path"]:
        blast_radius_score = raw_score * BACKUP_DISCOUNT_FACTOR
    else:
        blast_radius_score = raw_score

    # Cap at 100
    blast_radius_score = min(100.0, round(blast_radius_score, 1))

    return {
        "node_id": node_id,
        "downstream_node_ids": downstream_ids,
        "total_customers_at_risk": total_customers,
        "unprotected_customers": unprotected_customers,
        "critical_loads_at_risk": critical_loads,
        "has_backup_path": failing_node["has_backup_path"],
        "blast_radius_score": blast_radius_score,
    }


def compute_all_blast_radii(topology: dict) -> list[dict]:
    """
    Compute blast radius for every node in the topology.

    Returns list sorted by blast_radius_score descending.
    """
    children_graph = build_power_flow_graph(topology)
    node_map = get_node_map(topology)

    results = []
    for node in topology["nodes"]:
        result = compute_blast_radius(
            node["id"], topology, children_graph, node_map
        )
        results.append(result)

    results.sort(key=lambda r: r["blast_radius_score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# CLI entry point for verification
# ---------------------------------------------------------------------------
def main():
    topology_path = Path(__file__).parent.parent / "data" / "generated" / "grid_topology.json"
    if not topology_path.exists():
        raise FileNotFoundError(f"Topology not found: {topology_path}")

    topology = load_topology(topology_path)
    results = compute_all_blast_radii(topology)

    print("--- Blast Radius Scores (sorted by score) ---")
    print(f"{'Rank':<5} {'Node':<10} {'Score':>6} {'Customers':>10} {'Unprotected':>12} {'Backup':>7} {'Critical Loads'}")
    print("-" * 90)

    for i, r in enumerate(results, 1):
        backup = "YES" if r["has_backup_path"] else "no"
        critical = ", ".join(r["critical_loads_at_risk"]) if r["critical_loads_at_risk"] else "-"
        print(
            f"{i:<5} {r['node_id']:<10} {r['blast_radius_score']:>6.1f} "
            f"{r['total_customers_at_risk']:>10,} {r['unprotected_customers']:>12,} "
            f"{backup:>7}   {critical}"
        )

    # Verification: SUB-001 should score highest (hospital + water treatment,
    # most customers, no backup). A small leaf feeder with backup (FDR-005)
    # should score much lower.
    scores = {r["node_id"]: r["blast_radius_score"] for r in results}

    print(f"\n--- Verification ---")
    print(f"SUB-001 (hospital+water, no backup): {scores['SUB-001']:.1f}")
    print(f"FDR-005 (no critical, HAS backup):   {scores['FDR-005']:.1f}")
    print(f"FDR-012 (leaf, no critical):          {scores['FDR-012']:.1f}")

    assert scores["SUB-001"] > scores["FDR-005"], (
        "SUB-001 should score higher than FDR-005"
    )
    assert scores["SUB-001"] > scores["FDR-012"], (
        "SUB-001 should score higher than FDR-012"
    )
    # SUB-001 should be #1 or #2
    top_3 = [r["node_id"] for r in results[:3]]
    assert "SUB-001" in top_3, f"SUB-001 should be in top 3, got {top_3}"

    print("[OK] Blast radius scoring verified - high-impact nodes rank correctly")


if __name__ == "__main__":
    main()
