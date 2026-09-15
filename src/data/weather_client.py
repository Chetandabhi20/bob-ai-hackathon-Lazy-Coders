"""
Real Weather Client for Grid Guardian
======================================

Fetches live weather forecasts from the Open-Meteo API (free, no API key).
This is the credibility anchor of the pipeline — real data, not simulated.

Returns data matching the schema in PROJECT_GUIDE.md Section 5.4.

Storm risk derivation:
  - "high"     : wind >= 50 kph OR precip >= 20 mm
  - "moderate" : wind >= 30 kph OR precip >= 10 mm
  - "low"      : everything else
"""

import os

import httpx


# Default base URL; can be overridden via WEATHER_API_BASE env var
DEFAULT_API_BASE = "https://api.open-meteo.com/v1"

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 15.0


class WeatherClientError(Exception):
    """Raised when the weather API call fails for any reason."""
    pass


def _classify_storm_risk(wind_speed_kph: float, precip_mm: float) -> str:
    """Derive a qualitative storm risk label from wind speed and precipitation."""
    if wind_speed_kph >= 50 or precip_mm >= 20:
        return "high"
    if wind_speed_kph >= 30 or precip_mm >= 10:
        return "moderate"
    return "low"


def get_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """
    Fetch a real weather forecast from Open-Meteo.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        days: Number of forecast days (1-16). Default 7.

    Returns:
        dict matching PROJECT_GUIDE Section 5.4 schema:
        {
          "location": {"lat": ..., "lon": ...},
          "forecast": [
            {
              "date": "YYYY-MM-DD",
              "temp_max_c": float,
              "wind_speed_kph": float,
              "precip_mm": float,
              "storm_risk": "low" | "moderate" | "high"
            },
            ...
          ]
        }

    Raises:
        WeatherClientError: On network failure, API error, or unexpected
            response format. Never silently returns fake/default data.
    """
    api_base = os.environ.get("WEATHER_API_BASE", DEFAULT_API_BASE)
    url = f"{api_base}/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,wind_speed_10m_max,precipitation_sum",
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }

    try:
        response = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except httpx.ConnectError as e:
        raise WeatherClientError(
            f"Network error: could not connect to weather API at {url}. "
            f"Check your internet connection. Details: {e}"
        ) from e
    except httpx.TimeoutException as e:
        raise WeatherClientError(
            f"Timeout: weather API at {url} did not respond within "
            f"{REQUEST_TIMEOUT}s. Details: {e}"
        ) from e
    except httpx.HTTPError as e:
        raise WeatherClientError(
            f"HTTP error calling weather API: {e}"
        ) from e

    if response.status_code != 200:
        raise WeatherClientError(
            f"Weather API returned status {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        data = response.json()
    except Exception as e:
        raise WeatherClientError(
            f"Weather API returned non-JSON response: {response.text[:200]}"
        ) from e

    # Validate expected fields exist
    if "daily" not in data:
        raise WeatherClientError(
            f"Weather API response missing 'daily' field. Got keys: {list(data.keys())}"
        )

    daily = data["daily"]
    required_keys = ["time", "temperature_2m_max", "wind_speed_10m_max", "precipitation_sum"]
    missing = [k for k in required_keys if k not in daily]
    if missing:
        raise WeatherClientError(
            f"Weather API daily data missing fields: {missing}. "
            f"Got: {list(daily.keys())}"
        )

    # Transform to our schema
    forecast_days = []
    for i, date_str in enumerate(daily["time"]):
        temp_max = daily["temperature_2m_max"][i]
        wind_speed = daily["wind_speed_10m_max"][i]
        precip = daily["precipitation_sum"][i]

        # Handle None values from API (can happen for far-out forecasts)
        if temp_max is None or wind_speed is None or precip is None:
            continue

        forecast_days.append({
            "date": date_str,
            "temp_max_c": round(temp_max, 1),
            "wind_speed_kph": round(wind_speed, 1),
            "precip_mm": round(precip, 1),
            "storm_risk": _classify_storm_risk(wind_speed, precip),
        })

    if not forecast_days:
        raise WeatherClientError(
            "Weather API returned daily data but all values were None."
        )

    return {
        "location": {"lat": lat, "lon": lon},
        "forecast": forecast_days,
    }


# ---------------------------------------------------------------------------
# CLI entry point for quick testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    # Test with Riverside Substation coordinates from grid_topology.json
    test_lat, test_lon = 22.31, 73.18
    print(f"Fetching forecast for ({test_lat}, {test_lon})...")

    try:
        result = get_forecast(test_lat, test_lon, days=7)
        print(json.dumps(result, indent=2))
        print(f"\n[OK] Received {len(result['forecast'])} days of real forecast data")
    except WeatherClientError as e:
        print(f"[ERROR] {e}")

    # Test error handling with a broken URL
    print("\n--- Testing error handling with broken URL ---")
    os.environ["WEATHER_API_BASE"] = "http://localhost:1"
    try:
        get_forecast(test_lat, test_lon)
        print("[FAIL] Should have raised WeatherClientError")
    except WeatherClientError as e:
        print(f"[OK] Correctly raised error: {type(e).__name__}: {str(e)[:100]}...")
    finally:
        del os.environ["WEATHER_API_BASE"]
