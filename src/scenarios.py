from src.models import Scenario

def normal_rainfall_scenario(start_regions: list) -> Scenario:
    return Scenario(
        rainfall_intensity=30.0,
        duration_hours=4.0,
        rainfall_start_regions=start_regions,
        time_step_minutes=10.0
    )

def heavy_rainfall_scenario(start_regions: list) -> Scenario:
    return Scenario(
        rainfall_intensity=80.0,
        duration_hours=4.0,
        rainfall_start_regions=start_regions,
        time_step_minutes=10.0
    )