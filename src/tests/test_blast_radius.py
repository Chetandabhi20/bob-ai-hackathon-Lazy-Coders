import pytest
from risk_engine.blast_radius import (
    build_power_flow_graph,
    find_downstream_nodes,
    compute_blast_radius,
    compute_all_blast_radii
)

@pytest.fixture
def mock_topology():
    return {
        "nodes": [
            {"id": "A", "type": "substation", "customers_served": 1000, "has_backup_path": False, "criticality_flags": ["hospital"]},
            {"id": "B", "type": "transformer", "customers_served": 500, "has_backup_path": True, "criticality_flags": ["school"]},
            {"id": "C", "type": "feeder", "customers_served": 200, "has_backup_path": False, "criticality_flags": []},
            {"id": "D", "type": "feeder", "customers_served": 300, "has_backup_path": True, "criticality_flags": ["water_treatment"]}
        ],
        "edges": [
            {"from": "A", "to": "B", "type": "primary"},
            {"from": "B", "to": "C", "type": "feeder"},
            {"from": "B", "to": "D", "type": "feeder"},
            {"from": "C", "to": "D", "type": "tie"} # Should be ignored in power flow
        ]
    }

def test_build_power_flow_graph(mock_topology):
    graph = build_power_flow_graph(mock_topology)
    assert "B" in graph["A"]
    assert "C" in graph["B"]
    assert "D" in graph["B"]
    assert "D" not in graph.get("C", []) # Tie edge ignored

def test_find_downstream_nodes(mock_topology):
    graph = build_power_flow_graph(mock_topology)
    downstream_A = find_downstream_nodes("A", graph)
    assert set(downstream_A) == {"B", "C", "D"}
    
    downstream_B = find_downstream_nodes("B", graph)
    assert set(downstream_B) == {"C", "D"}
    
    downstream_C = find_downstream_nodes("C", graph)
    assert len(downstream_C) == 0

def test_compute_blast_radius(mock_topology):
    # Test node A (no backup, affects everyone)
    result_A = compute_blast_radius("A", mock_topology)
    assert result_A["node_id"] == "A"
    assert result_A["total_customers_at_risk"] == 2000 # 1000 + 500 + 200 + 300
    assert result_A["unprotected_customers"] == 1200 # A (1000) + C (200)
    assert set(result_A["critical_loads_at_risk"]) == {"hospital", "school", "water_treatment"}
    assert result_A["has_backup_path"] is False
    
    # Test node B (has backup, affects B, C, D)
    result_B = compute_blast_radius("B", mock_topology)
    assert result_B["total_customers_at_risk"] == 1000 # 500 + 200 + 300
    assert result_B["unprotected_customers"] == 200 # C (200)
    assert set(result_B["critical_loads_at_risk"]) == {"school", "water_treatment"}
    assert result_B["has_backup_path"] is True
    
    # B's score should be discounted because it has a backup path
    assert result_B["blast_radius_score"] < 50.0

def test_compute_all_blast_radii(mock_topology):
    results = compute_all_blast_radii(mock_topology)
    assert len(results) == 4
    # Highest impact should be first
    assert results[0]["node_id"] == "A"
    # Ensure scores are between 0 and 100
    for r in results:
        assert 0 <= r["blast_radius_score"] <= 100.0
