import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import json
import pandas as pd
import numpy as np
from src.models import Region, Scenario
from src.simulation import SimulationEngine, optimize_drainage_allocation
from src.visualization import render_grid_heatmap, render_water_level_chart
from src.classification import calculate_time_to_critical, classify_status

st.set_page_config(page_title="FLOWSHIELD — Hydrodynamic Early Warning Dashboard", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .header-card { background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .critical-box { background: #3C1E1E; border: 1px solid #F85149; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .warning-box { background: #382C1E; border: 1px solid #D29922; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .safe-box { background: #1E3A2B; border: 1px solid #2EA043; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .legend-card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 15px; margin-top: 10px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

def load_default_city():
    with open("data/sample_city.json", "r") as f:
        data = json.load(f)
        for r in data["regions"]:
            if r["max_capacity"] < 3000.0:
                r["max_capacity"] = 4500.0
        return data

city_data = load_default_city()

st.sidebar.title("🎛️ FlowShield Control Plane")

base_regions = [Region(**item) for item in city_data["regions"]]
region_names = [r.name for r in base_regions]

# --- DEMO PRESETS DEFINITION ---
st.sidebar.subheader("🎬 Demo Quick-Presets")
preset_choice = st.sidebar.selectbox(
    "Load Scenario Preset:",
    [
        "Custom Manual Inputs",
        "🎯 Preset 1: Multi-Risk City (Green, Yellow & Red Mix)",
        "🌧️ Preset 2: Severe Monsoonal Crisis (High Critical Risk)",
        "🛡️ Preset 3: Infrastructure Resilient Basin (Mostly Safe)"
    ]
)

default_rain = 40.0
default_epicenters = region_names
default_rain_map = {}
default_drainage_zones = []
default_drainage_values = {}

if preset_choice == "🎯 Preset 1: Multi-Risk City (Green, Yellow & Red Mix)":
    default_rain = 40.0
    default_epicenters = region_names
    default_rain_map = {
        "Yeshwanthpur": 10.0, "Hebbal - Sahakar Nagar": 35.0, "Manyata Tech Park - Nagavara": 40.0, "Hennur - KR Puram Lake Reach": 45.0,
        "Rajajinagar": 15.0, "Majestic": 25.0, "Indiranagar - Domlur Valley": 50.0, "Marathahalli - ORR Tech Corridor": 55.0,
        "Vijayanagar": 15.0, "Jayanagar": 30.0, "Koramangala 4th Block - Valley": 60.0, "Bellandur Lake Wetland": 65.0,
        "Banashankari Hills": 15.0, "BTM Layout - Madiwala Catchment": 35.0, "Silk Board Chokepoint - HSR": 60.0, "Varthur Downstream Lake Basin": 65.0
    }
    default_drainage_zones = ["Yeshwanthpur", "Majestic"]
    default_drainage_values = {"Yeshwanthpur": 60.0, "Majestic": 50.0}

elif preset_choice == "🌧️ Preset 2: Severe Monsoonal Crisis (High Critical Risk)":
    default_rain = 80.0
    default_epicenters = region_names
    default_rain_map = {name: 80.0 for name in region_names}
    default_drainage_zones = []
    default_drainage_values = {}

elif preset_choice == "🛡️ Preset 3: Infrastructure Resilient Basin (Mostly Safe)":
    default_rain = 35.0
    default_epicenters = region_names
    default_rain_map = {name: 35.0 for name in region_names}
    default_drainage_zones = [
        "Hebbal - Sahakar Nagar", "Indiranagar - Domlur Valley", "Jayanagar", 
        "Koramangala 4th Block - Valley", "Bellandur Lake Wetland", "Silk Board Chokepoint - HSR"
    ]
    default_drainage_values = {
        "Hebbal - Sahakar Nagar": 100.0,
        "Indiranagar - Domlur Valley": 150.0,
        "Jayanagar": 100.0,
        "Koramangala 4th Block - Valley": 180.0,
        "Bellandur Lake Wetland": 200.0,
        "Silk Board Chokepoint - HSR": 150.0
    }

st.sidebar.markdown("---")
st.sidebar.subheader("🌧️ Climate & Infrastructure Inputs")

with st.sidebar.form("simulation_parameter_form"):
    global_rain = st.slider("Base Rainfall Intensity (mm/hr)", 0.0, 200.0, float(default_rain), 5.0)
    duration = st.number_input("Duration (Hours)", value=6.0, step=1.0)
    time_step = st.number_input("Time Step (Mins)", value=10.0, step=5.0)

    selected_epicenters = st.multiselect(
        "Target Rainfall Regions (Grid Epicenters):", 
        region_names, 
        default=default_epicenters
    )
    
    st.markdown("---")
    st.write("✏️ **Custom Region Rainfall Overrides:**")
    custom_rain_map = {}
    for name in region_names:
        init_val = default_rain_map.get(name, float(global_rain))
        if name in selected_epicenters:
            custom_rain_map[name] = st.number_input(
                f"🌧️ {name} (mm/hr)", 
                value=float(init_val), 
                min_value=0.0, max_value=200.0, step=5.0,
                key=f"override_{name}"
            )
        else:
            custom_rain_map[name] = 0.0

    st.markdown("---")
    st.subheader("🏗️ Drainage Infrastructure Upgrades")
    selected_drainage_zones = st.multiselect(
        "Select Regions to Deploy / Custom-Limit Drainage Infrastructure:",
        region_names,
        default=default_drainage_zones
    )
    
    custom_drainage_map = {}
    if selected_drainage_zones:
        st.write("🔧 **Set Drainage Throughput Limit (mm/hr):**")
        for d_name in selected_drainage_zones:
            base_d = default_drainage_values.get(d_name, next((r.drainage_capacity for r in base_regions if r.name == d_name), 30.0))
            custom_drainage_map[d_name] = st.number_input(
                f"🚰 {d_name} Drainage Capacity (mm/hr)",
                value=float(base_d),
                min_value=0.0, max_value=300.0, step=5.0,
                key=f"drain_{d_name}"
            )
            
    apply_changes = st.form_submit_button("✅ Apply Simulation Parameters", use_container_width=True)

active_regions = []
for r in base_regions:
    new_d = custom_drainage_map.get(r.name, r.drainage_capacity)
    active_regions.append(
        Region(
            id=r.id, name=r.name, sector=r.sector, grid_pos=r.grid_pos,
            elevation=r.elevation, drainage_capacity=new_d,
            initial_water_level=r.initial_water_level, max_capacity=r.max_capacity,
            population=r.population, terrain_type=r.terrain_type
        )
    )

start_r_ids = [r.id for r in active_regions if r.name in selected_epicenters]

scenario = Scenario(
    rainfall_intensity=global_rain,
    duration_hours=duration,
    rainfall_start_regions=start_r_ids,
    time_step_minutes=time_step,
    drainage_failure_regions=[]
)

engine = SimulationEngine(active_regions, scenario, flow_k=0.15, custom_rain_map=custom_rain_map)
sim_result = engine.run()

# Header
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
    "🌊 Water Level Progression Line Graph",
    "📜 Early Warning Export & Reports"
])

with tab1:
    st.subheader("⏱️ Time-Series Playback & Scrubber")
    
    time_steps = len(sim_result["times_h"])
    selected_step = st.slider("Scrub Simulation Time (Hours : Minutes)", 0, time_steps - 1, time_steps - 1)
    current_t = sim_result["times_h"][selected_step]
    
    st.caption(f"Viewing: ⚙️ **SIMULATION STATE at t={current_t:.2f} hrs**")
    
    curr_statuses = []
    for idx in range(len(active_regions)):
        w_lvl = sim_result["water_levels"][selected_step, idx]
        m_cap = sim_result["capacities"][idx]
        curr_statuses.append(classify_status(w_lvl, m_cap))
    
    sim_result["statuses"][selected_step] = curr_statuses
    
    num_critical = curr_statuses.count("Critical")
    num_warning = curr_statuses.count("Warning")
    num_safe = curr_statuses.count("Safe")
    
    avg_water_lvl = float(np.mean(sim_result["water_levels"][selected_step]))
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 CRITICAL FLOOD ZONES", f"{num_critical}/{len(active_regions)}", "Ratio ≥ 90% capacity")
    k2.metric("⚠️ WARNING CATCHMENTS", f"{num_warning}", "Ratio 60% - 89.9%")
    k3.metric("🟢 SAFE RESILIENT ZONES", f"{num_safe}", "Water level < 60%")
    k4.metric("💧 AVG WATER ACCUMULATION", f"{avg_water_lvl:.1f} mm", "Mean basin depth")
    
    st.markdown("---")
    
    layer_mode = st.radio(
        "Select Active Grid Layer:", 
        ["🚨 Flood Early Warning Status (Safe/Warning/Critical)", "💧 Water Accumulation Level (mm)", "⛰️ Terrain Elevation Topography (m)", "🚰 Storm Drainage Capacity (mm/hr)"], 
        horizontal=True
    )

    # Dynamic Legend Card based on selected active layer
    if "Status" in layer_mode:
        st.markdown("""
        <div class="legend-card">
            <b style="color: #58A6FF;">🎨 Flood Risk Classification Legend:</b>
            <div style="display: flex; gap: 20px; margin-top: 8px; flex-wrap: wrap; font-size: 13px;">
                <div><span style="color: #2ECC71; font-weight: bold;">🟢 Green (Safe)</span>: Water Level &lt; 2000 mm</div>
                <div><span style="color: #F39C12; font-weight: bold;">🟡 Yellow / Orange (Warning)</span>: Water Level 2000 mm – 3800 mm</div>
                <div><span style="color: #E74C3C; font-weight: bold;">🔴 Red (Critical)</span>: Water Level ≥ 3800 mm</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif "Water" in layer_mode:
        st.markdown("""
        <div class="legend-card">
            <b style="color: #58A6FF;">💧 Water Accumulation Legend:</b>
            <span style="font-size: 13px; margin-left: 10px;">Gradient scale from <b>Light Red (Low Depth, ~0 mm)</b> to <b>Dark Red (Deep Accumulation, >5000 mm)</b>. See side colorbar.</span>
        </div>
        """, unsafe_allow_html=True)
    elif "Elevation" in layer_mode:
        st.markdown("""
        <div class="legend-card">
            <b style="color: #58A6FF;">⛰️ Terrain Elevation Topography Legend:</b>
            <span style="font-size: 13px; margin-left: 10px;">Viridis gradient scale from <b>Dark Purple (Low Valley Basins, ~880m)</b> to <b>Bright Yellow/Green (Highland Ridges, ~935m)</b>. See side colorbar.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="legend-card">
            <b style="color: #58A6FF;">🚰 Storm Drainage Infrastructure Capacity Legend:</b>
            <span style="font-size: 13px; margin-left: 10px;">Blues gradient scale from <b>Light Blue (Low Capacity, ~10 mm/hr)</b> to <b>Deep Blue (High Capacity / Upgraded, 150-300 mm/hr)</b>. See side colorbar.</span>
        </div>
        """, unsafe_allow_html=True)

    fig_map = render_grid_heatmap(sim_result, selected_step, layer_mode, custom_rain_map=custom_rain_map)
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
        if eta == 0.0:
            eta_str = "0.0 hrs (Already Critical)"
        elif eta is not None and eta > 0:
            eta_str = f"{eta:.1f} hrs to Critical"
        else:
            eta_str = "Not projected"
            
        rows.append({
            "Region ID": r.id,
            "Region Name": r.name,
            "Sector": r.sector,
            "Elevation (m)": r.elevation,
            "Drainage Capacity (mm/hr)": r.drainage_capacity,
            "Rainfall (mm/hr)": f"{custom_rain_map.get(r.name, 0.0):.0f}",
            "Water Level (mm)": f"{lvl:.1f} / {cap:.0f}",
            "Status": curr_statuses[idx],
            "ETA to Critical Status": eta_str
        })
        
    df_reg = pd.DataFrame(rows)
    st.dataframe(df_reg, use_container_width=True)

with tab2:
    st.subheader("🧮 Mathematical Drainage Optimization Solver")
    st.caption("Gradient Descent solver prioritizing drainage capacity reinforcement.")
    budget = st.slider("Total Available Drainage Upgrade Budget (mm/hr)", 10.0, 200.0, 50.0)
    
    if st.button("🚀 Run Optimization Solver"):
        opt_res = optimize_drainage_allocation(active_regions, scenario, budget_mm_h=budget)
        st.success("Optimization Complete!")
        
        opt_rows = []
        for r in active_regions:
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

with tab3:
    st.subheader("🌊 Temporal Flood Progression Rates")
    fig_line = render_water_level_chart(sim_result)
    st.plotly_chart(fig_line, use_container_width=True)

with tab4:
    st.subheader("📜 Export Official Early Warning Report")
    st.write("Download the complete mathematical simulation output:")
    
    csv_data = df_reg.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Early Warning Report (CSV)",
        data=csv_data,
        file_name=f"FlowShield_Bangalore_Early_Warning_t{current_t:.1f}h.csv",
        mime="text/csv"
    )