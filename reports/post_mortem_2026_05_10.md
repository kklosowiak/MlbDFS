# ⚾ OMEGA Post-Mortem: May 10, 2026

## 📌 Executive Summary
The morning slate was a success ("cashed"), while the 4-game afternoon slate was a "super close" miss. Forensic analysis reveals that while OMEGA correctly identified the **Arizona Diamondbacks** stack and hit on one-off targets like **Jordan Walker** and **Oneil Cruz**, it suffered from high-variance outcomes in the LAD/ATL matchup and a model "blind spot" on **Eduardo Rodriguez**.

---

## 📉 Post-Mortem Analysis

### ✅ The "Hits" (Logic Validation)
*   **Matt Olson (ATL):** Projected as the #1 Hitter Spotlight (103.2 OMEGA). **Result:** Home Run.
*   **ARI @ NYM Matchup:** The engine correctly projected a Diamondbacks victory and a productive stack environment (5-1 final).
*   **Jordan Walker (STL):** Projected as a "One-Off Power Target" (82.8 OMEGA). **Result:** Home Run.
*   **Oneil Cruz (PIT):** Projected as GPP Leverage (65.3 OMEGA). **Result:** Home Run.

### ❌ The "Misses" (Variance & Model Logic)
*   **LAD @ ATL (Stack Ranking):** OMEGA favored the Dodgers (92.2) over the Braves (89.1). The Dodgers offense stalled (2 runs), while the Braves exploded for 7 runs.
*   **Eduardo Rodriguez (ARI):** Rodriguez was a "Fade Zone" target (62.2) due to low market juice. He outplayed this significantly, pitching into the 9th with 8 K's. This highlights a need to respect "Physics" upside even when the "Market" is quiet on a veteran arm.

### 🛑 Data Integrity (PIT & STL Games)
*   **Stale Probables:** The PIT/SFG and STL/SDP games had incorrect starting pitchers in the report (Bubba Chandler and Kyle Leahy). This created noise in the lower-tier projections, though the main LAD/ATL and ARI/NYM matchups were data-correct.

---

## 🛠️ Hardening Fixes (Data Coverage)
We have implemented the following improvements to ensure the engine has the best possible "field of vision" for the next slate:

1.  **Roster Discovery Expansion:** `hitter_prop_analyzer.py` now discovers **18 players** (up from 10) per team. This ensures no bench players or elite veterans on cold streaks are "ghosted" from the discovery phase.
2.  **Unified Cache Expansion:** `statcast_bridge.py` now tracks **1,057 profiles** (up from ~280), covering the entire active MLB roster.
3.  **Probable Refresh Logging:** `probable_pitcher_fetcher.py` now logs the target fetch date to prevent slate window drift.

---

## 📈 Minor Tweaks (Logic Hardening)
Based on today's pitching performance (Gavin Williams/Payton Tolle) and your success with the Reds stack, we have implemented two surgical logic tweaks:

1.  **The "Neutral K-Zone":** Matchups between -3% and +3% K-boost are now treated as neutral. This prevents the model from overvaluing pitchers like Gavin Williams who are facing mediocre strikeout teams (like the Twins).
2.  **The "Exhaustion" Accelerator:** Increased the "Gassed Bullpen" stack bonus from 15% to 20%. This rewards the model for leaning harder into the fatigue signals that helped you identify the Reds stack today.

---
**Conclusion:** The engine's individual hitter discovery was actually quite strong today (Olson, Walker, Cruz all hit HRs). The miss came down to stack-ranking variance and a market-heavy fade on E-Rod. We are moving forward with the original logic but with significantly hardened data coverage and more disciplined pitching filters.
