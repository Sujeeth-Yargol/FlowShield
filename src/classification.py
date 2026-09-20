from typing import Optional

def classify_status(water_level: float, max_capacity: float) -> str:
    """
    Classifies flood status into strictly 3 categories:
    - Safe: < 1500 mm
    - Warning: 1500 mm - 3500 mm
    - Critical: >= 3500 mm
    """
    if water_level < 1500.0:
        return "Safe"
    elif water_level < 3500.0:
        return "Warning"
    else:
        return "Critical"

def calculate_time_to_critical(water_level: float, max_capacity: float, accumulation_rate_h: float) -> Optional[float]:
    critical_threshold = 3500.0
    if water_level >= critical_threshold:
        return 0.0
    if accumulation_rate_h <= 0:
        return None
    
    return (critical_threshold - water_level) / accumulation_rate_h