from dataclasses import dataclass
import numpy as np

@dataclass
class SimulationResult:
    times_h: np.ndarray
    region_ids: list
    levels_mm: np.ndarray
    capacity_mm: np.ndarray
    population: np.ndarray

def get_mock_simulation() -> SimulationResult:
    times = np.linspace(0, 5, 11)
    regions = ["R1", "R2", "R3", "R4", "R5"]
    capacities = np.array([100, 100, 100, 100, 100])
    pop = np.array([1200, 3400, 5600, 2100, 8900])
    
    levels = np.zeros((len(times), len(regions)))
    for t_idx, t in enumerate(times):
        levels[t_idx] = [20 + t*5, 40 + t*8, 50 + t*10, 10 + t*3, 30 + t*6]
        
    return SimulationResult(times, regions, levels, capacities, pop)