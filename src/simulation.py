import numpy as np
from typing import Dict, List
from src.models import Region, Scenario
from src.classification import classify_status

class SimulationEngine:
    def __init__(self, regions: List[Region], scenario: Scenario, flow_k: float = 0.15):
        self.regions = {r.id: r for r in regions}
        self.scenario = scenario
        self.flow_k = flow_k
        self._build_grid_connectivity()
        
    def _build_grid_connectivity(self):
        pos_map = {tuple(r.grid_pos): r.id for r in self.regions.values()}
        for r in self.regions.values():
            r.neighbors = []
            row, col = tuple(r.grid_pos)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor_id = pos_map.get((row + dr, col + dc))
                if neighbor_id:
                    r.neighbors.append(neighbor_id)

    def run(self) -> Dict:
        dt_hours = self.scenario.time_step_minutes / 60.0
        total_steps = int(np.ceil(self.scenario.duration_hours / dt_hours)) + 1
        times_h = np.array([min(i * dt_hours, self.scenario.duration_hours) for i in range(total_steps)])
        
        region_ids = list(self.regions.keys())
        N = len(region_ids)
        id_to_idx = {rid: i for i, rid in enumerate(region_ids)}
        
        elevations = np.array([self.regions[rid].elevation for rid in region_ids])
        capacities = np.array([self.regions[rid].max_capacity for rid in region_ids])
        populations = np.array([self.regions[rid].population for rid in region_ids])
        drainage_base = np.array([
            0.0 if rid in self.scenario.drainage_failure_regions else self.regions[rid].drainage_capacity
            for rid in region_ids
        ])
        
        water_levels = np.zeros((total_steps, N))
        water_levels[0] = np.array([self.regions[rid].initial_water_level for rid in region_ids])
        rates_h = np.zeros((total_steps, N))
        
        blocked_set = set(self.scenario.blocked_channels) | set((b, a) for a, b in self.scenario.blocked_channels)

        for t_idx in range(total_steps - 1):
            current_t = times_h[t_idx]
            rain_rate = self.scenario.get_rainfall_at_time(current_t)
            curr_water = water_levels[t_idx].copy()
            
            rain_in = np.zeros(N)
            for rid in self.scenario.rainfall_start_regions:
                if rid in id_to_idx:
                    rain_in[id_to_idx[rid]] = rain_rate * dt_hours
                    
            drained = np.minimum(curr_water, drainage_base * dt_hours)
            net_flow = np.zeros(N)
            heads = curr_water + elevations
            
            for i, rid in enumerate(region_ids):
                for neighbor_id in self.regions[rid].neighbors:
                    j = id_to_idx[neighbor_id]
                    if i < j and (rid, neighbor_id) not in blocked_set:
                        head_diff = heads[i] - heads[j]
                        if head_diff != 0:
                            flow = self.flow_k * head_diff
                            if flow > 0:
                                flow = min(flow, curr_water[i])
                            else:
                                flow = max(flow, -curr_water[j])
                            net_flow[i] -= flow
                            net_flow[j] += flow
                            
            new_water = np.maximum(0.0, curr_water + rain_in - drained + net_flow)
            water_levels[t_idx + 1] = new_water
            rates_h[t_idx] = (new_water - curr_water) / dt_hours

        rates_h[-1] = rates_h[-2] if total_steps > 1 else np.zeros(N)

        status_matrix = []
        for t_idx in range(total_steps):
            step_status = [classify_status(water_levels[t_idx, i], capacities[i]) for i in range(N)]
            status_matrix.append(step_status)

        return {
            "times_h": times_h,
            "region_ids": region_ids,
            "regions": self.regions,
            "water_levels": water_levels,
            "capacities": capacities,
            "elevations": elevations,
            "populations": populations,
            "rates_h": rates_h,
            "statuses": status_matrix
        }