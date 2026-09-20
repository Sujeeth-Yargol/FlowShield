import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import json
import pandas as pd
from src.models import Region, Scenario
from src.simulation import SimulationEngine, optimize_drainage_allocation
from src.visualization import render_grid_heatmap, render_water_level_chart
from src.classification import calculate_time_to_critical

st.set_page_config(page_title="FLOWSHIELD — Bangalore Basin & Grid Engine", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .header-card { background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .critical-box { background: #3C1E1E; border: 1px solid #F85149; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .warning-box { background: #382C1E; border: 1px solid #D29922; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .safe-box { background: #1E3A2B; border: 1px solid #2EA043; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_default_city():
    with open("data/sample_city.json", "r") as f:
        return json.load(f)

city_data = load_default_city()

st.sidebar.title("🎛️ Simulation Control Plane")

st.sidebar.subheader("📐 Grid Topology Configuration")
grid_mode = st.sidebar.radio("Select Grid Size Preset", ["4x4 Bangalore Core (16 Zones)", "Custom Subset (e.g. 2x2, 2x3, 3x3)"])

all_regions = [Region(**item) for item in city_data["regions"]]

if "Custom Subset" in grid_mode:
    rows_cnt = st.sidebar.slider("Grid Rows (Y)", 1, 4, 2)
    cols_cnt = st.sidebar.slider("Grid Columns (X)", 1, 4, 3)
    regions_list = [r for r in all_regions if r.grid_pos[0] < rows_cnt and r.grid_pos[1] < cols_cnt]
else:
    regions_list = all_regions

st.sidebar.markdown("---")
st.sidebar.subheader("🌧️ Climate & Rainfall Setup")
duration = st.sidebar.number_input("Duration (Hours)", value=6.0, step=1.0)
time_step = st.sidebar.number_input("Time Step (Mins)", value=10.0, step=5.0)

region_names = [r.name for r in regions_list]

st.sidebar.subheader("🎯 Rainfall Intensity Per Region")
st.sidebar.info("Select regions below or click a cell on the grid map to set custom rainfall intensity.")

selected_epicenters = st.sidebar.multiselect(
    "Active Rainfall Regions:", 
    region_names, 
    default=region_names[:min(2, len(region_names))]
)

# Custom Rainfall Intensity Map per region
if "custom_rainfall_map" not in st.session_state:
    st.session_state["custom_rainfall_map"] = {r.name: 45.0 for r in regions_list}

global_rain = st.sidebar.slider("Default Rainfall Intensity for selected areas (mm/hr)", 0.0, 150.0, 45.0)

for name in selected_epicenters:
    st.session_state["custom_rainfall_map"][name] = st.sidebar.number_input(
        f"🌧️ Intensity for {name} (mm/hr)", 
        value=st.session_state["custom_rainfall_map"].get(name, global_rain),
        min_value=0.0, max_value=200.0, key=f"rain_{name}"
    )

start_r_ids = [r.id for r in regions_list if r.name in selected_epicenters]

st.sidebar.subheader("🚧 Infrastructure Status")
drainage_failures = st.sidebar.multiselect("Drainage Failure Regions (Drainage = 0)", region_names)
failure_r_ids = [r.id for r in regions_list if r.name in drainage_failures]

flow_k = st.sidebar.slider("Inter-region Flow Coefficient (k)", 0.05, 0.50, 0.15)

scenario = Scenario(
    rainfall_intensity=global_rain,
    duration_hours=duration,
    rainfall_start_regions=start_r_ids,
    time_step_minutes=time_step,
    drainage_failure_regions=failure_r_ids
)

engine = SimulationEngine(regions_list, scenario, flow_k=flow_k)
sim_result = engine.run()

# Dynamic Overwrite of custom regional rainfall
for idx, rid in enumerate(sim_result["region_ids"]):
    r = sim_result["regions"][rid]
    if r.name in selected_epicenters:
        custom_rate = st.session_state["custom_rainfall_map"].get(r.name, global_rain)
        dt_hours = scenario.time_step_minutes / 60.0
        # Re-apply custom rain rate vector
        for t_step in range(len(sim_result["times_h"]) - 1):
            sim_result["water_levels"][t_step + 1, idx] += (custom_rate - global_rain) * dt_hours * 0.1

st.markdown("""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #58A6FF;">🛡️ FLOWSHIELD</h2>
            <p style="margin: 0; color: #8B949E;">Predict the flood. Protect the future.</p>
        </div>
        <div>
            <span style="background: #21262D; padding: 6px 12px; border-radius: 6px; font-size: 12px; color: #8B949E; margin-right: 10px;">THEME: VECTOR</span>
            <span style="background: #21262D; padding: 6px 12px; border-radius: 6px; font-size: 12px; color: #58A6FF;">Bangalore Basin & Grid Engine</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Real-Time Flood Intelligence", 
    "🧮 Mathematical Optimization Studio", 
    "🌊 Inter-Region Hydraulic Vectors", 
    "📜 Export & Documentation"
])

with tab1:
    st.subheader("⏱️ Time-Series Playback & Scrubber")
    
    time_steps = len(sim_result["times_h"])
    selected_step = st.slider("Scrub Simulation Time (Hours : Minutes)", 0, time_steps - 1, time_steps - 1)
    current_t = sim_result["times_h"][selected_step]
    
    st.caption(f"Viewing: ⚙️ **FINAL FLOOD STATE at t={current_t:.2f} hrs**")
    
    curr_statuses = sim_result["statuses"][selected_step]
    num_critical = curr_statuses.count("Critical")
    num_warning = curr_statuses.count("Warning")
    num_safe = curr_statuses.count("Safe")
    
    affected_pop = sum(
        sim_result["populations"][i] for i, s in enumerate(curr_statuses) if s in ["Warning", "Critical"]
    )
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 CRITICAL FLOOD ZONES", f"{num_critical}/{len(regions_list)}", "Ratio ≥ 90% capacity")
    k2.metric("⚠️ WARNING CATCHMENTS", f"{num_warning}", "Ratio 60% - 90%")
    k3.metric("🟢 SAFE RESILIENT ZONES", f"{num_safe}", "Water level < 60%")
    k4.metric("👥 AFFECTED POPULATION", f"{affected_pop:,}", "Citizens in Warning or Critical")
    
    st.markdown("---")
    
    st.subheader("🗺️ Multi-Layer Interactive Grid Visualization")
    layer_mode = st.radio(
        "Select Active Grid Layer:", 
        ["🚨 Flood Early Warning Status (Safe/Warning/Critical)", "💧 Water Accumulation Level (mm)", "⛰️ Terrain Elevation Topography (m)", "🚰 Storm Drainage Capacity (mm/hr)"], 
        horizontal=True
    )
    
    fig_map = render_grid_heatmap(sim_result, selected_step, layer_mode)
    
    # Enable point selection without zooming
    event = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun", selection_mode="points")
    
    # Handle Mouse Click Selection on Grid
    if event and "selection" in event and event["selection"]["points"]:
        pt = event["selection"]["points"][0]
        clicked_r = pt.get("y")
        clicked_c = pt.get("x")
        
        clicked_region = next((r for r in regions_list if r.grid_pos == (clicked_r, clicked_c)), None)
        if clicked_region:
            st.info(f"📍 **Selected Region on Grid:** {clicked_region.name} (Sector: {clicked_region.sector})")
            
            new_val = st.number_input(
                f"Set Specific Rainfall Intensity for {clicked_region.name} (mm/hr):", 
                value=st.session_state["custom_rainfall_map"].get(clicked_region.name, global_rain),
                min_value=0.0, max_value=200.0, key=f"click_rain_{clicked_region.name}"
            )
            st.session_state["custom_rainfall_map"][clicked_region.name] = new_val
            if clicked_region.name not in selected_epicenters:
                st.write("💡 *Added region to active rainfall epicenters.*")

    st.markdown("---")
    
    st.subheader("🚨 Flood Risk & Time-to-Critical Early Warning Registry")
    
    rows = []
    for idx, rid in enumerate(sim_result["region_ids"]):
        r = sim_result["regions"][rid]
        lvl = sim_result["water_levels"][selected_step, idx]
        cap = sim_result["capacities"][idx]
        rate = sim_result["rates_h"][selected_step, idx]
        eta = calculate_time_to_critical(lvl, cap, rate)
        eta_str = f"{eta:.1f} hrs" if eta is not None and eta > 0 else ("0.0 (Critical)" if eta == 0.0 else "Not projected")
        
        rows.append({
            "Region ID": r.id,
            "Region Name": r.name,
            "Sector": r.sector,
            "Elevation (m)": r.elevation,
            "Drainage (mm/hr)": r.drainage_capacity,
            "Water Level (mm)": f"{lvl:.1f} / {cap:.0f}",
            "Capacity Fill": round(lvl / cap, 3),
            "Status": curr_statuses[idx],
            "ETA to Critical": eta_str
        })
        
    df_reg = pd.DataFrame(rows)
    st.dataframe(df_reg, use_container_width=True)

with tab2:
    st.subheader("🧮 Mathematical Optimization Engine")
    budget = st.slider("Total Available Drainage Upgrade Budget (mm/hr)", 10.0, 200.0, 50.0)
    
    if st.button("🚀 Run Gradient Descent Optimization Solver"):
        opt_res = optimize_drainage_allocation(regions_list, scenario, budget_mm_h=budget)
        st.success("Optimization Complete!")
        
        opt_rows = []
        for r in regions_list:
            alloc = opt_res["allocations"][r.id]
            if alloc > 0:
                opt_rows.append({
                    "Region Name": r.name,
                    "Current Drainage (mm/hr)": r.drainage_capacity,
                    "Recommended Upgrade (+mm/hr)": alloc,
                    "New Total Drainage (mm/hr)": r.drainage_capacity + alloc
                })
        
        if opt_rows:
            st.dataframe(pd.DataFrame(opt_rows), use_container_width=True)
        else:
            st.info("Current drainage infrastructure is sufficient for this scenario!")