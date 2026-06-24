# 🧪 OMEGA Extended Decision-Layer Historical Audit
**Generated:** 2026-06-23 09:56 PM ET

This report audits three decision-layer systems that have never been systematically backtested historically: **Pitcher Confidence**, **Hitter Confidence**, and **Prop Board Pressure Labels**.

## 1. Pitcher Confidence Audit
Tracks how well starting pitcher confidence scores predict on-field success (Quality Starts and DraftKings points) and blowouts (4+ Earned Runs).

| Tier | Count | Quality Start Rate | Avg DK Points | Blowout Rate (4+ ER) |
| :--- | :--- | :--- | :--- | :--- |
| High Conf (>=80) | 75 | 46.7% | 22.74 | 16.0% |
| Mid Conf (50-79) | 438 | 33.6% | 20.24 | 30.1% |
| Low Conf (<50) | 326 | 31.0% | 18.13 | 25.8% |
| Vegas TRAP Pitchers | 159 | 30.2% | 18.26 | 24.5% |

## 2. Hitter Confidence Audit
Tracks how well individual hitter confidence scores predict a 'Smash' performance (2+ Hits or 1+ Home Run) and average DraftKings points.

| Tier | Count | Smash Rate (2H/1HR) | Avg DK Points |
| :--- | :--- | :--- | :--- |
| High Conf (>=80) | 976 | 29.6% | 4.92 |
| Mid Conf (50-79) | 3034 | 27.3% | 4.43 |
| Low Conf (<50) | 2971 | 25.7% | 4.20 |

## 3. Prop Board Pressure Audit
Tracks how well team-level prop betting pressure labels correlate with team run scoring.

| Prop Label | Count | 4+ Runs Rate | 5+ Runs Rate | Avg Runs Scred |
| :--- | :--- | :--- | :--- | :--- |
| HOT | 0 | N/A | N/A | N/A |
| WARM | 117 | 53.0% | 42.7% | 4.69 |
| NEUTRAL | 675 | 52.3% | 41.9% | 4.29 |
| COLD | 136 | 56.6% | 44.1% | 4.57 |