# 🧪 OMEGA Parameter Backtest: OLD vs NEW
**Date Range:** 2026-04-15 to 2026-05-27  |  **Slates Analyzed:** 26
**Generated:** 2026-05-27 10:39 PM ET

---

## Parameter Changes Tested

| Parameter | OLD Value | NEW Value | Direction |
|-----------|-----------|-----------|-----------|
| DQI TRUST Threshold | 75 pts | 80 pts | 🔒 Tighter |
| DQI Divergence Gate | 12.0% | 14.0% | 🔒 Tighter |
| DQI ITT Floor | 3.8 runs | 4.2 runs | 🔒 Tighter |
| Divergence Dampening (≥15%, xwOBA<.330) | None | 30% scale-back | 🛡️ Added |
| Bullpen Short-Leash Multiplier | 1.20x | 1.05x | 📉 Reduced |

## Key Metric Comparison

| Metric | OLD Model | NEW Model | Verdict |
|--------|-----------|-----------|---------|
| DQI TRUST Hit Rate (4+ runs) | 0% (0/5) | 0% (0/4) | ➡️ SAME |
| DQI TRUST Volume | 5 tags | 4 tags | 🎯 More Selective |
| Top-3 Stack Hit Rate | 56% (43/77) | 55% (42/77) | ⚠️ DECLINED |
| Divergence Fail Miss Rate | 49% (23/47) | 49% (23/47) | (stack score reduced in NEW) |

## Divergence Dampening Impact (≥15% Div + xwOBA < .330)

These are the specific teams where the new dampening logic would have reduced their stack score premium:

| Date | Team | Div% | xwOBA | Old Score | New Score | Reduction | Actual Runs | Hit? |
|------|------|------|-------|-----------|-----------|-----------|-------------|------|
| 2026-04-15 | Seattle Mariners | +27% | .320 | 94.0 | 91.2 | -2.8 | 6 | ✅ |
| 2026-04-15 | San Diego Padres | +47% | .320 | 93.0 | 90.2 | -2.8 | 7 | ✅ |
| 2026-04-19 | New York Mets | +22% | .320 | 93.3 | 90.5 | -2.8 | 1 | ❌ |
| 2026-04-19 | Tampa Bay Rays | +31% | .320 | 84.2 | 81.7 | -2.5 | 3 | ❌ |
| 2026-04-29 | Pittsburgh Pirates | +17% | .290 | 125.9 | 122.2 | -3.7 | 4 | ✅ |
| 2026-04-29 | Athletics | +27% | .268 | 109.5 | 106.8 | -2.7 | 5 | ✅ |
| 2026-04-29 | Houston Astros | +28% | .322 | 102.5 | 99.4 | -3.1 | 0 | ❌ |
| 2026-04-29 | Colorado Rockies | +39% | .290 | 88.3 | 85.7 | -2.6 | 13 | ✅ |
| 2026-04-29 | San Francisco Giants | +20% | .306 | 85.5 | 82.9 | -2.6 | 0 | ❌ |
| 2026-05-04 | Milwaukee Brewers | +18% | .295 | 130.6 | 126.7 | -3.9 | 3 | ❌ |
| 2026-05-04 | Los Angeles Angels | +21% | .307 | 95.6 | 92.7 | -2.9 | 0 | ❌ |
| 2026-05-05 | Los Angeles Angels | +16% | .308 | 86.7 | 84.1 | -2.6 | 4 | ✅ |
| 2026-05-08 | Kansas City Royals | +15% | .285 | 83.7 | 81.4 | -2.3 | 4 | ✅ |
| 2026-05-09 | Pittsburgh Pirates | +19% | .326 | 68.2 | 66.2 | -2.0 | 13 | ✅ |
| 2026-05-11 | Los Angeles Angels | +15% | .309 | 98.6 | 95.6 | -3.0 | 2 | ❌ |
| 2026-05-11 | Texas Rangers | +16% | .283 | 88.2 | 85.8 | -2.4 | 0 | ❌ |
| 2026-05-12 | Chicago White Sox | +24% | .306 | 114.6 | 111.2 | -3.4 | 6 | ✅ |
| 2026-05-12 | Arizona Diamondbacks | +28% | .284 | 107.5 | 104.5 | -3.0 | 4 | ✅ |
| 2026-05-12 | Detroit Tigers | +20% | .281 | 101.6 | 98.8 | -2.8 | 2 | ❌ |
| 2026-05-12 | St. Louis Cardinals | +32% | .292 | 94.8 | 92.0 | -2.8 | 6 | ✅ |
| 2026-05-13 | Tampa Bay Rays | +24% | .278 | 103.1 | 100.4 | -2.7 | 3 | ❌ |
| 2026-05-13 | Arizona Diamondbacks | +16% | .284 | 98.7 | 96.0 | -2.7 | 5 | ✅ |
| 2026-05-13 | St. Louis Cardinals | +29% | .322 | 96.3 | 93.4 | -2.9 | 2 | ❌ |
| 2026-05-14 | Kansas City Royals | +16% | .282 | 89.9 | 87.4 | -2.5 | 2 | ❌ |
| 2026-05-14 | Chicago Cubs | +15% | .294 | 85.5 | 83.0 | -2.5 | 2 | ❌ |
| 2026-05-14 | Detroit Tigers | +20% | .283 | 80.0 | 77.8 | -2.2 | 4 | ✅ |
| 2026-05-15 | Los Angeles Angels | +29% | .288 | 136.0 | 132.1 | -3.9 | 0 | ❌ |
| 2026-05-15 | San Diego Padres | +37% | .273 | 97.8 | 95.3 | -2.5 | 2 | ❌ |
| 2026-05-15 | Houston Astros | +15% | .316 | 95.2 | 92.3 | -2.9 | 2 | ❌ |
| 2026-05-15 | Cincinnati Reds | +24% | .307 | 87.2 | 84.6 | -2.6 | 7 | ✅ |
| 2026-05-16 | Los Angeles Angels | +25% | .315 | 97.6 | 94.7 | -2.9 | 2 | ❌ |
| 2026-05-17 | New York Mets | +32% | .280 | 130.5 | 127.0 | -3.5 | 7 | ✅ |
| 2026-05-17 | San Diego Padres | +23% | .274 | 84.2 | 82.0 | -2.2 | 8 | ✅ |
| 2026-05-18 | Chicago White Sox | +25% | .307 | 121.6 | 118.0 | -3.6 | 1 | ❌ |
| 2026-05-18 | Cleveland Guardians | +25% | .303 | 110.5 | 107.2 | -3.3 | 8 | ✅ |
| 2026-05-18 | Minnesota Twins | +18% | .300 | 110.4 | 107.1 | -3.3 | 6 | ✅ |
| 2026-05-18 | San Francisco Giants | +19% | .288 | 91.4 | 88.8 | -2.6 | 2 | ❌ |
| 2026-05-19 | Cincinnati Reds | +25% | .303 | 115.9 | 112.4 | -3.5 | 4 | ✅ |
| 2026-05-19 | Colorado Rockies | +53% | .300 | 109.9 | 106.6 | -3.3 | 0 | ❌ |
| 2026-05-19 | Chicago White Sox | +36% | .304 | 109.1 | 105.8 | -3.3 | 2 | ❌ |
| 2026-05-19 | Toronto Blue Jays | +16% | .280 | 107.3 | 104.4 | -2.9 | 4 | ✅ |
| 2026-05-19 | Washington Nationals | +29% | .294 | 93.0 | 90.2 | -2.8 | 9 | ✅ |
| 2026-05-22 | Tampa Bay Rays | +36% | .320 | 79.9 | 77.3 | -2.6 | 4 | ✅ |
| 2026-05-22 | Minnesota Twins | +27% | .326 | 63.9 | 62.0 | -1.9 | 8 | ✅ |
| 2026-05-23 | Minnesota Twins | +32% | .328 | 113.3 | 109.9 | -3.4 | 4 | ✅ |
| 2026-05-27 | Tampa Bay Rays | +16% | .327 | 150.0 | 144.1 | -5.9 | 2 | ❌ |
| 2026-05-27 | Philadelphia Phillies | +17% | .328 | 112.5 | 108.3 | -4.2 | 3 | ❌ |

> **23/47** of these teams failed to score 4+ runs — the dampening reduces their ranking premium, making them less likely to land in your top-3 stacks.

## DQI Trust -> Caution Flips (Tighter Thresholds)

Cases where OLD params said TRUST but NEW params say CAUTION:

| Date | Team | DQI Score | Div% | ITT | Actual Runs | Correct Flip? |
|------|------|-----------|------|-----|-------------|---------------|
| 2026-05-23 | Chicago White Sox | 100 | +13% | 4.6 | 3 | ✅ YES (bad trust avoided) |

> **1/1** flips correctly prevented a bad TRUST call.

## Daily Summary

| Date | OLD Trust | NEW Trust | OLD Top-3 | NEW Top-3 |
|------|-----------|-----------|-----------|-----------|
| 2026-04-15 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-04-19 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-04-29 | 0/0 | 0/0 | 3/3 | 3/3 |
| 2026-05-04 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-05-05 | 0/0 | 0/0 | 1/3 | 0/3 |
| 2026-05-06 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-05-08 | 0/0 | 0/0 | 0/3 | 0/3 |
| 2026-05-09 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-10 | 0/0 | 0/0 | 1/2 | 1/2 |
| 2026-05-11 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-12 | 0/0 | 0/0 | 3/3 | 3/3 |
| 2026-05-13 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-05-14 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-15 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-16 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-17 | 0/0 | 0/0 | 3/3 | 3/3 |
| 2026-05-18 | 0/0 | 0/0 | 3/3 | 3/3 |
| 2026-05-19 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-05-20 | 0/0 | 0/0 | 3/3 | 3/3 |
| 2026-05-21 | 0/0 | 0/0 | 0/3 | 0/3 |
| 2026-05-22 | 0/0 | 0/0 | 2/3 | 2/3 |
| 2026-05-23 | 0/2 | 0/1 | 1/3 | 1/3 |
| 2026-05-24 | 0/0 | 0/0 | 1/3 | 1/3 |
| 2026-05-25 | 0/1 | 0/1 | 2/3 | 2/3 |
| 2026-05-26 | 0/1 | 0/1 | 3/3 | 3/3 |
| 2026-05-27 | 0/1 | 0/1 | 1/3 | 1/3 |

---

## 🏁 Verdict

- ➡️ DQI TRUST accuracy unchanged (0%): Threshold changes have neutral impact.
- [IMPROVED] **TRUST selectivity improved**: Fewer false positives (5 -> 4 tags).
- [WARNING] **Top-3 stack accuracy declined** (56% -> 55%): Re-ordering may be hurting top picks.
- ⚠️ **Divergence dampening mixed results**: Only 23/47 (49%) of dampened teams failed. Consider narrowing the xwOBA threshold.

**Overall: 🔴 NEW parameters show regression. Review and consider reverting.**

---
*Backtest generated by OMEGA Parameter Backtest v1.0*