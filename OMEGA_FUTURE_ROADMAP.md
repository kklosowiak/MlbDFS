# OMEGA Future Roadmap: The "Physics 2.0" Layer

These notes capture the proposed enhancements and long-term directions for the OMEGA model.

## 🚀 Completed / Calibrated (May 23 Sprint)

1. **Platoon Intelligence (The "Splits" Patch)**: Completed with Bayesian Hitter and Pitcher regressions, combined into a final `NPAS_xwOBA` platoon split difference.
2. **Bullpen Skill Grades (The "Closer" Layer)**: Completed. Bullpen skill multipliers are applied to stack scores, and fatigue boosts are scaled dynamically based on bullpen talent tier (dampened for elite pens, amplified for weak pens).
3. **Statcast "Smash Factor"**: Completed and calibrated using the standard `f2_matchup_synergy` formula (season OPS floor, rolling OPS momentum, and elite matchup xwOBA).
4. **Remove/Adjust Pitcher Debut Boost**: Completed. The debut visibility boost was removed/neutralized for starting pitchers.
5. **Cap Market Boosts for Weak-Hitting Stacks**: Completed. Market whale/shark multipliers were capped, and a 3.8 implied run total floor was added for DQI Trust ratings.
6. **Batting Order Weighting (Lineup Spot PA Decay)**: Completed and calibrated. Replaced steep decay with Moderate Lineup Spot PA Decay `[1.15, 1.12, 1.08, 1.04, 1.00, 0.96, 0.92, 0.88, 0.84]` to preserve bottom-of-the-order hitter variance.
7. **GPP Ownership Projections Proxy (The Leverage Engine)**: Completed. Heuristically projects ownership based on implied run totals, slate size, and SP matchup, exporting `gpp_leverage_index` and flagging `LEVERAGE PIVOT` teams in the dashboard.
8. **Ballpark Factor Dampening**: Completed and calibrated. Cuts stadium factor deviation from 1.0 in half (50% dampening) to eliminate venue bias.
9. **MSMI (Slate Momentum Index) Tuning**: Completed. Optimized rolling team form slump penalty to `-24.0` and surge boost to `+12.0` based on full-season backtest coordinate sweeps.
10. **Blended Stack Rating Display**: Completed. Integrated `(stack_score + attack_conf) / 2` as primary selection metric on JSON reports, terminal outputs, static dashboard, and dynamic cockpit.
11. **Matchup DNA: Pitch-Type Mapping**: Completed. Replaced standard platoon split multipliers with pitch-type usage xwOBA math vs. league averages when Statcast data is available.

---

## 📈 Long-Term Integration
*   **Automation**: Automatic "Snapshot velocity" detection (alerting if a line moves > 10 cents in 15 minutes).
*   **Weather 2.0**: Humidity and Air Density (DA) impact on HR potential.
*   **DraftKings Value Matrix (The "CSV Drop")**: Ingest local `dk_salaries.csv` files, cross-reference with Hitters Alpha, and isolate punts (sub-$3,500).
