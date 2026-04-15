# Konrad Sharp DFS Model v4.2 | Technical Manual

This document serves as the Master Logic Guide for the Konrad Sharp DFS Model, a production-ready "Set-and-Forget" MLB analytics engine.

## 1. Core Mathematical Protocol
The model operates on a **40/30/30 Hybrid-Relative Archetype**. Every player, pitcher, and team is evaluated against three distinct pillars:

| Pillar | Max Points | Metrics & Weighing |
| :--- | :---: | :--- |
| **Baseline Floor** | **40.0** | The fundamental starting point for all confirmed players. |
| **Physics Pillar** | **30.0** | **SP:** Weighted SIERA & CSW% (2024-2026). <br>**Hitters:** weighted xwOBA & On-the-fly ISO splits. |
| **Market Pillar** | **30.0** | **ML:** +15 pts for >20c move. <br>**TT:** +15 pts for >0.3 run jump. |
| **Signal Spikes** | **+5.0 ea** | Additive boosts (Target, Flame, Alpha, etc.) that override the 100-pt cap. |

## 2. Signal & Branding Key
- **⚡ KONRAD OVERDRIVE:** Scores > 100.0 trigger the **Cyan Glow (#00FFFF)** effect. This signals a maximum conviction play where Physics, Market, and Props have converged.
- **🎯 TARGET:** Triggered for elite K-props (Line >= 6.5 or Juice <= -135) or high-efficiency xwOBA matchups.
- **🔥 ELITE:** Awarded to players in the upper 5% of historical production baselines.
- **🎰 SHARP**: Market Handle Convergence. Triggers when the **Pinnacle (Sharp)** price is at least **15 points** more bullish/shorter than the public DraftKings line. High-conviction professional alignment.

## 3. Production Workflow
1.  **Ingestion:** The Odds API V4 (`/events`, `/odds`, `/scores`).
2.  **Discovery:** Surgical Prop-Market analysis resolves "TBD" starters (The Ghost Kill Protocol).
3.  **Refinement:** Stats are anchored to a 3-season weighted average (2024: 30%, 2025: 50%, 2026: 20%).
4.  **Elite Constraint:** Matrices are surgically capped to the **Top 10** entries per category to preserve high-alpha focus.
5.  **Generation:** The Tabbed Control Center yields three matrices: Pitchers Matrix, Hitters Matrix, and Teams Matrix.

---
**Model Version:** v4.2 "True-North" Handover
**Owner:** Konrad
**Integrity Status:** Locked for Production
