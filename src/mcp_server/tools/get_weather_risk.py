"""
get_weather_risk — MCP Tool
=============================

Fetch a real-time weather forecast for a location and flag weather-related
risk to grid assets in that area.

Backend: data.weather_client.get_forecast()
"""

from data.weather_client import WeatherClientError, get_forecast


def get_weather_risk(lat: float, lon: float, days: int = 7) -> dict:
    """
    Fetch a real-time weather forecast and assess storm risk for grid assets.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        days: Number of forecast days (1-16). Default 7.

    Returns:
        Dict with location, forecast array (Section 5.4 schema), and an
        overall_risk summary (max storm_risk across all forecast days).

    Raises:
        WeatherClientError: On network failure or API error.
        ValueError: On invalid input parameters.
    """
    # Validate inputs
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180.")
    if not (1 <= days <= 16):
        raise ValueError(f"Invalid days: {days}. Must be between 1 and 16.")

    # Fetch real forecast from Open-Meteo
    result = get_forecast(lat, lon, days)

    # Compute overall_risk: highest storm_risk across all forecast days
    risk_levels = {"low": 0, "moderate": 1, "high": 2}
    risk_names = {0: "low", 1: "moderate", 2: "high"}

    max_risk = 0
    for day in result["forecast"]:
        level = risk_levels.get(day["storm_risk"], 0)
        if level > max_risk:
            max_risk = level

    result["overall_risk"] = risk_names[max_risk]

    return result
