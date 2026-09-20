import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def render_grid_heatmap(sim_res: dict, time_idx: int, layer_mode: str, active_dragmode: str = "pan", custom_rain_map: dict = None):
    region_ids = sim_res["region_ids"]
    regions = sim_res["regions"]
    
    max_r = max(r.grid_pos[0] for r in regions.values()) + 1
    max_c = max(r.grid_pos[1] for r in regions.values()) + 1
    
    grid_data = np.zeros((max_r, max_c))
    annotations = []
    text_matrix = []
    
    for r_i in range(max_r):
        row_text = []
        for c_i in range(max_c):
            row_text.append("")
        text_matrix.append(row_text)
    
    for idx, rid in enumerate(region_ids):
        r = regions[rid]
        r_i, c_i = r.grid_pos
        
        rain_val = custom_rain_map.get(r.name, 0.0) if custom_rain_map else 0.0
        lvl = sim_res["water_levels"][time_idx, idx]
        cap = sim_res["capacities"][idx]
        
        # Calculate true status ratio
        if lvl < 2000.0:
            status_str = "Safe"
            status_icon = "🟢"
            status_val = 0.0   # Green
        elif lvl < 3800.0:
            status_str = "Warning"
            status_icon = "🟡"
            status_val = 0.5   # Yellow
        else:
            status_str = "Critical"
            status_icon = "🔴"
            status_val = 1.0   # Red
            
        if "Status" in layer_mode:
            val = status_val
            label = f"<b>{r.name}</b><br>{status_icon} {status_str}<br>🌧️ {rain_val:.0f} mm/hr<br>💧 {lvl:.1f} mm<br>🚰 {r.drainage_capacity:.0f} mm/h"
        elif "Water" in layer_mode:
            val = lvl
            label = f"<b>{r.name}</b><br>🌧️ {rain_val:.0f} mm/hr<br>💧 {lvl:.1f} mm"
        elif "Elevation" in layer_mode:
            val = r.elevation
            label = f"<b>{r.name}</b><br>⛰️ {val:.0f} m"
        else:
            val = r.drainage_capacity
            label = f"<b>{r.name}</b><br>🚰 {val:.0f} mm/h<br>⛰️ {r.elevation:.0f}m"
            
        grid_data[r_i, c_i] = val
        text_matrix[r_i][c_i] = r.name
        annotations.append(
            dict(x=c_i, y=r_i, text=label, showarrow=False, font=dict(color="white", size=10, family="Inter"))
        )

    if "Status" in layer_mode:
        colorscale = [
            [0.0, "#2ecc71"],
            [0.33, "#2ecc71"],
            [0.34, "#f39c12"],
            [0.66, "#f39c12"],
            [0.67, "#e74c3c"],
            [1.0, "#e74c3c"]
        ]
        z_min, z_max = 0.0, 1.0
    elif "Drainage" in layer_mode:
        colorscale = "Blues"
        z_min, z_max = 0.0, max(300.0, float(np.max(grid_data)))
    elif "Water" in layer_mode:
        colorscale = "Reds"
        z_min, z_max = 0.0, max(100.0, float(np.max(grid_data)))
    else:
        colorscale = "Viridis"
        z_min, z_max = float(np.min(grid_data)), float(np.max(grid_data))
    
    fig = go.Figure(data=go.Heatmap(
        z=grid_data,
        text=text_matrix,
        hoverinfo="text+z",
        colorscale=colorscale,
        showscale=False,
        zmin=z_min,
        zmax=z_max
    ))
    
    fig.update_layout(
        annotations=annotations,
        xaxis=dict(showgrid=True, gridcolor="#2D3748", zeroline=False, title="Grid Columns", fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor="#2D3748", zeroline=False, autorange="reversed", title="Grid Rows", fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=20, b=40),
        height=520,
        dragmode=active_dragmode
    )
    return fig

def render_water_level_chart(sim_res: dict):
    times = sim_res["times_h"]
    levels = sim_res["water_levels"]
    region_ids = sim_res["region_ids"]
    regions = sim_res["regions"]
    
    df_list = []
    for t_i, t in enumerate(times):
        for r_i, rid in enumerate(region_ids):
            df_list.append({
                "Time (Hours)": t,
                "Water Level (mm)": levels[t_i, r_i],
                "Region": regions[rid].name
            })
    df = pd.DataFrame(df_list)
    
    fig = px.line(
        df, x="Time (Hours)", y="Water Level (mm)", color="Region",
        template="plotly_dark"
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        height=350,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    return fig