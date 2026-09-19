from dataclasses import dataclass, field
from typing import List, Tuple, Union

WARNING_THRESHOLD = 0.60
CRITICAL_THRESHOLD = 0.90

@dataclass
class Region:
    id: str
    name: str
    sector: str
    grid_pos: Tuple[int, int]
    elevation: float
    drainage_capacity: float
    initial_water_level: float
    max_capacity: float
    population: int
    terrain_type: int = 1
    neighbors: List[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.grid_pos, list):
            self.grid_pos = tuple(self.grid_pos)

@dataclass
class Scenario:
    rainfall_intensity: Union[float, List[Tuple[float, float]]]
    duration_hours: float
    rainfall_start_regions: List[str]
    time_step_minutes: float = 10.0
    drainage_failure_regions: List[str] = field(default_factory=list)
    blocked_channels: List[Tuple[str, str]] = field(default_factory=list)

    def get_rainfall_at_time(self, t_hours: float) -> float:
        if isinstance(self.rainfall_intensity, (int, float)):
            return float(self.rainfall_intensity)
        sorted_series = sorted(self.rainfall_intensity, key=lambda x: x[0])
        current_val = sorted_series[0][1]
        for t_point, val in sorted_series:
            if t_hours >= t_point:
                current_val = val
            else:
                break
        return current_val