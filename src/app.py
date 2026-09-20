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

@st.cache_data
def load_default_city():
    with open("data/sample_city.json", "r") as f:
        data = json.load(f)
        for r in data["regions"]:
            if r["max_capacity"] < 3000.0:
                r["max_capacity"] = 4500.0
        return data

city_data = load_default_city()

st.sidebar.title("🎛️ FlowShield Control Plane")

st.sidebar.subheader("📐 Grid Topology Configuration")
all_regions = [Region(**item) for item in city_data["regions"]]
region_names = [r.name for r in all_regions]

st.sidebar.subheader("🌧️ Climate & Rainfall Inputs")

with st.sidebar.form("simulation_parameter_form"):
    global_rain = st.slider("Base Rainfall Intensity (mm/hr)", 0.0, 200.0, 50.0, 5.0)
    duration = st.number_input("Duration (Hours)", value=6.0, step=1.0)
    time_step = st.number_input("Time Step (Mins)", value=10.0, step=5.0)

    selected_epicenters = st.multiselect(
        "Target Rainfall Regions (Grid Epicenters):", 
        region_names, 
        default=region_names[:6]
    )
    
    st.markdown("---")
    st.write("✏️ **Custom Region Overrides:**")
    custom_rain_map = {}
    for name in region_names:
        if name in selected_epicenters:
            custom_rain_map[name] = st.number_input(
                f"🌧️ {name} (mm/hr)", 
                value=float(global_rain), 
                min_value=0.0, max_value=200.0, step=5.0,
                key=f"override_{name}"
            )
        else:
            custom_rain_map[name] = 0.0

    st.markdown("---")
    st.subheader("🚧 Infrastructure Status")
    drainage_failures = st.multiselect("Blocked Drainage Regions (Drainage = 0)", region_names)
    
    flow_k = 0.15
    
    apply_changes = st.form_submit_button("✅ Apply Simulation Parameters", use_container_width=True)

start_r_ids = [r.id for r in all_regions if r.name in selected_epicenters]
failure_r_ids = [r.id for r in all_regions if r.name in drainage_failures]

scenario = Scenario(
    rainfall_intensity=global_rain,
    duration_hours=duration,
    rainfall_start_regions=start_r_ids,
    time_step_minutes=time_step,
    drainage_failure_regions=failure_r_ids
)

engine = SimulationEngine(all_regions, scenario, flow_k=flow_k, custom_rain_map=custom_rain_map)
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
    for idx in range(len(all_regions)):
        w_lvl = sim_result["water_levels"][selected_step, idx]
        m_cap = sim_result["capacities"][idx]
        curr_statuses.append(classify_status(w_lvl, m_cap))
    
    sim_result["statuses"][selected_step] = curr_statuses
    
    num_critical = curr_statuses.count("Critical")
    num_warning = curr_statuses.count("Warning")
    num_safe = curr_statuses.count("Safe")
    
    avg_water_lvl = float(np.mean(sim_result["water_levels"][selected_step]))
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🚨 CRITICAL FLOOD ZONES", f"{num_critical}/{len(all_regions)}", "Ratio ≥ 90% capacity")
    k2.metric("⚠️ WARNING CATCHMENTS", f"{num_warning}", "Ratio 60% - 89.9%")
    k3.metric("🟢 SAFE RESILIENT ZONES", f"{num_safe}", "Water level < 60%")
    k4.metric("💧 AVG WATER ACCUMULATION", f"{avg_water_lvl:.1f} mm", "Mean basin depth")
    
    st.markdown("---")
    
    st.markdown("""
    <div class="legend-card">
        <b style="color: #58A6FF;">🎨 Flood Risk Classification Legend:</b>
        <div style="display: flex; gap: 20px; margin-top: 8px; flex-wrap: wrap; font-size: 13px;">
            <div><span style="color: #2ECC71; font-weight: bold;">🟢 Green (Safe)</span>: Water Level &lt; 60% Capacity</div>
            <div><span style="color: #F39C12; font-weight: bold;">🟡 Yellow / Orange (Warning)</span>: Water Level 60% – 89.9% Capacity</div>
            <div><span style="color: #E74C3C; font-weight: bold;">🔴 Red (Critical)</span>: Water Level ≥ 90% Capacity (Flooding)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    layer_mode = st.radio(
        "Select Active Grid Layer:", 
        ["🚨 Flood Early Warning Status (Safe/Warning/Critical)", "💧 Water Accumulation Level (mm)", "⛰️ Terrain Elevation Topography (m)", "🚰 Storm Drainage Capacity (mm/hr)"], 
        horizontal=True
    )
    
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
        
        # Calculate time remaining strictly to reach Critical status (90%)
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
            "Drainage (mm/hr)": r.drainage_capacity,
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
        opt_res = optimize_drainage_allocation(all_regions, scenario, budget_mm_h=budget)
        st.success("Optimization Complete!")
        
        opt_rows = []
        for r in all_regions:
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