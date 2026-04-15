# OMEGA v6.2.2 SE: High-Alpha Intelligence Engine
**Architectural Overview & Technical Foundation**

## 1. The Core Philosophy: Convex Meta-Ensembling
Traditional DFS models rely on "Bottom-Up" projections (Stats -> Expected Points). OMEGA utilizes a "Top-Down" Market Consensus approach, treating the Global Betting Market as a high-accuracy, real-time prediction engine. 

The model resolves the delta between **Physics** (Statcast/Metric-based baselines) and **Market Alpha** (Sharp money movement).

## 2. Feature Engineering & Feature Layers
The engine processes data through three distinct layers before generating a final OMEGA Score:

### Layer 1: The Physics Baseline (Beta)
*   **Pitchers**: Weighted average of **SIERA** (Skill-Interactive ERA) and **CSW%** (Called Strikes + Whiff %). CSW% is treated as the leading indicator of "K-Enthropy."
*   **Hitters**: **Matchup xWOBA** (Expected Weighted On-Base Average) normalized for the opposing pitcher's handedness and high-frequency velocity trends.
*   **Context**: All physics scores are adjusted via a **Weather-Officiating (WO) Mod**, which scales the environment based on wind velocity, humidity, and Umpire strike-zone historical biases.

### Layer 2: Market Intelligence (Alpha Signals)
This is where the model identifies "The Sharp Edge." We track line velocity and magnitude across 15+ sportsbooks:
*   **RLM (Reverse Line Movement)**: Detects when a line moves *away* from the betting percentage (e.g., 80% of bets are on Team A, but Team B’s odds are improving).
*   **Divergence (Δ)**: The spread between Ticket Count % and Money Handle %. A high positive divergence (Δ > +15%) triggers a **Whale Signal**.
*   **Ghost Movement**: Tracking "Laggard" books to identify pre-market moves before they hit the major domestic DFS books.

### Layer 3: Tiered Signal Weighting
Instead of linear regression, OMEGA uses a **Tiered Multiplier System**:
*   **Base Score**: 40.0 + (Physics_Raw * 0.25) + (Market_Raw * 0.35).
*   **Alpha Multiplier (+15%)**: Real-time signals of sharp conviction (SHARK, WHALE, STORM, TARGET).
*   **Beta Multiplier (+5%)**: Supporting indicators (PEN_ALERT, POWER, ENGINE).

## 3. The Math: Dynamic Divergence Scaling
One of the most powerful features of v6.2.2 is the **Divergence Multiplier**. We don't just treat sharp money as a "yes/no" flag. We scale it:
$$Final Score = BaseScore \times (1.0 + \sum Signals) \times (1.0 + \min(0.15, \frac{\max(0, Divergence)}{150.0}))$$

This ensures that the more "Extreme" the sharp money is compared to the public, the more the model weights the play, capped at a 15% raw boost to prevent over-fitting.

## 4. Operational Pipeline (High-Level)
1.  **Snapshotting**: Lines are captured 4 times daily to establish a velocity baseline.
2.  **The Purge**: An "Anti-Ghosting" protocol filters out roster members who are not part of the active 2026 Monday slate mapping.
3.  **Handoff**: Scored data is formatted into the **God-Tier Matrix** for visual decision-making.

---
**Technical Verdict**: OMEGA is designed to exploit the variance between public perception and professional liquidity. It values **Information Velocity** over stagnant seasonal statistics.
