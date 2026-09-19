import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import json
import pandas as pd
from src.models import Region, Scenario
from src.simulation import SimulationEngine
from src.scenarios import normal_rainfall_scenario, heavy_rainfall_scenario
from src.visualization import render_grid_heatmap, render_water_level_chart
from src.classification import calculate_time_to_critical

st.set_page_config(page_title="FLOWSHIELD — Bangalore Basin & Grid Engine", layout="wide")

# Custom UI Theme
st.markdown("""
<style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .header-card { background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .metric-box { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 15px; text-align: center; }
    .critical-box { background: #3C1E1E; border: 1px solid #F85149; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .warning-box { background: #382C1E; border: 1px solid #D29922; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .safe-box { background: #1E3A2B; border: 1px solid #2EA043; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# Load City Data
@st.cache_data
def load_default_city():
    with open("data/sample_city.json", "r") as f:
        return json.load(f)

city_data = load_default_city()
regions_list = [Region(**item) for item in city_data["regions"]]

# Sidebar Control Plane
st.sidebar.title("🎛️ Simulation Control Plane")
st.sidebar.radio("Select City Topography Source", ["Bangalore Basin (16 Zones)", "Custom Grid Builder", "Import Custom JSON/CSV"])

st.sidebar.markdown("---")
st.sidebar.subheader("🌧️ Climate & Scenario Parameters")
preset = st.sidebar.selectbox("Quick Scenario Preset (Bonus)", ["Normal rainfall", "Heavy rainfall", "Drainage failure"])

duration = st.sidebar.number_input("Duration (Hours)", value=6.0, step=1.0)
time_step = st.sidebar.number_input("Time Step (Mins)", value=10.0, step=5.0)

rain_type = st.sidebar.radio("Rainfall Type", ["Constant Rate", "Time-Varying Curve"])
rain_intensity = st.sidebar.slider("Rainfall Intensity (mm/hr)", 0.0, 150.0, 24.0)

st.sidebar.subheader("📍 Rainfall Inflow Epicenters")
rain_distrib = st.sidebar.radio("Rainfall Distribution", ["City-Wide (All Regions)", "Targeted Epicenters (Highland/Specific Zones)"])

region_names = [r.name for r in regions_list]
if rain_distrib == "City-Wide (All Regions)":
    start_r_ids = [r.id for r in regions_list]
else:
    selected_epicenters = st.sidebar.multiselect("Choose Epicenters", region_names, default=[region_names[2], region_names[11]])
    start_r_ids = [r.id for r in regions_list if r.name in selected_epicenters]

st.sidebar.subheader("🚧 Infrastructure Status")
drainage_failures = st.sidebar.multiselect("Drainage Failure Regions (Drainage = 0)", region_names)
failure_r_ids = [r.id for r in regions_list if r.name in drainage_failures]

flow_k = st.sidebar.slider("Inter-region Flow Coefficient (k)", 0.05, 0.50, 0.15)

# Build & Run Scenario
scenario = Scenario(
    rainfall_intensity=rain_intensity,
    duration_hours=duration,
    rainfall_start_regions=start_r_ids,
    time_step_minutes=time_step,
    drainage_failure_regions=failure_r_ids
)

engine = SimulationEngine(regions_list, scenario, flow_k=flow_k)
sim_result = engine.run()

# Main Header
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

# Top Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Real-Time Flood Intelligence", 
    "⚖️ Scenario Comparison Studio", 
    "🌊 Inter-Region Hydraulic Vectors", 
    "📜 Export & Documentation"
])

with tab1:
    st.subheader("⏱️ Time-Series Playback & Scrubber")
    
    time_steps = len(sim_result["times_h"])
    selected_step = st.slider("Scrub Simulation Time (Hours : Minutes)", 0, time_steps - 1, time_steps - 1)
    current_t = sim_result["times_h"][selected_step]
    
    st.caption(f"Viewing: ⚙️ **FINAL FLOOD STATE at t={current_t:.2f} hrs**")
    
    # Live KPI Cards Bar
    curr_statuses = sim_result["statuses"][selected_step]
    num_critical = curr_statuses.count("Critical")
    num_warning = curr_statuses.count("Warning")
    num_safe = curr_statuses.count("Safe")
    
    affected_pop = sum(
        sim_result["populations"][i] for i, s in enumerate(curr_statuses) if s in ["Warning", "Critical"]
    )
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 CRITICAL FLOOD ZONES", f"{num_critical}/16", "Ratio ≥ 90% capacity")
    k2.metric("⚠️ WARNING CATCHMENTS", f"{num_warning}", "Ratio 60% - 90%")
    k3.metric("🟢 SAFE RESILIENT ZONES", f"{num_safe}", "Water level < 60%")
    k4.metric("👥 AFFECTED POPULATION (BONUS)", f"{affected_pop:,}", "Citizens in Warning or Critical")
    
    st.markdown("---")
    
    # Regional Breakdown Summaries
    crit_names = [sim_result["regions"][rid].name for i, rid in enumerate(sim_result["region_ids"]) if curr_statuses[i] == "Critical"]
    warn_names = [sim_result["regions"][rid].name for i, rid in enumerate(sim_result["region_ids"]) if curr_statuses[i] == "Warning"]
    safe_names = [sim_result["regions"][rid].name for i, rid in enumerate(sim_result["region_ids"]) if curr_statuses[i] == "Safe"]
    
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(f"<div class='critical-box'><b style='color:#F85149;'>CRITICAL FLOOD ZONES ({len(crit_names)})</b><br><small>{', '.join(crit_names) if crit_names else 'None'}</small></div>", unsafe_allow_html=True)
    with b2:
        st.markdown(f"<div class='warning-box'><b style='color:#D29922;'>WARNING CATCHMENTS ({len(warn_names)})</b><br><small>{', '.join(warn_names) if warn_names else 'None'}</small></div>", unsafe_allow_html=True)
    with b3:
        st.markdown(f"<div class='safe-box'><b style='color:#2EA043;'>SAFE RESILIENT ZONES ({len(safe_names)})</b><br><small>{', '.join(safe_names) if safe_names else 'None'}</small></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    st.subheader("🗺️ Multi-Layer Grid Visualization")
    layer_mode = st.radio(
        "Select Active Grid Layer:", 
        ["🚨 Flood Early Warning Status (Safe/Warning/Critical)", "💧 Water Accumulation Level (mm)", "⛰️ Terrain Elevation Topography (m)", "🚰 Storm Drainage Capacity (mm/hr)"], 
        horizontal=True
    )
    
    fig_map = render_grid_heatmap(sim_result, selected_step, layer_mode)
    st.plotly_chart(fig_map, use_container_width=True)
    
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
    
    st.markdown("---")
    
    st.subheader("📈 Water Level Evolution Over Simulation Time")
    st.plotly_chart(render_water_level_chart(sim_result), use_container_width=True)