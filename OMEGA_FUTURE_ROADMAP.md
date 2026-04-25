# OMEGA Future Roadmap: The "Physics 2.0" Layer

These notes capture the proposed enhancements identified during the April 16th post-mortem. These are deferred tasks to be evaluated after observing the performance of the v6.1.1 "Hardening" update.

## 🧠 High-Priority Research (Next Phase)

### 1. Platoon Intelligence (The "Splits" Patch)
*   **Concept**: Explicitly weight the handedness matchup between Hitter and Pitcher.
*   **Logic**: 
    - Opposite Hand (L vs R): +8% Alpha Boost.
    - Same Hand (L vs L / R vs R): -5% Alpha Penalty (escalating for elite pitchers).
*   **Objective**: Reduce the "Fried Trap" by penalizing same-handed matchups against elite starters.

### 2. Bullpen Skill Grades (The "Closer" Layer)
*   **Concept**: Move beyond "Fatigue" to "Quality."
*   **Logic**: Tag team bullpens with a K-rate ranking.
    - Elite Pen (e.g., CLE, MIL): -5% Hitter penalty.
    - Weak Pen (e.g., COL, CWS): +10% Hitter boost.
*   **Objective**: Capture the true value of stacks facing weak middle relief.

### 3. Statcast "Smash Factor"
*   **Concept**: Integrate Exit Velocity (EV) and HardHit% into the Hitter Alpha.
*   **Logic**: Replace or supplement the `ops` momentum with a `HardHit_delta`.
*   **Objective**: Identify "Unlucky Stars" who are hitting rockets but haven't cashed yet.

## 📈 Long-Term Integration
*   **Automation**: Automatic "Snapshot velocity" detection (alerting if a line moves > 10 cents in 15 minutes).
*   **Weather 2.0**: Humidity and Air Density (DA) impact on HR potential.
*   **DraftKings Value Matrix (The "CSV Drop")**: Ingest local `dk_salaries.csv` files generated via manual export from the DraftKings contest page. Cross-reference salaries with the Hitters Alpha `xwOBA` matrix to isolate elite punts (sub-$3,500) and build a definitive Value per Dollar ($) dashboard to perfectly complement the Teams matrix.

---
*Note: These changes are currently on hold to allow the 40/25 Market/Physics re-weighting (v6.1.1) to be validated on the April 17th slate.*
