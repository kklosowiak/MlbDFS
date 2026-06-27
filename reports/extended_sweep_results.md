# OMEGA Extended Parameter Optimization Report
**Generated:** 2026-05-25 11:57 PM ET

This report details the Coordinate Descent parameter sweep across all 12 mathematical signals in the MLB DFS engine, covering the entire 2025 season.

## Summary of Core Sweeps

### ⚙️ Signal: `order_decay`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| Default (Steep) | 50.54% | 5.33 |
| Moderate | 50.54% | 5.31 |
| Flat (Equal) 🌟 *(Winner)* | 51.25% | 5.34 |
| Extreme | 50.18% | 5.30 |

### ⚙️ Signal: `park_factor_scale`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (Ignore) | 51.08% | 5.36 |
| 0.25 (Damp 75%) | 50.72% | 5.34 |
| 0.50 (Damp 50%) 🌟 *(Winner)* | 51.61% | 5.37 |
| 0.75 (Damp 25%) | 51.61% | 5.36 |
| 1.00 (Default) | 51.25% | 5.34 |
| 1.25 (Exaggerate) | 51.61% | 5.37 |

### ⚙️ Signal: `bullpen_fatigue_mult`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (Ignore) | 51.43% | 5.31 |
| 0.5 (Damp 50%) | 51.25% | 5.34 |
| 1.0 (Default) 🌟 *(Winner)* | 51.61% | 5.37 |
| 1.5 (Boost 50%) | 51.08% | 5.32 |

### ⚙️ Signal: `bullpen_fatigue_threshold`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 75.0% | 50.54% | 5.34 |
| 80.0% | 50.36% | 5.32 |
| 85.0% (Default) 🌟 *(Winner)* | 51.61% | 5.37 |
| 90.0% | 50.72% | 5.31 |

### ⚙️ Signal: `sp_phys_threshold`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 20.0 (Aggressive) 🌟 *(Winner)* | 51.61% | 5.37 |
| 21.0 | 51.61% | 5.37 |
| 22.0 (Default) | 51.61% | 5.37 |
| 23.0 | 51.61% | 5.37 |
| 24.0 (Conservative) | 51.61% | 5.37 |

### ⚙️ Signal: `sp_penalty_weight`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 12.0 (Soft) | 51.61% | 5.37 |
| 18.0 | 51.43% | 5.36 |
| 24.0 (Default) 🌟 *(Winner)* | 51.61% | 5.37 |
| 30.0 (Hard) | 51.08% | 5.35 |

### ⚙️ Signal: `cold_sp_boost`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (Ignore) | 50.54% | 5.30 |
| 6.0 (Soft) | 51.43% | 5.40 |
| 12.0 (Default) 🌟 *(Winner)* | 51.61% | 5.37 |
| 18.0 (Hard) | 50.72% | 5.31 |

### ⚙️ Signal: `msmi_slump_penalty`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (Ignore) | 50.54% | 5.32 |
| 9.0 (Soft) | 51.08% | 5.34 |
| 18.0 (Default) | 51.61% | 5.37 |
| 24.0 (Hard) 🌟 *(Winner)* | 51.79% | 5.41 |

### ⚙️ Signal: `msmi_surge_boost`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (Ignore) | 51.43% | 5.34 |
| 4.0 (Soft) | 51.43% | 5.38 |
| 8.0 (Default) | 51.79% | 5.41 |
| 12.0 (Hard) 🌟 *(Winner)* | 51.97% | 5.41 |

### ⚙️ Signal: `platoon_same_hand`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.94 (Extreme) | 51.79% | 5.40 |
| 0.96 | 51.79% | 5.39 |
| 0.97 (Default) 🌟 *(Winner)* | 51.97% | 5.41 |
| 0.98 | 51.25% | 5.31 |
| 1.00 (Ignore) | 50.90% | 5.31 |

### ⚙️ Signal: `platoon_opp_hand`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 1.00 (Ignore) | 51.79% | 5.38 |
| 1.02 | 51.61% | 5.39 |
| 1.03 (Default) 🌟 *(Winner)* | 51.97% | 5.41 |
| 1.04 | 51.43% | 5.38 |
| 1.06 (Extreme) | 51.43% | 5.39 |

### ⚙️ Signal: `omega_blend_weight`
| Parameter Setting | 2025 Hit Rate (5+ runs) | Avg Runs Scored |
| :--- | :---: | :---: |
| 0.0 (100% CONF) | 49.28% | 5.14 |
| 0.25 (75/25) | 50.00% | 5.33 |
| 0.50 (50/50 - Default) 🌟 *(Winner)* | 51.97% | 5.41 |
| 0.75 (25/75) | 51.79% | 5.37 |
| 1.00 (100% OMEGA) | 50.72% | 5.30 |

## Global Champion Settings
By compiling the optimal coordinate offsets, we evaluated the ultimate blended model configuration:
- **Final Optimized Hit Rate:** **50.72%** (Baseline: **50.54%**)
- **Final Optimized Avg Runs:** **5.30 runs** (Baseline: **5.33 runs**)

### Champion Parameters:
- `order_decay`: `[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`
- `sp_penalty_dampener_mode`: `tiered_hybrid`
- `bullpen_fatigue_mult`: `1.0`
- `bullpen_fatigue_threshold`: `85.0`
- `park_factor_scale`: `0.5`
- `sp_phys_threshold`: `20.0`
- `sp_penalty_weight`: `24.0`
- `cold_sp_boost`: `12.0`
- `msmi_slump_penalty`: `24.0`
- `msmi_surge_boost`: `12.0`
- `platoon_same_hand`: `0.97`
- `platoon_opp_hand`: `1.03`
- `omega_blend_weight`: `0.5`