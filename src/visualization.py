import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def render_grid_heatmap(sim_res: dict, time_idx: int, layer_mode: str, active_dragmode: str = "select", custom_rain_map: dict = None):
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
        
        # Determine rainfall intensity for this specific cell
        rain_val = custom_rain_map.get(r.name, 45.0) if custom_rain_map else 45.0
        
        if "Status" in layer_mode:
            val = sim_res["water_levels"][time_idx, idx] / r.max_capacity
            status = sim_res["statuses"][time_idx][idx]
            label = f"<b>{r.name}</b><br>● {status}<br>🌧️ {rain_val:.0f} mm/hr<br>💧 {sim_res['water_levels'][time_idx, idx]:.1f} mm<br>⛰️ {r.elevation:.0f}m"
        elif "Water" in layer_mode:
            val = sim_res["water_levels"][time_idx, idx]
            label = f"<b>{r.name}</b><br>🌧️ {rain_val:.0f} mm/hr<br>💧 {val:.1f} mm"
        elif "Elevation" in layer_mode:
            val = r.elevation
            label = f"<b>{r.name}</b><br>⛰️ {val:.0f} m"
        else:
            val = r.drainage_capacity
            label = f"<b>{r.name}</b><br>🚰 {val:.0f} mm/h"
            
        grid_data[r_i, c_i] = val
        text_matrix[r_i][c_i] = r.name
        annotations.append(
            dict(x=c_i, y=r_i, text=label, showarrow=False, font=dict(color="white", size=10, family="Inter"))
        )

    colorscale = [
        [0.0, "#2ecc71"],
        [0.6, "#f39c12"],
        [0.9, "#e74c3c"],
        [1.0, "#900c3f"]
    ] if "Status" in layer_mode else "Reds"
    
    fig = go.Figure(data=go.Heatmap(
        z=grid_data,
        text=text_matrix,
        hoverinfo="text+z",
        colorscale=colorscale,
        showscale=False
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