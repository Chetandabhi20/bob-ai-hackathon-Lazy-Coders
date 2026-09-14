"""
generate_crew_plan — MCP Tool
===============================

Generate an optimized crew pre-positioning plan that assigns maintenance
crews to the highest-priority at-risk assets.

Backend: risk_engine.crew_planner.generate_crew_plan()
"""

from risk_engine.crew_planner import generate_crew_plan as _generate_crew_plan


def generate_crew_plan(crew_locations: list[dict] | None = None) -> dict:
    """
    Generate a crew pre-positioning plan for at-risk grid assets.

    Args:
        crew_locations: Optional list of crew starting positions. Each entry
            must have keys: crew_id (str), name (str), lat (float), lon (float).
            If omitted, uses the 4 default depot locations.

    Returns:
        Dict matching Section 5.6 schema with generated_at timestamp,
        assignments list, and unassigned_high_risk_assets.

    Raises:
        ValueError: On invalid crew location data.
    """
    # Validate crew_locations if provided
    if crew_locations is not None:
        if not isinstance(crew_locations, list):
            raise ValueError(
                f"crew_locations must be a list, got {type(crew_locations).__name__}"
            )
        if len(crew_locations) == 0:
            raise ValueError(
                "crew_locations must contain at least one crew. "
                "Omit the parameter to use the 4 default depots."
            )

        required_keys = {"crew_id", "lat", "lon"}
        for i, crew in enumerate(crew_locations):
            if not isinstance(crew, dict):
                raise ValueError(
                    f"crew_locations[{i}] must be a dict, got {type(crew).__name__}"
                )
            missing = required_keys - set(crew.keys())
            if missing:
                raise ValueError(
                    f"crew_locations[{i}] missing required keys: {sorted(missing)}. "
                    f"Required: crew_id, lat, lon. Optional: name."
                )
            # Add default name if missing
            if "name" not in crew:
                crew["name"] = f"Crew {crew['crew_id']}"

    return _generate_crew_plan(crew_locations=crew_locations)
