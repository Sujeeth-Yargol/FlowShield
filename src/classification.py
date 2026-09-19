from typing import Optional
from src.models import WARNING_THRESHOLD, CRITICAL_THRESHOLD

def classify_status(water_level: float, max_capacity: float) -> str:
    if max_capacity <= 0:
        return "Critical"
    ratio = water_level / max_capacity
    if ratio < WARNING_THRESHOLD:
        return "Safe"
    elif ratio < CRITICAL_THRESHOLD:
        return "Warning"
    else:
        return "Critical"

def calculate_time_to_critical(water_level: float, max_capacity: float, net_rate_per_hour: float) -> Optional[float]:
    critical_level = CRITICAL_THRESHOLD * max_capacity
    if water_level >= critical_level:
        return 0.0
    if net_rate_per_hour <= 0:
        return None
    return (critical_level - water_level) / net_rate_per_hour