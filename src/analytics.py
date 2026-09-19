from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from src.classification import classify_level, RiskStatus

@dataclass
class RiskSummary:
    current_safe: int
    current_warning: int
    current_critical: int
    peak_water_level_mm: float
    affected_population: int
    earliest_critical_region: Optional[str]
    earliest_critical_time_h: Optional[float]
    critical_regions: List[str]
    warning_regions: List[str]

def calculate_eta(current_level: float, capacity: float, rate_per_hour: float) -> Optional[float]:
    critical_level = 0.90 * capacity
    if current_level >= critical_level:
        return 0.0
    if rate_per_hour <= 0:
        return None
    return (critical_level - current_level) / rate_per_hour

def generate_region_table(
    times_h: np.ndarray,
    region_ids: List[str],
    levels_mm: np.ndarray,
    capacity_mm: np.ndarray,
    population: np.ndarray,
    time_index: int
) -> pd.DataFrame:
    rows = []
    num_regions = len(region_ids)
    
    for idx in range(num_regions):
        r_id = region_ids[idx]
        cap = capacity_mm[idx]
        pop = population[idx]
        current_lvl = levels_mm[time_index, idx]
        
        status = classify_level(current_lvl, cap)
        ratio = current_lvl / cap if cap > 0 else 1.0
        
        if time_index > 0:
            dt = times_h[time_index] - times_h[time_index - 1]
            rate = (levels_mm[time_index, idx] - levels_mm[time_index - 1, idx]) / dt if dt > 0 else 0.0
        else:
            rate = 0.0
            
        eta = calculate_eta(current_lvl, cap, rate)
        eta_str = f"{eta:.1f}h" if eta is not None and eta > 0 else ("0.0h" if eta == 0.0 else "--")
        
        rows.append({
            "Region": r_id,
            "Status": status.name,
            "Water (mm)": round(current_lvl, 1),
            "Capacity (mm)": round(cap, 1),
            "Ratio": round(ratio, 2),
            "ETA": eta_str,
            "Population": int(pop)
        })
        
    return pd.DataFrame(rows)