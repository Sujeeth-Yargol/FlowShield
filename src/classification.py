def classify_status(water_level: float, max_capacity: float) -> str:
    if water_level < 2000.0:
        return "Safe"
    elif water_level < 3800.0:
        return "Warning"
    else:
        return "Critical"

def calculate_time_to_thresholds(current_level: float, max_capacity: float, rate_per_hour: float) -> dict:
    warning_threshold = 2000.0
    critical_threshold = 3800.0
    
    eta_warning = None
    eta_critical = None
    
    if rate_per_hour > 0:
        if current_level < warning_threshold:
            eta_warning = (warning_threshold - current_level) / rate_per_hour
        else:
            eta_warning = 0.0
            
        if current_level < critical_threshold:
            eta_critical = (critical_threshold - current_level) / rate_per_hour
        else:
            eta_critical = 0.0
            
    return {
        "eta_warning": eta_warning,
        "eta_critical": eta_critical
    }