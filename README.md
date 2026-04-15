# OMEGA v6.1 | Single Entry Edition (MLB DFS Engine)

The **OMEGA Single Entry Edition** is a high-leverage MLB DFS analytics engine optimized for $121+ Single Entry contests. It prioritizes professional market conviction (Storm, Whale, Shark) while suppressing general noise to give you maximum GPP leverage.

## 🚀 Key Features (v6.1)
*   **⚖️ 15/5 Tiered Multiplier**: High-conviction **Alpha signals** (🌪️ Storm, 🐋 Whale, 🦈 Shark, 🎯 Target) receive a **+15% boost**, while secondary **Beta signals** (🎰 Sharp, 🔋 Power, 🏗️ Engine) provide a **+5% context boost**.
*   **📱 Remote Command System**: Full decentralized control via Telegram. Use `/run` to trigger a full marketplace sync and analysis from anywhere.
*   **🔍 Alpha Context Matrix**: A refined dashboard layout that separates primary Alpha leverage from environmental context (Weather, Umpires, Bullpen).
*   **♨️ Consolidated Pen Alert**: One-pill bullpen status monitoring that identifies gassed rotations with color-coded severity.
*   **📡 Hardened Statcast Bridge**: Stealth-mode momentum tracking with randomized footprint and resilient multi-stage fallbacks to prevent site blocking.

## 📁 Project Structure
*   `data/`: Ingestion logic for Markets, Pitchers, Hitters, and Bullpens.
*   `engine/`: `sharps_weighting.py` (v6.1 Tiered Scoring engine).
*   `utils/`: `dashboard_generator.py` (Alpha Context UI) and `telegram_bot.py` (Remote Control).
*   `reports/`: `dashboard.html` & `latest_results.json` (Production Output).

## 🛠️ Remote Commands
1.  `/run`: Triggers the full OMEGA pipeline (Fetch -> Analyze) and sends a Top-3 summary.
2.  `/stacks`: Fetches the current Top High-Alpha Team Stacks.
3.  `/pitchers`: Fetches the current Elite Pitcher Alpha Matrix.

## 🛡️ Persistence
All project state, including the Saturday Retrospective Audit and v6.1 weighting logic, is saved to this workspace and ready for the Sunday Morning Refresh.
