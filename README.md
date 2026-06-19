
```markdown
# Security-Constrained Economic Dispatch (SCED) & N-1 Contingency Simulator

A high-performance Python-based power systems market clearing engine. This tool simulates a 3-bus meshed transmission grid, performing basic Economic Dispatch (ED), Security-Constrained Economic Dispatch (SCED), predictive N-1 Contingency Analysis, and Locational Marginal Pricing (LMP) calculations.

The core architecture uses a Power Transfer Distribution Factor (PTDF) matrix to map generation assets to physical line flows, identifying and clearing transmission bottlenecks programmatically.

---

## 🚀 Engine Architecture

The simulator executes sequentially across five distinct stages to move the grid from an unconstrained economic ideal to a highly secure, physically verified operational state:


```

[Stage 1: Baseline ED]
│
▼
[Stage 2: Physical Flow Tracking]
│
▼
[Stage 3: Base-Case SCED Loop]
│
▼
[Stage 4: Preventative N-1 SCED]
│
▼
[Stage 5: Locational Marginal Pricing]

```

1. **Stage 1: Unconstrained Baseline Economic Dispatch** Calculates the system-wide market clearing lambda ($\lambda$) using incremental cost curves and dispatches generators to meet the system load at minimal cost, ignoring network limits.
2. **Stage 2: Physical Network Flow Tracking** Projects generator outputs onto physical transmission lines using a linear algebra PTDF matrix ($\text{Flow} = \text{PTDF} \times \text{Generation}$).
3. **Stage 3: Security-Constrained Re-Dispatch (Base Case)** Triggers a feedback optimization loop if a transmission line violates its **Normal Limit**, shifting generation to eliminate the baseline overload.
4. **Stage 4: Preventative N-1 Security Optimization** Simulates predictive outages of every critical transmission line one-by-one. If a simulated outage pushes a surviving line past its **Emergency Limit**, a preventative loop shifts power *proactively* during normal operations to guarantee security under contingency conditions.
5. **Stage 5: Locational Marginal Pricing (LMP)** Deconstructs the single market clearing price into separate bus-specific nodes based on marginal congestion impacts, capturing advanced grid phenomena like negative LMPs.

---

## 📖 Glossary of Terms

### 🌐 Core Power Grid Concepts
* **Economic Dispatch (ED):** Allocating total electricity demand among available units in the most cost-effective manner possible based purely on incremental production costs.
* **Security-Constrained Economic Dispatch (SCED):** An advanced optimization process that modifies generator targets to ensure that physical transmission line capacities are never violated during normal or emergency states.
* **PTDF (Power Transfer Distribution Factor):** A linear algebra sensitivity matrix determining what percentage of power injected at a specific generator bus physically flows across each individual transmission line in a meshed grid.
* **Normal Limit (Continuous Rating):** The maximum thermal capacity (in MW) that a transmission line can carry safely day in and day out without overheating or degrading the physical wires.
* **Emergency Limit (Short-Term Rating):** A higher thermal limit that a line can withstand for a very brief window (typically 15 to 30 minutes) during a crisis before immediate structural failure occurs.
* **N-1 Contingency:** A standard reliability rule requiring power grids to be operated such that if any *single* component suddenly fails, the remaining system remains entirely stable and within emergency limits.
* **Preventative Re-Dispatch:** Proactively changing the generation mix during normal, healthy operations to leave headroom on the grid, ensuring that if a predicted worst-case N-1 line trip occurs, surviving lines will not cascade into an overload.

### 💵 Power Market Financial Concepts
* **System Lambda ($\lambda$):** The unconstrained market-clearing price of electricity. It represents the incremental cost of producing the next megawatt of power using the cheapest available generator, ignoring network limitations.
* **Shadow Price ($\mu$):** An optimization value assigned to a congested line. It represents the exact financial savings the wholesale market would realize per hour if the capacity of that specific bottleneck line could be expanded by 1 MW.
* **LMP (Locational Marginal Pricing):** The dynamic, real-time price of wholesale electricity at a specific physical bus (node) on the grid, calculated as:
  $$\text{LMP} = \text{Marginal Energy Component} + \text{Marginal Loss Component} + \text{Marginal Congestion Component}$$
* **Negative LMP:** A pricing phenomenon where the congestion component outweighs the baseline energy component. This happens when consuming power at a specific bus actively reduces stress on a jammed line, meaning the market structurally *pays* users to consume power at that node to stabilize the physical grid.

---

## 🛠️ Configuration & Setup

### Requirements
* Python 3.8+
* NumPy

### Input Data Layout (`sced_config.json`)
The simulation configuration should be placed in the project root directory following this schema:

```json
{
  "system_load": 250.0,
  "generators": [
    { "id": 1, "a": 0.04, "b": 15.0, "p_min": 10.0, "p_max": 150.0 },
    { "id": 2, "a": 0.05, "b": 20.0, "p_min": 10.0, "p_max": 100.0 },
    { "id": 3, "a": 0.03, "b": 35.0, "p_min": 20.0, "p_max": 200.0 }
  ],
  "transmission_lines": [
    { "id": "Line_1-2", "normal_limit": 100.0, "emergency_limit": 130.0 },
    { "id": "Line_2-3", "normal_limit": 50.0, "emergency_limit": 75.0 },
    { "id": "Line_1-3", "normal_limit": 80.0, "emergency_limit": 110.0 }
  ]
}

```

### Execution

To run the end-to-end simulation, optimize the network constraints, and output the locational market prices, execute the main script:

```bash
python sced_engine.py

```

```
