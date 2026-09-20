import numpy as np
from typing import Dict, List
from src.models import Region, Scenario
from src.classification import classify_status

class SimulationEngine:
    def __init__(self, regions: List[Region], scenario: Scenario, flow_k: float = 0.15, roughness_n: float = 0.025, custom_rain_map: Dict[str, float] = None):
        self.regions = {r.id: r for r in regions}
        self.scenario = scenario
        self.flow_k = flow_k
        self.roughness_n = roughness_n
        self.grid_spacing_m = 1000.0
        self.custom_rain_map = custom_rain_map or {}
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
        
        drainage_base = np.array([self.regions[rid].drainage_capacity for rid in region_ids])
        
        rain_rates_per_region = np.array([
            self.custom_rain_map.get(self.regions[rid].name, self.scenario.rainfall_intensity)
            if rid in self.scenario.rainfall_start regions else 0.0
            for rid in region_ids
        ])
        
        water_levels = np.zeros((total_steps, N))
        water_levels[0] = np.array([self.regions[rid].initial_water_level for rid in region_ids])
        rates_h = np.zeros((total_steps, N))
        
        blocked_set = set(self.scenario.blocked_channels) | set((b, a) for a, b in self.scenario.blocked_channels)

        for t_idx in range(total_steps - 1):
            curr_water = water_levels[t_idx].copy()
            
            max_w = max(1.0, np.max(curr_water) / 1000.0)
            cfl_dt_max_h = (self.grid_spacing_m / np.sqrt(9.81 * max_w)) / 3600.0
            n_substeps = max(1, int(np.ceil(dt_hours / max(1e-4, cfl_dt_max_h))))
            sub_dt = dt_hours / n_substeps
            
            temp_water = curr_water.copy()
            
            for _ in range(n_substeps):
                rain_in = rain_rates_per_region * sub_dt
                
                # Active evacuation rate scaling
                drained = np.minimum(temp_water + rain_in, (drainage_base * 4.0) * sub_dt)
                
                net_flow = np.zeros(N)
                heads = temp_water + elevations
                
                for i, rid in enumerate(region_ids):
                    for neighbor_id in self.regions[rid].neighbors:
                        j = id_to_idx[neighbor_id]
                        if i < j and (rid, neighbor_id) not in blocked_set:
                            head_diff = heads[i] - heads[j]
                            if head_diff != 0:
                                slope = abs(head_diff) / self.grid_spacing_m
                                flow_velocity = (1.0 / self.roughness_n) * ((max_w)**(2/3)) * np.sqrt(slope)
                                flow = self.flow_k * flow_velocity * np.sign(head_diff) * sub_dt * 1000.0
                                
                                if flow > 0:
                                    flow = min(flow, temp_water[i])
                                else:
                                    flow = max(flow, -temp_water[j])
                                net_flow[i] -= flow
                                net_flow[j] += flow
                                
                temp_water = np.maximum(0.0, temp_water + rain_in - drained + net_flow)
                
            water_levels[t_idx + 1] = temp_water
            rates_h[t_idx] = (temp_water - curr_water) / dt_hours

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

def optimize_drainage_allocation(regions: list, scenario: Scenario, budget_mm_h: float = 50.0) -> dict:
    base_engine = SimulationEngine(regions, scenario)
    base_res = base_engine.run()
    
    last_step = -1
    base_pop = sum(base_res["populations"][i] for i, s in enumerate(base_res["statuses"][last_step]) if s in ["Warning", "Critical"])
    
    allocations = {r.id: 0.0 for r in regions}
    remaining_budget = budget_mm_h
    step_size = 10.0
    
    while remaining_budget >= step_size:
        best_region_id = None
        max_pop_reduction = -1
        
        for r in regions:
            test_regions = [
                Region(
                    id=item.id, name=item.name, sector=item.sector, grid_pos=item.grid_pos,
                    elevation=item.elevation,
                    drainage_capacity=item.drainage_capacity + allocations[item.id] + (step_size if item.id == r.id else 0.0),
                    initial_water_level=item.initial_water_level, max_capacity=item.max_capacity,
                    population=item.population, terrain_type=item.terrain_type
                ) for item in regions
            ]
            test_engine = SimulationEngine(test_regions, scenario)
            test_res = test_engine.run()
            test_pop = sum(test_res["populations"][i] for i, s in enumerate(test_res["statuses"][last_step]) if s in ["Warning", "Critical"])
            
            pop_reduction = base_pop - test_pop
            if pop_reduction > max_pop_reduction:
                max_pop_reduction = pop_reduction
                best_region_id = r.id
                
        if best_region_id is None or max_pop_reduction <= 0:
            crit_ids = [rid for i, rid in enumerate(base_res["region_ids"]) if base_res["statuses"][last_step][i] == "Critical"]
            if crit_ids:
                for cid in crit_ids:
                    allocations[cid] += remaining_budget / len(crit_ids)
            break
            
        allocations[best_region_id] += step_size
        remaining_budget -= step_size
        
    return {
        "allocations": allocations,
        "baseline_affected": base_pop,
        "total_budget_allocated": budget_mm_h
    }