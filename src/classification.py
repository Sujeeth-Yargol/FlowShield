def classify_status(water_level: float, max_capacity: float) -> str:
    if water_level < 2000.0:
        return "Safe"
    elif water_level < 3800.0:
        return "Warning"
    else:
        return "Critical"

def calculate_time_to_thresholds(current_level: float, max_capacity: float, rate_per_hour: float, rainfall_rate: float = 0.0, drainage_capacity: float = 0.0) -> dict:
    warning_threshold = 2000.0
    critical_threshold = 3800.0
    
    # Use net rate if provided, fallback to explicit rainfall - drainage
    effective_rate = rate_per_hour if rate_per_hour > 0 else (rainfall_rate - drainage_capacity)
    
    eta_warning = None
    eta_critical = None
    
    if effective_rate > 0:
        if current_level < warning_threshold:
            eta_warning = (warning_threshold - current_level) / effective_rate
        else:
            eta_warning = 0.0
            
        if current_level < critical_threshold:
            eta_critical = (critical_threshold - current_level) / effective_rate
        else:
            eta_critical = 0.0
            
    return {
        "eta_warning": eta_warning,
        "eta_critical": eta_critical
    }