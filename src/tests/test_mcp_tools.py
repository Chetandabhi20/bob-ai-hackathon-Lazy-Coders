"""
Tests for MCP Tools
====================

Covers happy paths and error cases for the four MCP tools exposed by the server.
"""

import pytest

from mcp_server.tools.get_asset_health import get_asset_health
from mcp_server.tools.get_weather_risk import get_weather_risk
from mcp_server.tools.rank_at_risk_assets import rank_at_risk_assets
from mcp_server.tools.generate_crew_plan import generate_crew_plan
from data.weather_client import WeatherClientError


def test_get_asset_health_happy_path():
    """Test get_asset_health with valid asset IDs."""
    # Test a failing asset
    result = get_asset_health("TX-001")
    assert result["asset_id"] == "TX-001"
    assert result["asset_type"] == "transformer"
    assert "asset_name" in result
    assert 0.0 <= result["failure_probability_14d"] <= 1.0
    assert result["blast_radius_score"] >= 0
    assert isinstance(result["customers_at_risk"], int)
    assert isinstance(result["critical_loads_at_risk"], list)
    assert isinstance(result["has_backup_path"], bool)
    assert result["combined_priority_score"] >= 0
    assert isinstance(result["top_contributing_signals"], list)
    assert result["latest_readings"] is not None
    assert "temperature_c" in result["latest_readings"]

    # Test a substation
    result2 = get_asset_health("SUB-001")
    assert result2["asset_id"] == "SUB-001"
    assert result2["asset_type"] == "substation"


def test_get_asset_health_invalid():
    """Test get_asset_health with an unknown asset ID."""
    with pytest.raises(ValueError, match="not found in grid topology"):
        get_asset_health("FAKE-999")


def test_get_weather_risk_happy_path():
    """Test get_weather_risk with valid coordinates."""
    # Test Vadodara coordinates
    result = get_weather_risk(22.31, 73.18, 3)
    assert "location" in result
    assert result["location"]["lat"] == 22.31
    assert result["location"]["lon"] == 73.18
    assert "forecast" in result
    assert len(result["forecast"]) >= 1
    assert "overall_risk" in result
    assert result["overall_risk"] in ("low", "moderate", "high")
    
    day = result["forecast"][0]
    assert all(k in day for k in ("date", "temp_max_c", "wind_speed_kph", "precip_mm", "storm_risk"))


def test_get_weather_risk_invalid():
    """Test get_weather_risk with invalid coordinates."""
    with pytest.raises(ValueError, match="Invalid latitude"):
        get_weather_risk(999.0, 73.18)
    
    with pytest.raises(ValueError, match="Invalid longitude"):
        get_weather_risk(22.31, 999.0)
        
    with pytest.raises(ValueError, match="Invalid days"):
        get_weather_risk(22.31, 73.18, 0)


def test_rank_at_risk_assets_happy_path():
    """Test rank_at_risk_assets with valid limits."""
    # Top 5
    result = rank_at_risk_assets(5)
    assert "ranked_assets" in result
    assert len(result["ranked_assets"]) == 5
    assert "total_assets" in result
    assert result["total_assets"] >= 5
    assert "as_of_date" in result
    
    # Verify ranking order
    scores = [a["combined_priority_score"] for a in result["ranked_assets"]]
    assert scores == sorted(scores, reverse=True), "Not sorted descending!"
    
    # Verify Section 5.5 schema fields
    for asset in result["ranked_assets"]:
        assert all(k in asset for k in (
            "asset_id", "failure_probability_14d", "blast_radius_score",
            "customers_at_risk", "critical_loads_at_risk", "has_backup_path",
            "combined_priority_score", "top_contributing_signals",
        ))


def test_rank_at_risk_assets_invalid():
    """Test rank_at_risk_assets with an invalid limit."""
    with pytest.raises(ValueError, match="Invalid top_n"):
        rank_at_risk_assets(0)


def test_generate_crew_plan_happy_path():
    """Test generate_crew_plan with default and custom locations."""
    # Default crew locations
    result = generate_crew_plan()
    assert "generated_at" in result
    assert "assignments" in result
    assert "unassigned_high_risk_assets" in result
    assert len(result["assignments"]) > 0
    
    # Verify schema
    for a in result["assignments"]:
        assert all(k in a for k in (
            "crew_id", "assigned_asset_id", "priority_rank",
            "eta_minutes", "reason",
        ))
        
    # No duplicate crews or assets
    crew_ids = [a["crew_id"] for a in result["assignments"]]
    assert len(crew_ids) == len(set(crew_ids)), "Duplicate crew!"
    asset_ids = [a["assigned_asset_id"] for a in result["assignments"]]
    assert len(asset_ids) == len(set(asset_ids)), "Duplicate asset!"
    
    # Custom crew locations
    custom_crews = [
        {"crew_id": "TEAM-1", "name": "Test Crew 1", "lat": 22.30, "lon": 73.19},
        {"crew_id": "TEAM-2", "name": "Test Crew 2", "lat": 22.35, "lon": 73.22},
    ]
    result2 = generate_crew_plan(custom_crews)
    assert len(result2["assignments"]) <= 2


def test_generate_crew_plan_invalid():
    """Test generate_crew_plan with an empty crew list."""
    with pytest.raises(ValueError, match="must contain at least one crew"):
        generate_crew_plan([])
    
    with pytest.raises(ValueError, match="missing required keys"):
        generate_crew_plan([{"crew_id": "TEAM-X"}]) # Missing lat/lon
