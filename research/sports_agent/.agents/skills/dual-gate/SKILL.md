---
name: Dual_Gate
description: Documents the cross-threshold validation logic for 'Elite One-Off' selection in MLB DFS.
---

# Dual_Gate Skill

The Dual-Gate skill governs the selection of "Elite One-Off" hitters. It ensures that every one-off target in a Single Entry (SE) build satisfies two independent high-conviction signals.

## 1. Threshold Definitions

### ⚔️ Pitch-Match Alpha (Matchup Gate)
- **Constraint**: Hitter performance vs. the pitcher's specific arsenal.
- **Threshold**: `xwOBA > .380` OR `ISO > .200` against any of the pitcher's Top 3 pitches.
- **Data Source**: Statcast Pitch-Type Splits.

### 🏦 Bookie Shield (Market Gate)
- **Constraint**: Professional betting and market support.
- **Threshold**: Requires at least TWO of the following:
    - **Prop Juice**: `Prop Alpha Multiplier >= 1.05`.
    - **Sharp Team**: `FL Grade B` or higher (Sharp RLM).
    - **Money Flow**: Money % > Ticket % by at least 15%.

## 2. Prioritization Logic

When selecting the 3 one-off slots for a Single Entry build, the optimizer uses a weighted hierarchy:

1. **Dual-Gate (⚔️🏦)**: Hitters meeting BOTH criteria receive a `+3.0` bonus to their `composite` score.
2. **Multi-Signal**: Hitters with any two signals (e.g., 🚀🏦) receive a `+2.0` bonus.
3. **Single Signal**: Hitters with one signal receive a standard `+1.0` bonus.

> [!IMPORTANT]
> **Fallback Strategy**: If a position lacks a Dual-Gate candidate, the engine defaults to the highest raw projection with at least ONE signal to maintain the DFS ceiling.

## 3. Visual Verification
The final production report must display the `⚔️🏦` icons next to all one-off hitters to certify "Mastery & Shield" compliance.
