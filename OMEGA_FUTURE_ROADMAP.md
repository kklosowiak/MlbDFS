# OMEGA Future Roadmap: The "Physics 2.0" Layer

These notes capture the proposed enhancements and long-term directions for the OMEGA model.

## 🚀 Completed / Calibrated (May 23 Sprint)

1. **Platoon Intelligence (The "Splits" Patch)**: Completed with Bayesian Hitter and Pitcher regressions, combined into a final `NPAS_xwOBA` platoon split difference.
2. **Bullpen Skill Grades (The "Closer" Layer)**: Completed. Bullpen skill multipliers are applied to stack scores, and fatigue boosts are scaled dynamically based on bullpen talent tier (dampened for elite pens, amplified for weak pens).
3. **Statcast "Smash Factor"**: Completed and calibrated using the standard `f2_matchup_synergy` formula (season OPS floor, rolling OPS momentum, and elite matchup xwOBA).
4. **Remove/Adjust Pitcher Debut Boost**: Completed. The debut visibility boost was removed/neutralized for starting pitchers.
5. **Cap Market Boosts for Weak-Hitting Stacks**: Completed. Market whale/shark multipliers were capped, and a 3.8 implied run total floor was added for DQI Trust ratings.

---

## 🧠 High-Priority Research (Next Phase)

### 1. Batting Order Weighting (The "Lineup" Pillar)
*   **Concept**: Explicitly weight the lineup order when aggregating hitter physics and projections into the team stack score.
*   **Logic**: 
    - The top 4 batting positions capture over 60% of run-scoring upside.
    - Apply decay multipliers (e.g., spots 1–4: `1.2x`, spots 8–9: `0.7x`) to hitter physics scores before sum/blend.
*   **Objective**: Prevent teams with weak top-of-the-order hitters but deep benches from being artificially inflated.

### 2. GPP Ownership Projections Proxy (The "Leverage" Engine)
*   **Concept**: Heuristically estimate player/team ownership to isolate the leverage gap.
*   **Logic**: 
    - Estimate team ownership using implied run totals, slate size, and starting pitcher matchup.
    - Compute a `GPP Leverage Index` defined as `OMEGA_Score / Projected_Ownership`.
*   **Objective**: Directly highlight low-owned, high-upside stacks in the cockpit dashboard.

---

## 📈 Long-Term Integration
*   **Automation**: Automatic "Snapshot velocity" detection (alerting if a line moves > 10 cents in 15 minutes).
*   **Weather 2.0**: Humidity and Air Density (DA) impact on HR potential.
*   **DraftKings Value Matrix (The "CSV Drop")**: Ingest local `dk_salaries.csv` files, cross-reference with Hitters Alpha, and isolate punts (sub-$3,500).
