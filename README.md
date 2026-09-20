# FlowShield
# FlowShield: Hydrodynamic Early Warning and Urban Flood Intelligence Dashboard

FlowShield is a real-time hydrodynamic early warning, simulation, and decision-support system modeled on urban drainage basins and topography. Built with Streamlit, Plotly, NumPy, and Pandas, FlowShield models rainfall accumulation, overland flood routing, and drainage evacuation across connected urban catchments to deliver actionable intelligence for flood risk mitigation.

---

## System Architecture and Overview

FlowShield simulates surface water runoff and drainage dynamics across a 2D spatial grid representing Bangalore's key municipal and topographical sectors. The system couples hydrodynamic mass-balance physics with terrain elevation to predict flood depths, identify vulnerable populations, compute time-to-critical inundation thresholds, and mathematically optimize drainage infrastructure investments.

The platform provides:
- Real-time time-series playback and scrubbing over multi-hour storm events.
- Dynamic 2D spatial grid heatmaps representing risk tiers, water levels, elevations, and drainage capacities.
- Early warning registry with computed time-to-critical (ETA) values for disaster response prioritization.
- Mathematical optimization studio using greedy gradient-descent allocation to deploy drainage throughput where population impact is highest.
- Multi-line temporal progression graphs showing water level trajectories.
- Official early warning CSV report generation for municipal agencies and emergency responders.

---

## Mathematical Formulation and Physics Engine

The simulation engine models overland water dynamics using mass conservation, Manning's flow equation, gravity-driven hydraulic head differentials, and numerical stability criteria.

### 1. Hydraulic Head and Gradient

For each catchment region $i$, the total hydraulic head $H_i$ is defined by combining water depth $W_i$ (in mm converted to meters) with topographical terrain elevation $Z_i$ (in meters):

$$H_i = \frac{W_i}{1000.0} + Z_i$$

Between two adjacent connected cells $i$ and $j$, the hydraulic head differential is:

$$\Delta H_{ij} = H_i - H_j$$

The hydraulic slope (surface gradient) $S_{ij}$ over grid cell spacing $\Delta x$ is given by:

$$S_{ij} = \frac{|\Delta H_{ij}|}{\Delta x}$$

where $\Delta x = 1000\text{ m}$ (1 km spatial grid resolution).

### 2. Manning's Overland Flow Velocity

The flow velocity between adjacent cells is computed using Manning's open-channel equation:

$$v = \frac{1}{n} \cdot R_h^{2/3} \cdot \sqrt{S_{ij}}$$

where:
- $n$ is Manning's roughness coefficient (calibrated at $0.025\text{ s/m}^{1/3}$ for urbanized drainage surfaces).
- $R_h$ is the characteristic hydraulic radius approximated by the peak local water depth:
  $$R_h \approx \max\left(1.0, \frac{\max(W)}{1000.0}\right)$$
- $S_{ij}$ is the hydraulic gradient.

### 3. Inter-Cell Volumetric Discharge Flux

The volumetric flux transferred between connected neighboring cells $i$ and $j$ during a numerical sub-step $\Delta t_{\text{sub}}$ is given by:

$$Q_{ij} = k \cdot v \cdot \text{sgn}(\Delta H_{ij}) \cdot \Delta t_{\text{sub}} \cdot 1000.0$$

where:
- $k = 0.15$ is the inter-catchment transfer coefficient.
- $\text{sgn}(\Delta H_{ij})$ establishes directional gravity flow from higher total head to lower total head.
- Flux limiters ensure water cannot drain below zero:
  $$Q_{ij} \le W_i \quad \text{if } Q_{ij} > 0$$

### 4. Mass Balance Governing Equation

For each region $i$, the temporal rate of change of water accumulation is governed by:

$$\frac{dW_i}{dt} = R_i(t) - D_i(t) + \sum_{j \in \mathcal{N}(i)} Q_{ji}(t)$$

where:
- $R_i(t)$ is the incoming rainfall intensity ($\text{mm/hr}$).
- $D_i(t)$ is the effective drainage evacuation rate ($\text{mm/hr}$), constrained by current surface water availability:
  $$D_i = \min\left(W_i + R_i \cdot \Delta t_{\text{sub}}, \; C_{\text{drain}, i} \cdot \Delta t_{\text{sub}}\right)$$
- $\sum_{j \in \mathcal{N}(i)} Q_{ji}$ is the net overland inflow from adjacent grid neighbors.
- $W_i(t + \Delta t) \ge 0$ is strictly enforced to satisfy mass conservation.

### 5. Numerical Stability (CFL Condition)

To avoid numerical instabilities caused by steep hydraulic gradients, the engine calculates the maximum allowable time step using the Courant-Friedrichs-Lewy (CFL) gravity wave criterion:

$$\Delta t_{\text{CFL}} = \frac{\Delta x}{\sqrt{g \cdot h_{\max}}}$$

where $g = 9.81\text{ m/s}^2$ and $h_{\max} = \max(1.0, \max(W) / 1000.0)\text{ m}$.

The simulation time step $\Delta t$ is partitioned into $N_{\text{substeps}}$ internal iterations:

$$N_{\text{substeps}} = \max\left(1, \; \left\lceil \frac{\Delta t}{\Delta t_{\text{CFL}}} \right\rceil\right), \quad \Delta t_{\text{sub}} = \frac{\Delta t}{N_{\text{substeps}}}$$

### 6. Risk Classification Tiers

Regions are classified based on cumulative water depth thresholds:

- **Safe**: $W < 2000.0\text{ mm}$ (Green)
- **Warning**: $2000.0\text{ mm} \le W < 3800.0\text{ mm}$ (Yellow / Orange)
- **Critical**: $W \ge 3800.0\text{ mm}$ (Red)

### 7. Time-to-Critical (ETA) Calculation

The estimated time remaining before a catchment breaches the critical threshold ($W_{\text{crit}} = 3800\text{ mm}$) is calculated as:

$$\text{ETA}_{\text{critical}} = \begin{cases}
0.0\text{ hrs}, & \text{if } W_i \ge W_{\text{crit}} \\
\frac{W_{\text{crit}} - W_i}{\frac{dW_i}{dt}}, & \text{if } \frac{dW_i}{dt} > 0 \\
\text{Not projected}, & \text{if } \frac{dW_i}{dt} \le 0
\end{cases}$$

### 8. Drainage Optimization Solver

The mathematical optimization module implements a greedy gradient-descent solver. It identifies the optimal allocation of an infrastructure upgrade budget $B$ (in $\text{mm/hr}$) across regions to minimize the total population in flooded zones:

$$\min_{\{d_i\}} \sum_{i=1}^{N} P_i \cdot \mathbb{I}\left(W_i(T) \ge 2000\text{ mm}\right) \quad \text{subject to} \quad \sum_{i=1}^N d_i \le B, \quad d_i \ge 0$$

The algorithm steps in increments of $\Delta b = 10\text{ mm/hr}$, iteratively assigning additional capacity to the region that achieves the maximum reduction in affected population. If no further population reduction is possible, remaining capacity is uniformly distributed across existing Critical regions.

---

## Simulation Parameters

| Parameter | Symbol | Default Value | Range / Unit | Description |
|---|---|---|---|---|
| Grid Size | $M \times N$ | $4 \times 4$ | 16 zones | Spatial representation of urban catchments |
| Cell Spacing | $\Delta x$ | $1000.0$ | meters | Distance between cell centers |
| Simulation Duration | $T$ | $6.0$ | $1.0 - 24.0\text{ hrs}$ | Total duration of the storm scenario |
| Macro Time Step | $\Delta t$ | $10.0$ | $5.0 - 30.0\text{ mins}$ | Primary simulation reporting step |
| Base Rainfall Intensity | $R_{\text{base}}$ | $40.0$ | $0.0 - 200.0\text{ mm/hr}$ | Global precipitation intensity |
| Manning Roughness | $n$ | $0.025$ | $\text{s/m}^{1/3}$ | Roughness coefficient for urban surface channels |
| Inter-catchment Transfer Coefficient | $k$ | $0.15$ | dimensionless | Inter-cell flow attenuation scalar |
| Critical Risk Threshold | $W_{\text{crit}}$ | $3800.0$ | mm | Water level denoting critical flood emergency |
| Warning Risk Threshold | $W_{\text{warn}}$ | $2000.0$ | mm | Water level denoting elevated risk |
| Baseline Storage Capacity | $C_{\max}$ | $4500.0$ | mm | Minimum catchment volume capacity |
| Drainage Upgrade Budget | $B$ | $50.0$ | $10.0 - 200.0\text{ mm/hr}$ | Total throughput capacity available for optimization |

---



---

## Scenario Presets

The dashboard includes three pre-configured scenarios:

1. **Preset 1: Multi-Risk City (Green, Yellow & Red Mix)**
   - Heterogeneous storm distribution (10–65 mm/hr) across sectors with selective baseline drainage. Demonstrates simultaneous safe, warning, and critical risk bands.
2. **Preset 2: Severe Monsoonal Crisis (High Critical Risk)**
   - Widespread heavy rainfall (80 mm/hr) across all 16 regions with unreinforced drainage, simulating severe catchment inundation.
3. **Preset 3: Infrastructure Resilient Basin (Mostly Safe)**
   - Moderate storm (35 mm/hr) coupled with reinforced drainage infrastructure (100–200 mm/hr) at critical choke points (Koramangala, Bellandur, Silk Board), maintaining low water accumulation.

---

## Running the Application

Ensure Python 3.10+ is installed along with the required libraries.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Sujeeth-Yargol/FlowShield.git
   cd FlowShield
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Streamlit application**:
   ```bash
   streamlit run src/app.py
   ```

4. **Access the dashboard**:
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Repository Structure

```
FlowShield/
├── data/
│   └── sample_city.json       # Topographical, elevation, population, and capacity data for 16 sectors
├── src/
│   ├── __init__.py
│   ├── analytics.py           # Risk summary and registry helpers
│   ├── app.py                 # Streamlit dashboard interface and scenario coordinator
│   ├── classification.py      # Water depth risk classification and ETA projection
│   ├── mock_sim.py            # Simulation stubs
│   ├── models.py              # Region and Scenario dataclasses
│   ├── scenarios.py           # Scenario templates
│   ├── simulation.py          # Hydrodynamic simulation engine and optimization solver
│   └── visualization.py       # Plotly 2D heatmap and time-series line chart renderers
├── tests/
│   └── test_classification.py # Unit tests for classification boundaries
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

### Team Information
Team Name: Stack Overflow
Members: Samrudh AV, Sai Chiranth M, Sujeeth Yargol, Saksham Singh

## Libraries and Dependencies

FlowShield is implemented in Python and relies on the following core libraries:

- **Streamlit**: Interactive web dashboard framework providing reactive user inputs, sidebar forms, sliders, tabs, and real-time state re-rendering.
- **NumPy**: Vectorized array operations, CFL time-step calculations, hydraulic head differential matrices, and numerical mass conservation.
- **Pandas**: Structured time-series datasets, risk registry tables, and CSV report formatting.
- **Plotly**: Dynamic data visualizations, including the 2D spatial heatmap grid and multi-series water depth progression charts.
---
## AI Collaboration & Development Tools:
Antigravity IDE — Primary Agentic IDE & Execution Environment

Claude — Algorithm Design, Refactoring & Code Logic Architecture

ChatGPT — Mathematical Scaffolding, Documentation & Preset Formulation

Gemini — Real-Time Problem Solving, Prompt Engineering & Script Generation

VS Code — Source Code Editing, Git Workflows & Workspace Management
---
### Scientific Foundations
* *Manning's Equations* for Open-Channel Flow Hydraulics
* *Courant-Friedrichs-Lewy (CFL)* Gravity Wave Stability Criteria
* *Bangalore Basin Spatial Modeling* inspired by BBMP Storm-Water Drain Networks
* 
### Scientific & Domain Foundations

Manning's Open-Channel Flow Formulations — Used for modeling overland gravity flow velocities across urban surfaces.

Courant-Friedrichs-Lewy (CFL) Condition — Applied to maintain numerical stability across dynamic hydraulic gradients.

Bangalore Drainage & Topographical Insights — Topographical elevation variations and catchment spatial layouts inspired by BBMP (Bruhat Bengaluru Mahanagara Palike) storm-water drain network dynamics.
