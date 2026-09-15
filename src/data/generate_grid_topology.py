"""
Grid Topology Generator for Grid Guardian
==========================================

Generates a synthetic but realistic radial power distribution grid topology
for a small city (modeled on Vadodara, Gujarat, India — lat ~22.3, lon ~73.2).

Design rationale (important for blast-radius scoring in Phase 2):
- 3 substations form the backbone, each serving different parts of the city
- Substations feed transformers, transformers feed feeders (tree structure)
- Deliberately uneven: SUB-001 (Riverside) serves the most customers including
  a hospital and water treatment plant, with NO backup path — this should be
  the highest blast-radius node in the system
- SUB-002 (Industrial) has a backup tie to SUB-001, making its failures less
  catastrophic despite serving a data center
- SUB-003 (University) is the smallest substation — lower blast radius
- A few cross-ties between feeders provide backup paths for some nodes but
  not others, creating the contrast the blast-radius algorithm needs

The topology is deterministic (no randomness) so it produces identical output
on every run, ensuring reproducibility with the trained model in Phase 2.

Schema: see PROJECT_GUIDE.md Section 5.1
"""

import json
import os
from pathlib import Path


def generate_grid_topology() -> dict:
    """Generate the complete grid topology with nodes and edges."""

    nodes = [
        # =====================================================================
        # SUBSTATIONS (3) — backbone of the grid
        # =====================================================================
        {
            "id": "SUB-001",
            "type": "substation",
            "name": "Riverside Substation",
            "lat": 22.3100,
            "lon": 73.1800,
            "customers_served": 12500,
            "criticality_flags": ["hospital", "water_treatment"],
            "has_backup_path": False,
            "install_year": 1998,
        },
        {
            "id": "SUB-002",
            "type": "substation",
            "name": "Industrial Area Substation",
            "lat": 22.3400,
            "lon": 73.2200,
            "customers_served": 8200,
            "criticality_flags": ["data_center"],
            "has_backup_path": True,  # backup tie to SUB-001
            "install_year": 2010,
        },
        {
            "id": "SUB-003",
            "type": "substation",
            "name": "University Substation",
            "lat": 22.2900,
            "lon": 73.2500,
            "customers_served": 4500,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2015,
        },

        # =====================================================================
        # TRANSFORMERS (9) — step-down from substations
        # =====================================================================

        # --- Fed by SUB-001 (Riverside) ---
        {
            "id": "TX-001",
            "type": "transformer",
            "name": "Riverside North Transformer",
            "lat": 22.3180,
            "lon": 73.1750,
            "customers_served": 4200,
            "criticality_flags": ["hospital"],
            "has_backup_path": False,
            "install_year": 1998,
        },
        {
            "id": "TX-002",
            "type": "transformer",
            "name": "Riverside South Transformer",
            "lat": 22.3020,
            "lon": 73.1830,
            "customers_served": 4800,
            "criticality_flags": ["water_treatment"],
            "has_backup_path": False,
            "install_year": 2003,
        },
        {
            "id": "TX-003",
            "type": "transformer",
            "name": "Riverside East Transformer",
            "lat": 22.3100,
            "lon": 73.1950,
            "customers_served": 3500,
            "criticality_flags": [],
            "has_backup_path": True,  # cross-tie to TX-004
            "install_year": 2001,
        },

        # --- Fed by SUB-002 (Industrial) ---
        {
            "id": "TX-004",
            "type": "transformer",
            "name": "Industrial West Transformer",
            "lat": 22.3450,
            "lon": 73.2100,
            "customers_served": 2800,
            "criticality_flags": [],
            "has_backup_path": True,  # cross-tie to TX-003
            "install_year": 2010,
        },
        {
            "id": "TX-005",
            "type": "transformer",
            "name": "Industrial East Transformer",
            "lat": 22.3380,
            "lon": 73.2350,
            "customers_served": 3200,
            "criticality_flags": ["data_center"],
            "has_backup_path": False,
            "install_year": 2010,
        },
        {
            "id": "TX-006",
            "type": "transformer",
            "name": "Industrial Central Transformer",
            "lat": 22.3420,
            "lon": 73.2200,
            "customers_served": 2200,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2012,
        },

        # --- Fed by SUB-003 (University) ---
        {
            "id": "TX-007",
            "type": "transformer",
            "name": "University Main Transformer",
            "lat": 22.2920,
            "lon": 73.2450,
            "customers_served": 2500,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2015,
        },
        {
            "id": "TX-008",
            "type": "transformer",
            "name": "University Annex Transformer",
            "lat": 22.2850,
            "lon": 73.2550,
            "customers_served": 2000,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2016,
        },
        {
            "id": "TX-009",
            "type": "transformer",
            "name": "Residential Colony Transformer",
            "lat": 22.2980,
            "lon": 73.2600,
            "customers_served": 1800,
            "criticality_flags": ["school"],
            "has_backup_path": False,
            "install_year": 2008,
        },

        # =====================================================================
        # FEEDERS (13) — final distribution to customer clusters
        # =====================================================================

        # --- Fed by TX-001 (Riverside North, hospital area) ---
        {
            "id": "FDR-001",
            "type": "feeder",
            "name": "City Hospital Feeder",
            "lat": 22.3210,
            "lon": 73.1720,
            "customers_served": 1800,
            "criticality_flags": ["hospital"],
            "has_backup_path": False,
            "install_year": 1999,
        },
        {
            "id": "FDR-002",
            "type": "feeder",
            "name": "Market Road Feeder",
            "lat": 22.3160,
            "lon": 73.1690,
            "customers_served": 2400,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2000,
        },

        # --- Fed by TX-002 (Riverside South, water treatment) ---
        {
            "id": "FDR-003",
            "type": "feeder",
            "name": "Water Plant Feeder",
            "lat": 22.2990,
            "lon": 73.1800,
            "customers_served": 1200,
            "criticality_flags": ["water_treatment"],
            "has_backup_path": False,
            "install_year": 2003,
        },
        {
            "id": "FDR-004",
            "type": "feeder",
            "name": "South Colony Feeder",
            "lat": 22.2980,
            "lon": 73.1870,
            "customers_served": 3600,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2004,
        },

        # --- Fed by TX-003 (Riverside East) ---
        {
            "id": "FDR-005",
            "type": "feeder",
            "name": "Garden Area Feeder",
            "lat": 22.3120,
            "lon": 73.2000,
            "customers_served": 1900,
            "criticality_flags": [],
            "has_backup_path": True,  # backup from TX-004 cross-tie
            "install_year": 2002,
        },
        {
            "id": "FDR-006",
            "type": "feeder",
            "name": "Temple Road Feeder",
            "lat": 22.3080,
            "lon": 73.1980,
            "customers_served": 1600,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2005,
        },

        # --- Fed by TX-005 (Industrial East, data center) ---
        {
            "id": "FDR-007",
            "type": "feeder",
            "name": "Data Center Feeder",
            "lat": 22.3360,
            "lon": 73.2380,
            "customers_served": 800,
            "criticality_flags": ["data_center"],
            "has_backup_path": False,
            "install_year": 2011,
        },
        {
            "id": "FDR-008",
            "type": "feeder",
            "name": "Factory Lane Feeder",
            "lat": 22.3400,
            "lon": 73.2400,
            "customers_served": 2400,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2011,
        },

        # --- Fed by TX-006 (Industrial Central) ---
        {
            "id": "FDR-009",
            "type": "feeder",
            "name": "Warehouse District Feeder",
            "lat": 22.3440,
            "lon": 73.2250,
            "customers_served": 1100,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2013,
        },
        {
            "id": "FDR-010",
            "type": "feeder",
            "name": "Transport Hub Feeder",
            "lat": 22.3400,
            "lon": 73.2170,
            "customers_served": 1100,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2013,
        },

        # --- Fed by TX-007 (University Main) ---
        {
            "id": "FDR-011",
            "type": "feeder",
            "name": "Campus Feeder",
            "lat": 22.2930,
            "lon": 73.2420,
            "customers_served": 1500,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2015,
        },

        # --- Fed by TX-008 (University Annex) ---
        {
            "id": "FDR-012",
            "type": "feeder",
            "name": "Research Park Feeder",
            "lat": 22.2830,
            "lon": 73.2580,
            "customers_served": 1000,
            "criticality_flags": [],
            "has_backup_path": False,
            "install_year": 2017,
        },

        # --- Fed by TX-009 (Residential Colony) ---
        {
            "id": "FDR-013",
            "type": "feeder",
            "name": "School Zone Feeder",
            "lat": 22.2960,
            "lon": 73.2630,
            "customers_served": 1800,
            "criticality_flags": ["school"],
            "has_backup_path": False,
            "install_year": 2009,
        },
    ]

    edges = [
        # =====================================================================
        # SUBSTATION → TRANSFORMER links (primary radial structure)
        # =====================================================================

        # SUB-001 feeds 3 transformers
        {"from": "SUB-001", "to": "TX-001", "type": "primary", "capacity_kw": 15000},
        {"from": "SUB-001", "to": "TX-002", "type": "primary", "capacity_kw": 15000},
        {"from": "SUB-001", "to": "TX-003", "type": "primary", "capacity_kw": 12000},

        # SUB-002 feeds 3 transformers
        {"from": "SUB-002", "to": "TX-004", "type": "primary", "capacity_kw": 10000},
        {"from": "SUB-002", "to": "TX-005", "type": "primary", "capacity_kw": 12000},
        {"from": "SUB-002", "to": "TX-006", "type": "primary", "capacity_kw": 8000},

        # SUB-003 feeds 3 transformers
        {"from": "SUB-003", "to": "TX-007", "type": "primary", "capacity_kw": 8000},
        {"from": "SUB-003", "to": "TX-008", "type": "primary", "capacity_kw": 6000},
        {"from": "SUB-003", "to": "TX-009", "type": "primary", "capacity_kw": 6000},

        # =====================================================================
        # TRANSFORMER → FEEDER links
        # =====================================================================

        # TX-001 → 2 feeders
        {"from": "TX-001", "to": "FDR-001", "type": "feeder", "capacity_kw": 5000},
        {"from": "TX-001", "to": "FDR-002", "type": "feeder", "capacity_kw": 5000},

        # TX-002 → 2 feeders
        {"from": "TX-002", "to": "FDR-003", "type": "feeder", "capacity_kw": 4000},
        {"from": "TX-002", "to": "FDR-004", "type": "feeder", "capacity_kw": 6000},

        # TX-003 → 2 feeders
        {"from": "TX-003", "to": "FDR-005", "type": "feeder", "capacity_kw": 5000},
        {"from": "TX-003", "to": "FDR-006", "type": "feeder", "capacity_kw": 4000},

        # TX-005 → 2 feeders
        {"from": "TX-005", "to": "FDR-007", "type": "feeder", "capacity_kw": 5000},
        {"from": "TX-005", "to": "FDR-008", "type": "feeder", "capacity_kw": 5000},

        # TX-006 → 2 feeders
        {"from": "TX-006", "to": "FDR-009", "type": "feeder", "capacity_kw": 4000},
        {"from": "TX-006", "to": "FDR-010", "type": "feeder", "capacity_kw": 4000},

        # TX-007 → 1 feeder
        {"from": "TX-007", "to": "FDR-011", "type": "feeder", "capacity_kw": 4000},

        # TX-008 → 1 feeder
        {"from": "TX-008", "to": "FDR-012", "type": "feeder", "capacity_kw": 3000},

        # TX-009 → 1 feeder
        {"from": "TX-009", "to": "FDR-013", "type": "feeder", "capacity_kw": 4000},

        # =====================================================================
        # BACKUP / TIE links (these create the backup paths)
        # =====================================================================

        # Cross-tie between Riverside East (TX-003) and Industrial West (TX-004)
        # This is why TX-003, TX-004, and FDR-005 have has_backup_path = True
        {"from": "TX-003", "to": "TX-004", "type": "tie", "capacity_kw": 3000},

        # Backup tie from SUB-002 to SUB-001 (inter-substation)
        # This is why SUB-002 has has_backup_path = True
        {"from": "SUB-001", "to": "SUB-002", "type": "tie", "capacity_kw": 5000},
    ]

    return {"nodes": nodes, "edges": edges}


def validate_topology(topology: dict) -> None:
    """Run basic validation checks on the generated topology."""

    nodes = topology["nodes"]
    edges = topology["edges"]
    node_ids = {n["id"] for n in nodes}

    # Check all edge references exist
    for edge in edges:
        if edge["from"] not in node_ids:
            raise ValueError(f"Edge references unknown 'from' node: {edge['from']}")
        if edge["to"] not in node_ids:
            raise ValueError(f"Edge references unknown 'to' node: {edge['to']}")

    # Check minimum counts
    type_counts = {}
    for n in nodes:
        type_counts[n["type"]] = type_counts.get(n["type"], 0) + 1

    assert type_counts.get("substation", 0) >= 2, "Need at least 2 substations"
    assert type_counts.get("transformer", 0) >= 3, "Need at least 3 transformers"
    assert type_counts.get("feeder", 0) >= 5, "Need at least 5 feeders"

    # Check criticality and backup path distribution
    critical_nodes = [n for n in nodes if len(n["criticality_flags"]) > 0]
    backup_nodes = [n for n in nodes if n["has_backup_path"]]
    no_backup_nodes = [n for n in nodes if not n["has_backup_path"]]

    assert len(critical_nodes) >= 3, f"Need ≥3 critical nodes, got {len(critical_nodes)}"
    assert len(backup_nodes) >= 2, f"Need ≥2 backup-path nodes, got {len(backup_nodes)}"
    assert len(no_backup_nodes) > len(backup_nodes), (
        "Most nodes should NOT have backup paths (makes blast-radius interesting)"
    )

    # Check connectivity: every node should be reachable from at least one edge
    connected_nodes = set()
    for edge in edges:
        connected_nodes.add(edge["from"])
        connected_nodes.add(edge["to"])

    disconnected = node_ids - connected_nodes
    if disconnected:
        raise ValueError(f"Disconnected nodes found: {disconnected}")

    # Check node count
    assert 20 <= len(nodes) <= 30, f"Expected 20-30 nodes, got {len(nodes)}"

    print(f"[OK] Validation passed:")
    print(f"  Nodes: {len(nodes)} ({type_counts})")
    print(f"  Edges: {len(edges)}")
    print(f"  Critical nodes: {len(critical_nodes)}")
    print(f"  Nodes with backup: {len(backup_nodes)}")
    print(f"  Nodes without backup: {len(no_backup_nodes)}")


def main():
    """Generate and save the grid topology."""

    topology = generate_grid_topology()
    validate_topology(topology)

    # Write to generated/ directory
    output_dir = Path(__file__).parent / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "grid_topology.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(topology, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Grid topology written to: {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
