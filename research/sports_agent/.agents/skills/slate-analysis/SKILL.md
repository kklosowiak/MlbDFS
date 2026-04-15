---
name: Slate_Analysis
description: Outlines the end-to-end workflow from data ingestion to Telegram push for MLB DFS.
---

# Slate_Analysis Skill

This skill governs the execution of a complete MLB slate analysis. Use this skill to automate the flow from raw data to final SE Feature Play delivery.

## 1. End-to-End Workflow

The following linear process must be followed for every production run:

### Phase A: Data Ingestion (Ground Truth)
-   **DK Salaries**: Synchronize with the specific `DraftGroup ID`.
-   **Lineups**: Pull latest confirmed starters (1-6 order only).
-   **Betting Intelligence**: Fetch Moneyline, Totals, and RLM (Reverse Line Movement).

### Phase B: Scoring & Environmental Modifiers
-   **Prop Alpha Scouting**: Run `prop_alpha_scout.py` to identify HR targets and sharp K-props.
-   **Matchup Mastery (⚔️)**: Cross-reference pitcher arsenal vs. hitter pitch-type splits to identify 'Matchup Alphas'.
-   **Environment Check**: Run `data_environment.py` to apply Park, Weather (Temp/Wind), and Umpire modifiers.

### Phase C: Lineup Generation (SE Optimized)
-   Execute `dfs_lineup_builder.js` using the **Pure 5-1-1-1** stacking constraint.
-   Lock high-leverage cores (e.g., Rumfield at 1B) based on current value signals.

### Phase D: Telegram Distribution
-   Push the final **🏆 SE FEATURE PLAY** and the **Full GPP Report** to the Telegram channel.

## 2. Mandatory Pre-Run Hierarchy
Before executing `main.py`, the following modules **must** be confirmed as operational:
1. `prop_alpha_scout.py` (Market Signals)
2. `data_environment.py` (Climate & Umpire logic)
