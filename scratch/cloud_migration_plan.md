# 🚀 OMEGA Engine Cloud Migration & v8.8 Architecture Plan

This document outlines the step-by-step engineering plan to transition the local OMEGA Engine to a live, automated, and password-protected web platform. We will execute this migration over the next 2-3 days.

---

## 🛠️ Step 1: Code Sanitization & Porting (Local Prep)
Before moving files to a live Linux server (VPS), we must eliminate local Windows-specific quirks and hardcoded references.

- [ ] **Path Standardization**:
  - Replace all hardcoded Windows backslashes (`\`) and absolute paths (`C:\Users\...`) in `config.py` and file-handling utilities with dynamic, platform-independent `pathlib.Path` or `os.path` calls.
- [ ] **Environment Secret Isolation**:
  - Move API endpoints, proxy setups, and scraper headers out of the source code and into a secure `.env` file (using `python-dotenv`).
- [ ] **Dependency Freeze**:
  - Audit all active imports and generate a clean, minimal `requirements.txt` to avoid package bloat on the hosted server.

---

## ☁️ Step 2: VPS Server Setup & Automation
We will deploy the core data ingestion engine onto a lightweight Linux server (e.g., DigitalOcean or Linode) for $6/month.

- [ ] **Cron Job Automation**:
  - Set up automated Linux system timers (`cron`) to run the update pipeline automatically at critical slate junctions:
    - **11:00 AM EST**: Morning Slate Ingestion
    - **3:00 PM EST**: Mid-Day Statcast Momentum Sync
    - **6:30 PM EST**: Lock Ingestion (Umpire & Lineup Confirmations)
- [ ] **Force-Refresh Endpoint**:
  - Create a lightweight Python microservice (using **FastAPI**) on the server. If clicked on the website, it will trigger an immediate on-demand run of `run_fetch.py; python main.py` to capture emergency weather or lineup shifts.

---

## 🔒 Step 3: Password-Protected Web Dashboard
We will convert your raw `dashboard.html` output into a premium, hosted web experience.

- [ ] **Authentication Gate**:
  - Design a cinematic, glowing OMEGA themed portal.
  - Require a strong, hashed master password (using secure session tokens or cookies) before granting access.
- [ ] **Asset Bundling**:
  - Optimize the custom UI styles (`index.css`), charts, and images to load instantly on mobile devices and tablet screens.
- [ ] **Live AI Assistant Integration (Pro Feature)**:
  - Embed the floating glowing chat widget directly onto the hosted dashboard.
  - Link it to a lightweight Python backend connected to the Gemini API, pre-loaded with the daily `latest_results.json` data as context.

---

## 🧠 Step 4: The v8.8 Quant Upgrades
During migration, we will build three high-leverage defensive gates to protect against "Chalk Carnage":

### 1. The Opener Disruption Gate (Stack Score Suppressor)
*   **The Tweak**: If opposing starting pitcher projected outs are $\le$ 9.0 (confirmed opener):
    *   Apply a **0.90x Matchup Disruption multiplier** to the stack score.
*   **Goal**: Suppress false stack hype in bullpen games where hitter rhythm is broken by constant pitcher changes.

### 2. The K-Avoidance Dampener (Pitcher Floor Guard)
*   **The Tweak**: If a pitcher's high score relies on K-lines ($\ge$ 6.5) but the opposing lineup's strikeout avoidance rate is elite (`opponent_k_boost` $< -3.0$):
    *   Apply a **0.93x ceiling discount** to the pitcher's final score.
*   **Goal**: Avoid starting high-K pitchers against contact-heavy teams (like Logan Gilbert vs. the Padres today).

### 3. The Thermal HR-Hazard Gate (Flyball Vulnerability)
*   **The Tweak**: If the weather temperature is $\ge$ 82° and the opponent's power concentration is $\ge$ 0.33:
    *   Apply a **0.93x Thermal Hazard** to the starting pitcher's physics score.
*   **Goal**: Warn of elevated home run volatility for elite arms in summer heat (like Jacob deGrom today).

---

*Prepared by Antigravity (Advanced Quant Systems)* 🏁🐋🔋
