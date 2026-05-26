# OMEGA 3.0: Architectural Upgrades Blueprint

This document details the technical specifications, mathematical logic, and implementation pathways for the proposed OMEGA 3.0 architectural upgrades. These changes shift the model from static parameter-tuning to a dynamic, self-correcting decision engine.

---

## 1. 🧮 Integrated ILP Lineup Optimizer (The Knapsack Solver)

### Technical Specification
Instead of manually translating stack confidence ratings into lineups, we will integrate a native Integer Linear Programming (ILP) solver using Python's `PuLP` library. The optimizer will maximize projected fantasy points (derived from Hitter/Pitcher Alpha scores) under strict DFS salary cap and roster constraints.

### Mathematical Formulation
Let $x_i \in \{0, 1\}$ be the decision variable indicating whether player $i$ is selected.
Maximize the objective function:
$$\sum_{i} \text{Alpha}_i \cdot x_i$$
Subject to:
1. **Salary Constraint**: $\sum_{i} \text{Salary}_i \cdot x_i \le \$50,000$ (DraftKings cap)
2. **Roster Requirements**:
   - $\sum_{\text{Pitchers}} x_i = 2$
   - $\sum_{\text{Catchers}} x_i = 1$
   - $\sum_{\text{First Base}} x_i = 1$
   - $\sum_{\text{Second Base}} x_i = 1$
   - $\sum_{\text{Third Base}} x_i = 1$
   - $\sum_{\text{Shortstop}} x_i = 1$
   - $\sum_{\text{Outfielders}} x_i = 3$
3. **Stacking Rule (e.g. 5-3 stack)**: Forces selection of 5 players from Team A and 3 players from Team B to maximize correlation.

### Implementation Pathway
- Create [engine/optimizer.py](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/engine/optimizer.py) to read DraftKings CSV exports.
- Map player names to OMEGA hitters using our existing resilient name-normalization module.
- Solve the ILP using CBC (PuLP default) and return the top 10 unique lineups.

---

## 2. 🧬 Matchup DNA: Pitch-Type Mapping

### Technical Specification
Standard platoon adjustments look only at handiness. OMEGA 3.0 will map starting pitchers' pitch mixes directly to hitter performance distributions.

### Mathematical Formulation
Let $P = \{p_1, p_2, \dots, p_n\}$ be the set of pitch types thrown by the opposing starter, and $W = \{w_1, w_2, \dots, w_n\}$ be the pitcher's percentage usage of each pitch.
Let $H_{\text{woba}} = \{h_1, h_2, \dots, h_n\}$ be the hitter's expected xwOBA against each pitch type.
The DNA Matchup xwOBA ($xwOBA_{\text{DNA}}$) is calculated as:
$$xwOBA_{\text{DNA}} = \sum_{j} w_j \cdot h_j$$

### Implementation Pathway
- Ingest Statcast pitch-mix profiles for starting pitchers (e.g., Slider 35%, Sinker 25%, Four-Seam 25%, Changeup 15%).
- Maintain a local hitter database storing career xwOBA against individual pitches.
- Replace simple platoon multipliers in [utils/platoon_math.py](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/utils/platoon_math.py) with the dynamic $xwOBA_{\text{DNA}}$ product.

---

## 3. 📈 High-Frequency Line Velocity Tracker

### Technical Specification
Track the speed and momentum of odds movements (steam) in the hours leading up to lock to detect late-breaking sharp consensus.

### Mathematical Formulation
Let $ITT_t$ be the implied team total at time $t$ (in minutes before lock). The Velocity ($V$) of line movement is:
$$V_t = \frac{ITT_t - ITT_{t-15}}{15}$$
If $V_t \ge 0.0267$ runs/minute (equivalent to a $+0.40$ run move in 15 minutes), trigger a **High-Priority Steam Alert**.

### Implementation Pathway
- Set up a background daemon in [server.py](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/server.py) that updates every 10 minutes.
- Save historical snapshots to a memory-backed cache (`data/odds_velocity.json`).
- If Velocity exceeds the threshold, auto-inject a `Line Velocity Boost` (+8 CONF) to the targeted team stack.

---

## 4. 🔄 Auto-Correcting Bayesian Feedback Loop

### Technical Specification
Enable the model to self-correct its weights based on rolling short-term actual outcomes, adjusting to macro trends (like cold climate runs suppression in April/May).

### Mathematical Formulation
Let $\theta$ be a signal weight (e.g., `weather_temp_boost`). Update the weight daily based on the prediction error $e = Y_{\text{actual}} - \hat{Y}_{\text{pred}}$:
$$\theta_{t+1} = \theta_t + \lambda \cdot e \cdot X_t$$
where $X_t$ is the weather signal intensity and $\lambda$ is a small learning rate (e.g., $0.05$).

### Implementation Pathway
- Connect the production script to [run_post_mortem.py](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/run_post_mortem.py).
- Build a lightweight database (`data/feedback_loop.db`) to record daily projection error vectors.
- Apply rolling gradient updates to the model parameter configurations stored in `config.py`.
