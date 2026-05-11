# 🔱 OMEGA v7.6: Technical Architecture & Core Physics
**"The Sharpest Blade in the MLB DFS Market"**

## 1. The Multi-Pillar Core Philosophy
OMEGA is built on the principle of **Triangulation**. It does not trust any single data source. Instead, it reconciles three conflicting perspectives to find "The Truth."

1.  **The Physics Pillar (Statcast):** What is *physically* happening on the field (Exit Velo, xwOBA, SIERA, CSW).
2.  **The Market Pillar (Sharps):** What the smartest money in the world *thinks* will happen (Line moves, Whale/Shark divergence).
3.  **The Environmental Pillar (Context):** The invisible factors that tilt the game (Umpire bias, Bullpen fatigue, Park physics, Altitude).

---

## 2. Pitcher Matrix: The "Alpha/Beta" Hierarchy
The engine scores pitchers using a tiered weighting system designed to identify both high-floor "Cores" and high-ceiling "GPP Pivots."

### A. The Pure Talent Gate
*   **Metric:** (SIERA Score + CSW Score) / 2.
*   **Logic:** If a pitcher’s raw physics score is **< 55**, they are flagged. The engine will not trust "Sharp" money on a bad pitcher unless the environment (Umpire/Park) is overwhelmingly favorable.

### B. Alpha Signals (The High-Conviction "Target" Zones)
*   **Whale Signal:** Market divergence >= 15% (Whale money vs. Public volume).
*   **Shark Signal:** Sharp movement on both the Moneyline AND the Under.
*   **Steam Signal:** Aggressive line movement in a short window.

### C. The "Neutral K-Zone" (v7.6 Hardening)
*   **Logic:** OMEGA ignores opponent strikeout boosts between **-3% and +3%**. This prevents "False Positives" on pitchers facing mediocre contact teams, ensuring we only target genuine strikeout-vulnerable lineups.

---

## 3. Hitter Alpha: Momentum & Discovery
OMEGA uses a rolling-window analysis to find hitters about to "explode" before the market prices them in.

### A. Roster Discovery (Depth & Field of Vision)
*   **Window:** Top 18 hitters per team (expanded from 10).
*   **Momentum Cache:** Tracks 1,057+ active player profiles.
*   **Logic:** By looking 18-players deep, OMEGA catches elite veterans on cold streaks or high-leverage bench bats that other models "ghost."

### B. The "Abrams Patch" (Price Manipulation Floor)
*   **Logic:** If a hitter has elite Physics (xwOBA > .380), the engine sets a **Market Floor**. This prevents bookmakers from "tricking" the model by setting a high +HR price (e.g., +800) on a player who is actually in a smash spot.

---

## 4. Stack Conviction: The "Bullpen Death-Spiral"
This is the "Secret Sauce" that identified the Reds stack success today.

### A. Exhaustion Acceleration (v7.6 Tweak)
*   **Metric:** `Bullpen Fatigue` (0-100).
*   **Threshold:** If Fatigue > 80, the stack conviction is boosted by **20%**.
*   **Logic:** OMEGA tracks the usage of every relief pitcher over the last 3 days. If the "High Leverage" arms are gassed, the engine pivots to the opposing stack, regardless of the starting pitcher's talent.

### B. The Paradox Shield
*   **Logic:** If a pitcher is ranked in the Top 5 but their opponent is also a Top 3 stack, the engine triggers a **PARADOX penalty**. This forces you to pick a side, preventing you from playing a pitcher against your own stack.

---

## 5. Environmental Modifiers
The "Invisible 10%" that tilts slates.

1.  **Umpire Bias:** Tracked as a +/- ITT modifier. "Launch Zone" umpires (Tight zones) give a 1.1x multiplier to stacks.
2.  **Park Physics:** Differentiated by handedness. OMEGA knows if a park favors Lefties (Short porches) and adjusts the specific player xwOBA accordingly.
3.  **Thermal Physics:** High-heat/Humidity environments act as a "Physics Accelerator" for exit velocity, boosting the `Burst` signal for hitters.

---

## 6. The "Truth Table" (Output Metrics)
*   **OMEGA Score (0-110):** The final aggregated conviction.
*   **Divergence Score:** The difference between Model Expectation and Market Reality.
*   **Confidence Label:** `High`, `Med`, or `Low` (based on data sample size).

---
**SUMMARY:** OMEGA is not a "projection" engine. It is a **Probability Filter**. It identifies the games where the Physics of the field and the Money of the Sharps align to create an outlier event.
