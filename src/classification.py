from typing import Optional

def classify_status(water_level: float, max_capacity: float) -> str:
    """
    Balanced classification thresholds relative to max basin capacity:
    - Safe: < 60% capacity (< 2700 mm)
    - Warning: 60% - 89.9% capacity (2700 mm - 4050 mm)
    - Critical: >= 90% capacity (>= 4050 mm)
    """
    if max_capacity <= 0:
        return "Critical"
    
    ratio = water_level / max_capacity
    
    if ratio < 0.60:
        return "Safe"
    elif ratio < 0.90:
        return "Warning"
    else:
        return "Critical"

def calculate_time_to_critical(water_level: float, max_capacity: float, accumulation_rate_h: float) -> Optional[float]:
    critical_threshold = 0.90 * max_capacity
    if water_level >= critical_threshold:
        return 0.0
    if accumulation_rate_h <= 0:
        return None
    
    return (critical_threshold - water_level) / accumulation_rate_h