import os
import json
import time
import datetime
import threading
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="ΩMEGA Engine v9.0")

# Session state
is_refreshing = False
refresh_progress = "Idle"
last_refresh_time = None
last_refresh_timestamp_raw = 0  # epoch time of last refresh run
last_scheduled_hour_key = None  # YYYY-MM-DD HH of last completed refresh
refresh_lock = threading.Lock()

# Timezone engine helper to convert naive datetimes (which are UTC on Render) to Eastern Time (ET)
def get_eastern_time(dt_naive):
    import time
    is_utc = (time.tzname[0] == 'UTC' or time.timezone == 0)
    if is_utc:
        try:
            from zoneinfo import ZoneInfo
            dt_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
            return dt_utc.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            # Fallback to -4 offset (EDT)
            return dt_naive - datetime.timedelta(hours=4)
    else:
        return dt_naive

# Load last refresh time from cached results on startup
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        cached_ts = cached_data.get("timestamp")
        if cached_ts:
            if "T" in cached_ts:
                # Parse ISO timestamp format
                dt = datetime.datetime.fromisoformat(cached_ts)
                dt_et = get_eastern_time(dt)
                last_refresh_time = dt_et.strftime("%Y-%m-%d %I:%M %p ET")
                last_scheduled_hour_key = dt_et.strftime("%Y-%m-%d %H")
            else:
                last_refresh_time = cached_ts
                mtime = os.path.getmtime(results_path)
                dt_mtime = datetime.datetime.fromtimestamp(mtime)
                dt_et = get_eastern_time(dt_mtime)
                last_scheduled_hour_key = dt_et.strftime("%Y-%m-%d %H")
except Exception as init_err:
    print(f"[INIT WARNING]: Failed to load cached timestamp: {init_err}")

# Auth config (no defaults — set OMEGA_PASSWORD in environment)
PASSWORD = os.getenv("OMEGA_PASSWORD") or ""
COOKIE_NAME = "omega_session"
COOKIE_VALUE = "active"

# Thread-safe background runner
def perform_refresh_sync():
    global is_refreshing, refresh_progress, last_refresh_time, last_refresh_timestamp_raw, last_scheduled_hour_key
    with refresh_lock:
        if is_refreshing:
            return
        is_refreshing = True
        refresh_progress = "Initializing data fetch..."
    
    try:
        print("[SERVER BG-THREAD]: Starting ingestion scrape...")
        from run_fetch import perform_fetch
        snapshot_path = perform_fetch()
        if not snapshot_path:
            raise RuntimeError(
                "Market ingestion failed (no snapshot). Check ODDS_API_KEY quota and Render logs."
            )

        with refresh_lock:
            refresh_progress = "Running OMEGA engine analysis..."

        print("[SERVER BG-THREAD]: Starting model calculations...")
        from main import run_full_analysis
        run_full_analysis()

        results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "latest_results.json")
        if not os.path.exists(results_path):
            raise RuntimeError("Analysis finished but latest_results.json was not written.")
        with open(results_path, "r", encoding="utf-8") as f:
            res_check = json.load(f)
        n_p = len(res_check.get("pitchers") or [])
        n_t = len(res_check.get("teams") or [])
        n_h = len(res_check.get("hitters") or [])
        print(f"[SERVER BG-THREAD]: Results written — {n_p} pitchers, {n_t} teams, {n_h} hitters.")
        if n_p == 0 and n_t == 0:
            raise RuntimeError(
                "Analysis produced empty pitchers/teams — check ODDS_API_KEY, snapshot, and opening lines in logs."
            )
        if n_h == 0:
            print("[SERVER BG-THREAD WARNING]: Hitters list empty — check statcast cache and prop ingest.")

        try:
            from utils.dqi import persist_dqi_history
            from config import config
            results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
            if os.path.exists(results_path):
                with open(results_path, "r", encoding="utf-8") as f:
                    res = json.load(f)
                persist_dqi_history(
                    res.get("teams", []),
                    config.REPORTS_DIR,
                    pitchers=res.get("pitchers", []),
                )
        except Exception as dqi_e:
            print(f"[SERVER BG-THREAD WARNING]: DQI history persist failed: {dqi_e}")
        
        print("[SERVER BG-THREAD]: Running automated trend resolution for past games...")
        try:
            auto_resolve_trends()
        except Exception as trend_e:
            print(f"[SERVER BG-THREAD WARNING]: Trend auto-resolution failed: {trend_e}")
            
        with refresh_lock:
            et_now = get_eastern_time(datetime.datetime.now())
            last_refresh_time = et_now.strftime("%Y-%m-%d %I:%M %p ET")
            last_refresh_timestamp_raw = time.time()
            last_scheduled_hour_key = et_now.strftime("%Y-%m-%d %H")
            refresh_progress = "Idle"
            is_refreshing = False
        print("[SERVER BG-THREAD]: Refresh completed successfully!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        with refresh_lock:
            try:
                et_now = get_eastern_time(datetime.datetime.now())
                last_scheduled_hour_key = et_now.strftime("%Y-%m-%d %H")
            except Exception:
                pass
            refresh_progress = f"Error: {str(e)}"
            is_refreshing = False

# Background scheduler thread
def scheduler_loop():
    global is_refreshing, last_refresh_timestamp_raw, last_scheduled_hour_key
    print("[SERVER]: Auto-Refresh Hourly Scheduler thread started (Active: 8AM ET, last trigger by 5:59PM ET).")
    
    while True:
        # Check current US/Eastern Time dynamically (DST compliant)
        try:
            from zoneinfo import ZoneInfo
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            # Fallback to -4 offset (EDT)
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now - datetime.timedelta(hours=4)
            
        et_hour = et_now.hour
        current_hour_key = et_now.strftime("%Y-%m-%d %H")
        
        # Active window: 8:00 AM ET through 5:59 PM ET (hour <= 17).
        # Last trigger fires at 5:xx PM so even a slow refresh (45-60 min)
        # completes before 7:00 PM ET with no bleed-over visible to the user.
        # Hard cutoff: hour 18+ (6 PM+) — scheduler goes completely silent.
        is_active_window = (8 <= et_hour <= 17)
        
        if is_active_window:
            if current_hour_key != last_scheduled_hour_key:
                print(f"[SERVER]: Scheduled Auto-Refresh triggered for hour: {et_now.strftime('%I:%M %p ET')}.")
                perform_refresh_sync()
            
        # Sleep for 10 seconds before checking time again
        time.sleep(10)


# Start hourly scheduler in daemon thread
scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
scheduler_thread.start()

# --- v9.5: 4:30 AM ET Opening Lines Capture ---
# This dedicated background thread fires exactly once per night at 4:30 AM
# Eastern Time to lock in the true opening lines for the day's slate.
# Firing after 4:00 AM ET ensures that the timezone-aware rollover window
# matches today's slate date, preventing yesterday's lines from clobbering.
# Runs 24/7 — safe for Render $25/mo always-on tier.
opening_lines_last_date_triggered = None
opening_lines_lock = threading.Lock()

def opening_lines_capture_loop():
    """Background thread: fires perform_refresh_sync() once per night at 4:30 AM ET."""
    global opening_lines_last_date_triggered
    print("[SERVER]: 4:30 AM ET Opening Lines Capture thread started.")
    
    while True:
        try:
            from zoneinfo import ZoneInfo
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now - datetime.timedelta(hours=4)
        
        et_hour = et_now.hour
        et_minute = et_now.minute
        today_date_str = et_now.strftime("%Y-%m-%d")
        
        # Target window: exactly 4:30 AM ET (within the 4:30–4:31 minute window)
        is_capture_window = (et_hour == 4 and et_minute == 30)
        
        with opening_lines_lock:
            already_triggered_today = (opening_lines_last_date_triggered == today_date_str)
        
        if is_capture_window and not already_triggered_today:
            print(f"[4:30AM-CAPTURE]: Opening lines capture triggered at {et_now.strftime('%Y-%m-%d %I:%M %p ET')}.")
            with opening_lines_lock:
                opening_lines_last_date_triggered = today_date_str
            # Run in same thread (blocking) — this is a low-frequency, 1x/night event
            # We do NOT use perform_refresh_sync here to avoid clobbering the hourly lock.
            # Instead, do a lightweight fetch + analysis run.
            try:
                print("[4:30AM-CAPTURE]: Starting overnight opening lines ingestion scrape...")
                from run_fetch import perform_fetch
                perform_fetch(capture_opening=True)
                print("[4:30AM-CAPTURE]: Starting OMEGA opening lines analysis...")
                from main import run_full_analysis
                run_full_analysis()
                print("[4:30AM-CAPTURE]: ✅ Opening lines capture completed successfully!")
            except Exception as cap_err:
                import traceback
                print(f"[4:30AM-CAPTURE ERROR]: {cap_err}")
                traceback.print_exc()
        
        # Sleep 45 seconds between checks to catch the 1:00 minute window reliably
        time.sleep(45)

opening_lines_thread = threading.Thread(target=opening_lines_capture_loop, daemon=True)
opening_lines_thread.start()

# --- v9.5: 7:00 AM ET Auto-Audit Feedback Loop ---
# Automatically runs the performance audit feedback loop daily at 7:00 AM ET.
# Updates the dashboard with the previous day's final boxscores and grades automatically.
auto_audit_last_date_triggered = None
auto_audit_lock = threading.Lock()

def auto_audit_capture_loop():
    """Background thread: fires the backtest audit feedback loop once per night at 7:00 AM ET."""
    global auto_audit_last_date_triggered
    print("[SERVER]: 7:00 AM ET Auto-Audit Feedback Loop thread started.")
    
    while True:
        try:
            from zoneinfo import ZoneInfo
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            et_now = utc_now - datetime.timedelta(hours=4)
        
        et_hour = et_now.hour
        et_minute = et_now.minute
        today_date_str = et_now.strftime("%Y-%m-%d")
        
        # Target window: exactly 7:00 AM ET (within the 7:00–7:01 minute window)
        is_capture_window = (et_hour == 7 and et_minute == 0)
        
        with auto_audit_lock:
            already_triggered_today = (auto_audit_last_date_triggered == today_date_str)
        
        if is_capture_window and not already_triggered_today:
            print(f"[7AM-AUDIT]: Auto-audit feedback loop triggered at {et_now.strftime('%Y-%m-%d %I:%M %p ET')}.")
            with auto_audit_lock:
                auto_audit_last_date_triggered = today_date_str
            try:
                from run_feedback_loop import run_feedback_loop
                run_feedback_loop(7)
                print("[7AM-AUDIT]: ✅ Auto-audit feedback loop completed successfully!")
            except Exception as aud_err:
                import traceback
                print(f"[7AM-AUDIT ERROR]: {aud_err}")
                traceback.print_exc()
        
        # Sleep 45 seconds between checks to catch the 7:00 minute window reliably
        time.sleep(45)

auto_audit_thread = threading.Thread(target=auto_audit_capture_loop, daemon=True)
auto_audit_thread.start()


# Auth validation dependency
def get_current_user(request: Request):
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie != COOKIE_VALUE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return COOKIE_VALUE

# Auth checker redirecting to login instead of throwing 401 (for pages)
def check_page_auth(request: Request):
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie != COOKIE_VALUE:
        return False
    return True

# ----------------- ROUTES -----------------

@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    if check_page_auth(request):
        return RedirectResponse(url="/")
        
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ΩMEGA ENGINE - SECURE PORTAL</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #030303;
                --surface: rgba(20, 20, 25, 0.7);
                --text: #f5f5f7;
                --accent: #0a84ff;
                --accent-green: #32d74b;
                --accent-red: #ff453a;
                --border: rgba(255, 255, 255, 0.08);
                --radius: 20px;
            }
            body {
                margin: 0;
                padding: 0;
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Outfit', -apple-system, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                overflow: hidden;
                background-image: radial-gradient(circle at 50% 50%, #0d1b2a 0%, #030303 80%);
            }
            .login-card {
                background: var(--surface);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 50px 40px;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 100px rgba(10, 132, 255, 0.05);
                text-align: center;
                animation: floatIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            }
            @keyframes floatIn {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .logo {
                font-size: 3rem;
                font-weight: 800;
                color: var(--accent);
                text-shadow: 0 0 20px rgba(10, 132, 255, 0.5);
                margin-bottom: 10px;
            }
            h2 {
                margin: 0 0 8px 0;
                font-weight: 800;
                font-size: 1.5rem;
                letter-spacing: -0.02em;
            }
            p {
                margin: 0 0 35px 0;
                color: rgba(255, 255, 255, 0.5);
                font-size: 0.95rem;
                font-weight: 400;
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            input[type="password"] {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 16px;
                font-size: 1rem;
                color: #fff;
                font-family: inherit;
                text-align: center;
                transition: all 0.3s ease;
                outline: none;
            }
            input[type="password"]:focus {
                border-color: var(--accent);
                background: rgba(255, 255, 255, 0.08);
                box-shadow: 0 0 15px rgba(10, 132, 255, 0.2);
            }
            button {
                background: var(--accent);
                color: #fff;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                box-shadow: 0 4px 15px rgba(10, 132, 255, 0.4);
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(10, 132, 255, 0.6);
            }
            button:active {
                transform: translateY(0);
            }
            .error-msg {
                color: var(--accent-red);
                font-size: 0.9rem;
                margin-top: 15px;
                font-weight: 600;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="logo">Ω</div>
            <h2>ΩMEGA ENGINE</h2>
            <p>v9.0 Secure Analytical Gateway</p>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="ENTER ACCESS CODE" required autofocus>
                <button type="submit">DECRYPT & ENTER</button>
            </form>
            <div class="error-msg" id="error-box">DECRYPTION FAILED. ACCESS DENIED.</div>
        </div>
        <script>
            // Parse query string for errors
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('error')) {
                document.getElementById('error-box').style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")

@app.post("/login")
def post_login_page(password: str = Form(...)):
    if PASSWORD and password == PASSWORD:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        # Set persistent session cookie (lasts 30 days)
        response.set_cookie(
            key=COOKIE_NAME,
            value=COOKIE_VALUE,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response
    else:
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def get_logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/lineups", response_class=HTMLResponse)
def get_lineups_page(request: Request):
    if not check_page_auth(request):
        return RedirectResponse(url="/login")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tmpl_path = os.path.join(base_dir, "templates", "lineups.html")
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="Error: lineups.html not found.")

@app.get("/api/lineups")
def api_get_confirmed_lineups(request: Request):
    if not check_page_auth(request):
        raise HTTPException(status_code=401)
    
    from data.lineup_fetcher import LineupFetcher
    fetcher = LineupFetcher()
    confirmed = fetcher.fetch_confirmed_lineups()
    projected = fetcher.fetch_projected_lineups()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    
    projections = {}
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                projections = json.load(f)
        except Exception as e:
            print(f"Error loading projections for lineups: {e}")
            
    return {
        "confirmed_lineups": confirmed,
        "projected_lineups": projected,
        "projections": projections
    }


# Main page wrapper serving index.html
@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request):
    if not check_page_auth(request):
        return RedirectResponse(url="/login")
        
    # Read custom templates/index.html (we will create this in templates/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tmpl_path = os.path.join(base_dir, "templates", "index.html")
    
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return HTMLResponse(
                content=f.read(),
                media_type="text/html; charset=utf-8",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
    else:
        return HTMLResponse(content="ERROR: templates/index.html not found. Place template in templates/ folder.", media_type="text/html; charset=utf-8")

# API Endpoints
@app.get("/api/results", dependencies=[Depends(get_current_user)])
def get_results_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        from utils.dqi import calculate_dqi, load_dqi_history

        teams = data.get("teams", [])
        pitchers = data.get("pitchers", [])
        dqi_history = load_dqi_history(os.path.join(base_dir, "reports"))

        import datetime as _dt
        now_et = _dt.datetime.now()

        from utils.team_signals import apply_team_blind_spot, apply_team_burst

        for t in teams:
            team_key = t.get("team", "")
            apply_team_blind_spot(t)
            apply_team_burst(t, opp_pitcher_outs=t.get("opp_pitcher_outs", 18.0))

            try:
                dqi_score, dqi_status, dqi_pos_factors, dqi_warn_factors = calculate_dqi(
                    t, pitchers=pitchers
                )
                if dqi_score is not None:
                    t["dqi_score"] = dqi_score
                    t["dqi_status"] = dqi_status
                    t["dqi_pos_factors"] = dqi_pos_factors
                    t["dqi_warn_factors"] = dqi_warn_factors
                else:
                    hist = dqi_history.get(team_key)
                    if hist:
                        try:
                            recorded = _dt.datetime.fromisoformat(hist["recorded_at"])
                            hours_ago = (now_et - recorded).total_seconds() / 3600
                            if hours_ago <= 4:
                                t["dqi_faded"] = True
                                t["dqi_faded_score"] = hist["score"]
                                t["dqi_faded_status"] = hist["status"]
                        except Exception:
                            pass
            except Exception as dqi_err:
                print(f"[API WARNING]: DQI skipped for {team_key}: {dqi_err}")

            ump_factor = t.get("umpire_factor", 1.0)
            if ump_factor >= 1.03:
                t["umpire_label"] = "Hitter-Friendly"
            elif ump_factor <= 0.97:
                t["umpire_label"] = "Pitcher-Friendly"
            else:
                t["umpire_label"] = "Neutral"

        data["teams"] = teams

        try:
            from utils.slate_signal_history import attach_signal_deltas

            attach_signal_deltas(os.path.join(base_dir, "reports"), teams, pitchers)
        except Exception as sig_err:
            print(f"[API WARNING]: Signal delta attach skipped: {sig_err}")

        return JSONResponse(
            content=data,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        return JSONResponse(
            content={
                "pitchers": [],
                "teams": [],
                "hitters": [],
                "timestamp": None,
                "message": "No results available yet. Run a slate refresh.",
            },
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

@app.get("/api/analysis", dependencies=[Depends(get_current_user)])
def get_analysis_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_path = os.path.join(base_dir, "reports", "slate_analysis.md")
    
    if os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8") as f:
            return {"markdown": f.read()}
    else:
        return {"markdown": "No analysis available yet."}

@app.get("/api/data-health", dependencies=[Depends(get_current_user)])
def get_data_health_api():
    """Safe operational health for the live dashboard (no secrets)."""
    from config import config
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = config.DATA_DIR
    reports_dir = config.REPORTS_DIR

    latest_snap = None
    snapshot_age_minutes = None
    splits_status = "unknown"
    splits_teams_count = 0

    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.startswith("snapshot_") and f.endswith(".json"):
                if not latest_snap or f > latest_snap:
                    latest_snap = f
    if latest_snap:
        snap_path = os.path.join(data_dir, latest_snap)
        if os.path.exists(snap_path):
            snapshot_age_minutes = int((time.time() - os.path.getmtime(snap_path)) / 60)
            try:
                with open(snap_path, "r", encoding="utf-8") as f:
                    snap = json.load(f)
                splits = snap.get("splits", {})
                if isinstance(splits, dict):
                    notes = str(splits.get("notes", ""))
                    if notes and "pending" in notes.lower():
                        splits_status = "placeholder"
                    elif len(splits) > 0:
                        splits_status = "ok"
                        splits_teams_count = len([k for k in splits if k != "notes"])
                    else:
                        splits_status = "empty"
            except Exception:
                splits_status = "error"

    results_timestamp = None
    lineups_confirmed_pct = None
    teams_total = 0
    teams_confirmed = 0
    results_path = os.path.join(reports_dir, "latest_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                res = json.load(f)
            results_timestamp = res.get("timestamp")
            for t in res.get("teams", []):
                teams_total += 1
                if t.get("lineup_status") == "CONFIRMED":
                    teams_confirmed += 1
            if teams_total > 0:
                lineups_confirmed_pct = round((teams_confirmed / teams_total) * 100)
        except Exception:
            pass

    # Read data_health.json for any scraping warnings/errors
    health_status = "ok"
    health_warnings = []
    try:
        health_path = os.path.join(data_dir, "data_health.json")
        if os.path.exists(health_path):
            with open(health_path, "r", encoding="utf-8") as f:
                health_data = json.load(f)
            health_status = health_data.get("status", "ok")
            health_warnings = health_data.get("warnings", [])
    except Exception:
        pass

    return JSONResponse(
        content={
            "latest_snapshot": latest_snap,
            "snapshot_age_minutes": snapshot_age_minutes,
            "splits_status": splits_status,
            "splits_teams_count": splits_teams_count,
            "results_timestamp": results_timestamp,
            "lineups_confirmed_pct": lineups_confirmed_pct,
            "teams_confirmed": teams_confirmed,
            "teams_total": teams_total,
            "odds_api_configured": bool(config.ODDS_API_KEY),
            "health_status": health_status,
            "health_warnings": health_warnings,
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )



@app.get("/api/refresh-status", dependencies=[Depends(get_current_user)])
def get_refresh_status_api():
    global is_refreshing, refresh_progress, last_refresh_time
    with refresh_lock:
        return {
            "is_refreshing": is_refreshing,
            "progress": refresh_progress,
            "last_refresh_time": last_refresh_time or "Never"
        }

@app.get("/api/debug-env", dependencies=[Depends(get_current_user)])
def get_debug_env_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    reports_dir = os.path.join(base_dir, "reports")

    latest_snap = None
    snapshot_age_minutes = None
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.startswith("snapshot_") and f.endswith(".json"):
                if not latest_snap or f > latest_snap:
                    latest_snap = f
    if latest_snap:
        snap_path = os.path.join(data_dir, latest_snap)
        if os.path.exists(snap_path):
            snapshot_age_minutes = int((time.time() - os.path.getmtime(snap_path)) / 60)

    results_timestamp = None
    results_path = os.path.join(reports_dir, "latest_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                results_timestamp = json.load(f).get("timestamp")
        except Exception:
            pass

    splits_teams_count = 0
    splits_placeholder = False
    if latest_snap:
        try:
            with open(os.path.join(data_dir, latest_snap), "r", encoding="utf-8") as f:
                snap = json.load(f)
            splits = snap.get("splits", {})
            if isinstance(splits, dict):
                notes = splits.get("notes", "")
                if notes and "pending" in str(notes).lower():
                    splits_placeholder = True
                else:
                    splits_teams_count = len([k for k in splits.keys() if k != "notes"])
        except Exception:
            pass

    from run_fetch import get_slate_date
    try:
        slate_date = str(get_slate_date())
    except Exception as e:
        slate_date = f"Error: {e}"

    return {
        "odds_api_configured": bool(os.getenv("ODDS_API_KEY")),
        "base_date_slate": slate_date,
        "latest_snapshot": latest_snap,
        "snapshot_age_minutes": snapshot_age_minutes,
        "results_timestamp": results_timestamp,
        "splits_teams_count": splits_teams_count,
        "splits_placeholder": splits_placeholder,
    }

@app.post("/api/refresh", dependencies=[Depends(get_current_user)])
def post_refresh_api(background_tasks: BackgroundTasks):
    global is_refreshing
    with refresh_lock:
        if is_refreshing:
            return {"status": "already_refreshing", "message": "A slate analysis is currently in progress."}
            
    # Trigger refresh in background task so API returns instantly
    background_tasks.add_task(perform_refresh_sync)
    return {"status": "started", "message": "Slate analysis triggered in background."}

def auto_resolve_trends():
    import csv
    import tempfile
    import shutil
    import datetime
    from config import config
    from utils.audit_engine import AuditEngine
    
    log_path = os.path.join(config.LOG_DIR, "trend_tag_log.csv")
    if not os.path.exists(log_path):
        return {"status": "error", "message": "Trend log file not found"}
        
    # 1. Read unresolved entries in the past
    unresolved_dates = set()
    rows = []
    
    try:
        with open(log_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
                actual_runs = row.get("actual_runs", "").strip()
                hit = row.get("hit", "").strip()
                if actual_runs == "" or hit == "":
                    row_date = row.get("date", "").strip()
                    if row_date:
                        today_str = datetime.date.today().strftime("%Y-%m-%d")
                        if row_date != today_str:
                            unresolved_dates.add(row_date)
                            
        if not unresolved_dates:
            return {"status": "success", "message": "All past trend tags are already resolved!", "resolved_count": 0}
            
        # 2. Fetch results for each past date
        audit = AuditEngine()
        results_by_date = {}
        for date_str in unresolved_dates:
            print(f"[AUTO-RESOLVE]: Fetching MLB results for {date_str}...")
            day_results = audit.fetch_results(date=date_str)
            if day_results:
                results_by_date[date_str] = day_results
                
        # 3. Resolve the rows
        resolved_count = 0
        updated_rows = []
        for row in rows:
            actual_runs_val = row.get("actual_runs", "").strip()
            hit_val = row.get("hit", "").strip()
            
            if actual_runs_val == "" or hit_val == "":
                row_date = row.get("date", "").strip()
                row_team = row.get("team", "").strip()
                
                if row_date in results_by_date:
                    day_results = results_by_date[row_date]
                    team_match = None
                    if row_team in day_results:
                        team_match = row_team
                    else:
                        for full_team_name in day_results.keys():
                            if row_team.lower() in full_team_name.lower() or full_team_name.lower() in row_team.lower():
                                team_match = full_team_name
                                break
                                
                    if team_match:
                        team_data = day_results[team_match]
                        status = team_data.get("status", "Unknown")
                        if "Final" in status or status == "Completed Early":
                            runs = team_data.get("runs", 0)
                            implied_total = float(row.get("implied_total", 4.5) or 4.5)
                            tag = row.get("tag", "SURGING")
                            
                            row["actual_runs"] = str(runs)
                            if tag == "SURGING":
                                hit = 1 if runs >= implied_total else 0
                            else: # FADING
                                hit = 1 if runs < implied_total else 0
                                
                            row["hit"] = str(hit)
                            resolved_count += 1
                            print(f"[AUTO-RESOLVE]: Resolved {row_date} {row_team} -> {runs} runs ({'HIT' if hit else 'MISS'})")
                            
            updated_rows.append(row)
            
        # 4. Save CSV back atomically
        if resolved_count > 0:
            temp_fd, temp_path = tempfile.mkstemp()
            try:
                with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as temp_file:
                    writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in updated_rows:
                        writer.writerow(row)
                shutil.move(temp_path, log_path)
            except Exception as save_err:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise save_err
                
        return {
            "status": "success",
            "message": f"Successfully auto-resolved {resolved_count} trend tag(s)!",
            "resolved_count": resolved_count
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Auto-resolve error: {str(e)}"}

@app.post("/api/trends/auto-resolve", dependencies=[Depends(get_current_user)])
def post_trends_auto_resolve_api():
    res = auto_resolve_trends()
    return JSONResponse(content=res)

@app.get("/api/trends", dependencies=[Depends(get_current_user)])
def get_trends_api():
    import csv
    from config import config
    log_path = os.path.join(config.LOG_DIR, "trend_tag_log.csv")
    
    if not os.path.exists(log_path):
        return JSONResponse(content={"trends": []})
        
    try:
        trends = []
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trends.append(row)
        # Reverse to show newest first
        trends.reverse()
        return JSONResponse(content={"trends": trends})
    except Exception as e:
        return JSONResponse(content={"error": f"Failed to read trends: {str(e)}"}, status_code=500)

@app.post("/api/trends/resolve", dependencies=[Depends(get_current_user)])
def post_trends_resolve_api(body: dict):
    import csv
    import tempfile
    from config import config
    
    target_date = body.get("date", "")
    target_team = body.get("team", "")
    actual_runs_str = body.get("actual_runs", "")
    
    if not target_date or not target_team or actual_runs_str == "":
        raise HTTPException(status_code=400, detail="Missing required parameters: date, team, actual_runs")
        
    try:
        actual_runs = float(actual_runs_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="actual_runs must be a valid number")
        
    log_path = os.path.join(config.LOG_DIR, "trend_tag_log.csv")
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Trend log file not found")
        
    updated = False
    temp_fd, temp_path = tempfile.mkstemp()
    try:
        with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as temp_file:
            with open(log_path, 'r', newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                fieldnames = reader.fieldnames
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    if row.get("date") == target_date and row.get("team") == target_team:
                        row["actual_runs"] = str(actual_runs)
                        
                        # Calculate hit/miss
                        implied_total = float(row.get("implied_total", 4.5) or 4.5)
                        tag = row.get("tag", "SURGING")
                        
                        if tag == "SURGING":
                            hit = 1 if actual_runs >= implied_total else 0
                        else:  # FADING
                            hit = 1 if actual_runs < implied_total else 0
                            
                        row["hit"] = str(hit)
                        updated = True
                        
                    writer.writerow(row)
                    
        if updated:
            import shutil
            shutil.move(temp_path, log_path)
        else:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=404, detail="Matching trend log entry not found")
            
        # Return updated list
        trends = []
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trends.append(row)
        trends.reverse()
        return JSONResponse(content={"status": "success", "trends": trends})
        
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database writeback failure: {str(e)}")

@app.get("/api/platoons", dependencies=[Depends(get_current_user)])
def get_platoons_api():
    """Platoon Matrix: Cross-reference team/pitcher splits with today's matchups."""
    from utils.normalization import normalize_player_name
    from utils.xwoba_estimates import woba_proxy_to_xwoba, platoon_advantage_label
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load data sources
    platoon_path = os.path.join(base_dir, "data", "platoon_cache.json")
    probables_path = os.path.join(base_dir, "data", "probable_pitchers.json")
    statcast_path = os.path.join(base_dir, "data", "statcast_cache.json")
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    
    platoon_data = {}
    probables = {}
    statcast = {}
    results_data = {}
    
    try:
        if os.path.exists(platoon_path):
            with open(platoon_path, "r", encoding="utf-8") as f:
                platoon_data = json.load(f)
        if os.path.exists(probables_path):
            with open(probables_path, "r", encoding="utf-8") as f:
                probables = json.load(f)
        if os.path.exists(statcast_path):
            with open(statcast_path, "r", encoding="utf-8") as f:
                statcast = json.load(f)
        if os.path.exists(results_path):
            with open(results_path, "r", encoding="utf-8") as f:
                results_data = json.load(f)
    except Exception as e:
        return JSONResponse(content={"error": f"Failed to load data: {str(e)}", "matchups": []}, status_code=500)
    
    teams_splits = platoon_data.get("teams", {}) or {}
    pitchers_splits = platoon_data.get("pitchers", {}) or {}
    teams_results = results_data.get("teams", []) or []
    
    # Build a lookup: team_name -> team result row
    results_lookup = {}
    for t in teams_results:
        if isinstance(t, dict) and t.get("team"):
            results_lookup[t["team"]] = t
    
    from data.lineup_fetcher import LineupFetcher
    fetcher = LineupFetcher()
    try:
        confirmed_lineups = fetcher.fetch_confirmed_lineups() or {}
        projected_lineups = fetcher.fetch_projected_lineups() or {}
    except Exception:
        confirmed_lineups = {}
        projected_lineups = {}
    
    if not isinstance(confirmed_lineups, dict):
        confirmed_lineups = {}
    if not isinstance(projected_lineups, dict):
        projected_lineups = {}
        
    matchups = []
    seen_games = set()
    
    for team_result in teams_results:
        if not isinstance(team_result, dict):
            continue
        try:
            team_vs_hand_woba = None
            team_name = team_result.get("team", "")
            opponent = team_result.get("opponent", "")
            opp_pitcher_name = team_result.get("opp_pitcher", "TBD")
            stack_score = team_result.get("stack_score", 0)
            implied_total = team_result.get("implied_total", 0)
            
            if not team_name or not opponent or opp_pitcher_name == "TBD":
                continue
            
            # Avoid duplicate games (we want each team row independently)
            game_key = tuple(sorted([team_name, opponent]))
            
            # Resolve pitcher handedness from statcast cache
            norm_pitcher = normalize_player_name(opp_pitcher_name)
            pitcher_profile = statcast.get(norm_pitcher, {}) or {}
            pitcher_hand = pitcher_profile.get("pitch_hand", "R") if isinstance(pitcher_profile, dict) else "R"
            pitcher_hand_label = "LHP" if pitcher_hand == "L" else "RHP"
            
            short_map = {
                'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
                'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
                'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
                'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
                'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
                'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
                'New York Yankees': 'NYY', 'Athletics': 'OAK', 'Oakland Athletics': 'OAK',
                'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
                'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL',
                'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR',
                'Washington Nationals': 'WSH'
            }
            def get_abbrev(name):
                return short_map.get(name, name)
    
            confirmed = confirmed_lineups.get(team_name) or confirmed_lineups.get(get_abbrev(team_name))
            is_confirmed = (confirmed is not None and len(confirmed) >= 7)
    
            projected = None
            if not is_confirmed:
                projected = projected_lineups.get(team_name) or projected_lineups.get(get_abbrev(team_name))
    
            team_hitters = [h for h in results_data.get("hitters", []) if isinstance(h, dict) and h.get("team") == team_name]
    
            if is_confirmed:
                confirmed_order = {normalize_player_name(p): idx for idx, p in enumerate(confirmed)}
                active_lineup = [h for h in team_hitters if isinstance(h, dict) and normalize_player_name(h.get('name', '')) in confirmed_order]
                active_lineup = sorted(active_lineup, key=lambda x: confirmed_order[normalize_player_name(x.get('name', ''))])[:9]
                if not active_lineup:
                    team_hitters.sort(key=lambda x: float(x.get("player_score", 0.0) or 0.0) if isinstance(x, dict) else 0.0, reverse=True)
                    active_lineup = team_hitters[:9]
            else:
                if projected:
                    projected_order = {normalize_player_name(p): idx for idx, p in enumerate(projected)}
                    active_lineup = [h for h in team_hitters if isinstance(h, dict) and normalize_player_name(h.get('name', '')) in projected_order]
                    active_lineup = sorted(active_lineup, key=lambda x: projected_order[normalize_player_name(x.get('name', ''))])[:9]
                
                if not projected or not active_lineup:
                    # Filter active roster hitters who have played recently (rolling_pa > 0)
                    active_h = []
                    for h in team_hitters:
                        if not isinstance(h, dict): continue
                        h_prof = statcast.get(normalize_player_name(h.get("name", "")), {}) or {}
                        h_rpa = h_prof.get("rolling_pa", 0) if isinstance(h_prof, dict) else 0
                        if int(h_rpa or 0) > 0:
                            active_h.append(h)
                    if len(active_h) < 9:
                        active_h = team_hitters
                    
                    # Sort active hitters by season PA descending to get everyday starters
                    def get_season_pa(h):
                        if not isinstance(h, dict): return 0
                        h_prof = statcast.get(normalize_player_name(h.get("name", "")), {}) or {}
                        return int(h_prof.get("pa", 0) if isinstance(h_prof, dict) else 0) or 0
                    
                    active_h.sort(key=get_season_pa, reverse=True)
                    active_lineup = active_h[:9]
    
            if active_lineup:
                team_vs_hand_xwoba = sum(float(h.get("matchup_xwoba", 0.320) or 0.320) for h in active_lineup if isinstance(h, dict)) / len(active_lineup)
                xwoba_diff_val = sum(float(h.get("NPAS_xwOBA", 0.0) or 0.0) for h in active_lineup if isinstance(h, dict)) / len(active_lineup)
                team_other_xwoba = team_vs_hand_xwoba - xwoba_diff_val
                
                # Map xwOBA back to OPS: ops = (xwoba - 0.180) / 0.230
                team_vs_hand_ops = max(0.400, (team_vs_hand_xwoba - 0.180) / 0.230)
                team_other_ops = max(0.400, (team_other_xwoba - 0.180) / 0.230)
                
                ops_diff = round((team_vs_hand_ops - team_other_ops) * 1000)
                xwoba_diff = round(xwoba_diff_val * 1000)
                
                def get_h_avg(h):
                    if not isinstance(h, dict): return 0.250
                    h_prof = statcast.get(normalize_player_name(h.get("name", "")), {}) or {}
                    return float(h_prof.get("avg", 0.250) if isinstance(h_prof, dict) else 0.250) or 0.250
                def get_h_slg(h):
                    if not isinstance(h, dict): return 0.400
                    h_prof = statcast.get(normalize_player_name(h.get("name", "")), {}) or {}
                    return float(h_prof.get("slg", 0.400) if isinstance(h_prof, dict) else 0.400) or 0.400
                def get_h_pa(h):
                    if not isinstance(h, dict): return 400
                    h_prof = statcast.get(normalize_player_name(h.get("name", "")), {}) or {}
                    return int(h_prof.get("pa", 400) if isinstance(h_prof, dict) else 400) or 400
                    
                team_vs_hand_avg = sum(get_h_avg(h) for h in active_lineup) / len(active_lineup)
                team_vs_hand_slg = sum(get_h_slg(h) for h in active_lineup) / len(active_lineup)
                team_vs_hand_pa = sum(get_h_pa(h) for h in active_lineup)
            else:
                # Fallback to static splits vs the pitcher's hand
                team_split_key = "vl" if pitcher_hand == "L" else "vr"
                team_split_data = (teams_splits.get(team_name, {}) or {}).get(team_split_key, {}) or {}
                team_vs_hand_ops = team_split_data.get("ops", 0) if isinstance(team_split_data, dict) else 0
                team_vs_hand_woba = team_split_data.get("wOBA_proxy", 0) if isinstance(team_split_data, dict) else 0
                team_vs_hand_avg = team_split_data.get("avg", 0) if isinstance(team_split_data, dict) else 0
                team_vs_hand_slg = team_split_data.get("slg", 0) if isinstance(team_split_data, dict) else 0
                team_vs_hand_pa = team_split_data.get("pa", 0) if isinstance(team_split_data, dict) else 0
                
                team_other_key = "vr" if pitcher_hand == "L" else "vl"
                team_other_data = (teams_splits.get(team_name, {}) or {}).get(team_other_key, {}) or {}
                team_other_ops = team_other_data.get("ops", 0) if isinstance(team_other_data, dict) else 0
                team_other_woba = team_other_data.get("wOBA_proxy", 0) if isinstance(team_other_data, dict) else 0
    
                team_vs_hand_xwoba = woba_proxy_to_xwoba(team_vs_hand_woba, team_vs_hand_ops)
                team_other_xwoba = woba_proxy_to_xwoba(team_other_woba, team_other_ops)
                
                ops_diff = round((team_vs_hand_ops - team_other_ops) * 1000) if team_other_ops else 0
                xwoba_diff = round((team_vs_hand_xwoba - team_other_xwoba) * 1000) if team_other_xwoba else 0
            
            # Pitcher splits (how hittable by LHH vs RHH)
            pitcher_split_data = pitchers_splits.get(norm_pitcher, {}) or {}
            pitcher_vs_lhh = pitcher_split_data.get("vl", {}) or {} if isinstance(pitcher_split_data, dict) else {}
            pitcher_vs_rhh = pitcher_split_data.get("vr", {}) or {} if isinstance(pitcher_split_data, dict) else {}
            pitcher_vs_lhh_ops = pitcher_vs_lhh.get("ops", 0) if isinstance(pitcher_vs_lhh, dict) else 0
            pitcher_vs_lhh_woba = pitcher_vs_lhh.get("wOBA_proxy", 0) if isinstance(pitcher_vs_lhh, dict) else 0
            pitcher_vs_rhh_ops = pitcher_vs_rhh.get("ops", 0) if isinstance(pitcher_vs_rhh, dict) else 0
            pitcher_vs_rhh_woba = pitcher_vs_rhh.get("wOBA_proxy", 0) if isinstance(pitcher_vs_rhh, dict) else 0
            
            pitcher_vs_lhh_xwoba = woba_proxy_to_xwoba(pitcher_vs_lhh_woba, pitcher_vs_lhh_ops)
            pitcher_vs_rhh_xwoba = woba_proxy_to_xwoba(pitcher_vs_rhh_woba, pitcher_vs_rhh_ops)
            
            if pitcher_hand == "L":
                pitcher_vs_opp_hand_xwoba = pitcher_vs_rhh_xwoba
                pitcher_vs_own_hand_xwoba = pitcher_vs_lhh_xwoba
            else:
                pitcher_vs_opp_hand_xwoba = pitcher_vs_lhh_xwoba
                pitcher_vs_own_hand_xwoba = pitcher_vs_rhh_xwoba
                
            NPAS_xwOBA = (team_vs_hand_xwoba - team_other_xwoba) + (pitcher_vs_opp_hand_xwoba - pitcher_vs_own_hand_xwoba)
            NPAS_xwOBA = round(NPAS_xwOBA, 3)
            
            # Pitcher weakness side
            pitcher_weak_side = "LHH" if pitcher_vs_lhh_ops > pitcher_vs_rhh_ops else "RHH"
            pitcher_max_ops = max(pitcher_vs_lhh_ops, pitcher_vs_rhh_ops)
            
            matchups.append({
                "team": team_name,
                "opponent": opponent,
                "opp_pitcher": opp_pitcher_name,
                "pitcher_hand": pitcher_hand,
                "pitcher_hand_label": pitcher_hand_label,
                "team_vs_hand_ops": round(team_vs_hand_ops, 3),
                "team_vs_hand_xwoba": team_vs_hand_xwoba,
                "team_vs_hand_woba": round(team_vs_hand_woba or team_vs_hand_xwoba or 0, 3),
                "xwoba_diff": xwoba_diff,
                "team_vs_hand_avg": round(team_vs_hand_avg or 0.250, 3),
                "team_vs_hand_slg": round(team_vs_hand_slg or 0.400, 3),
                "team_vs_hand_pa": team_vs_hand_pa or 0,
                "ops_diff": ops_diff,
                "pitcher_vs_lhh_ops": round(pitcher_vs_lhh_ops, 3),
                "pitcher_vs_lhh_xwoba": pitcher_vs_lhh_xwoba,
                "pitcher_vs_lhh_woba": round(pitcher_vs_lhh_woba, 3),
                "pitcher_vs_rhh_ops": round(pitcher_vs_rhh_ops, 3),
                "pitcher_vs_rhh_xwoba": pitcher_vs_rhh_xwoba,
                "pitcher_vs_rhh_woba": round(pitcher_vs_rhh_woba, 3),
                "pitcher_weak_side": pitcher_weak_side,
                "pitcher_max_vulnerability_ops": round(pitcher_max_ops, 3),
                "advantage": "NEUTRAL",
                "advantage_xwoba": "NEUTRAL",
                "NPAS_xwOBA": NPAS_xwOBA,
                "stack_score": float(stack_score or 0.0),
                "implied_total": float(implied_total or 0.0)
            })
        except Exception as game_err:
            print(f"[API PLATOONS ERROR] failed to parse game: {team_result} | error: {game_err}")
            continue
    
    # Sort and calibrate slate-wide by NPAS_xwOBA (OMEGA v12.1: Tightened splits)
    if matchups:
        matchups.sort(key=lambda x: x.get("NPAS_xwOBA", 0.0), reverse=True)
        n_m = len(matchups)
        for idx, m in enumerate(matchups):
            percentile = idx / n_m if n_m > 0 else 0.5
            npas = m.get("NPAS_xwOBA", 0.0)
            
            if percentile <= 0.12 and npas >= 0.055:
                label = "ELITE PLATOON"
            elif percentile <= 0.30 and npas >= 0.030:
                label = "STRONG EDGE"
            elif npas <= -0.030 or (percentile >= 0.80 and npas <= -0.010):
                label = "PLATOON TRAP"
            else:
                label = "NEUTRAL"
                
            m["advantage"] = label
            m["advantage_xwoba"] = label
            
    return JSONResponse(
        content={"matchups": matchups, "count": len(matchups)},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/api/radar", dependencies=[Depends(get_current_user)])
def get_radar_api():
    """Matchup Radar DNA: Serves the weekly pitch arsenal & xwOBA parameters."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    radar_path = os.path.join(base_dir, "data", "matchup_data.json")
    if os.path.exists(radar_path):
        try:
            with open(radar_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JSONResponse(content=data)
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
    return JSONResponse(content={"pitchers": {}, "hitters": {}, "league_avg": {}})

@app.get("/api/weather", dependencies=[Depends(get_current_user)])
def get_weather_api():
    """Weather Matrix: Merge expert weather cache with live game totals and starters."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weather_path = os.path.join(base_dir, "data", "expert_weather_cache.json")
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    
    weather_data = []
    results_data = {}
    
    try:
        if os.path.exists(weather_path):
            with open(weather_path, "r", encoding="utf-8") as f:
                weather_data = json.load(f)
        if os.path.exists(results_path):
            with open(results_path, "r", encoding="utf-8") as f:
                results_data = json.load(f)
    except Exception as e:
        return JSONResponse(content={"error": f"Failed to load data: {str(e)}", "games": []}, status_code=500)
        
    pitchers_list = results_data.get("pitchers", [])
    teams_list = results_data.get("teams", [])
    
    # Create lookups
    pitcher_by_team = {p["team"]: p for p in pitchers_list}
    team_info = {t["team"]: t for t in teams_list}
    
    games = []
    for w in weather_data:
        home_team = w.get("home", "")
        away_team = w.get("away", "")
        
        # Resolve pitchers
        home_pitcher = pitcher_by_team.get(home_team, {}).get("pitcher", "TBD")
        away_pitcher = pitcher_by_team.get(away_team, {}).get("pitcher", "TBD")
        
        # Get team stats
        home_stats = team_info.get(home_team, {})
        away_stats = team_info.get(away_team, {})
        
        home_implied = home_stats.get("implied_total", 0)
        away_implied = away_stats.get("implied_total", 0)
        total_line = round(home_implied + away_implied, 2) if (home_implied and away_implied) else 0.0
        
        total_signal = home_stats.get("total_signal", "") or away_stats.get("total_signal", "")
        
        # Risk Priority for sorting (Postponement / Rainout > Delay > Dome > Clear)
        status = w.get("status", "Neutral").lower()
        risk_priority = 0
        if "postpone" in status or "cancel" in status or "red" in status or "hazard" in status:
            risk_priority = 3
        elif "delay" in status or "yellow" in status or "orange" in status:
            risk_priority = 2
        elif "dome" in status or "roof" in status or "indoor" in status:
            risk_priority = 0 # Safe
        elif "clear" in status or "green" in status:
            risk_priority = 1 # Open air active
            
        games.append({
            "home": home_team,
            "away": away_team,
            "home_pitcher": home_pitcher,
            "away_pitcher": away_pitcher,
            "home_implied": home_implied,
            "away_implied": away_implied,
            "total_line": total_line,
            "total_signal": total_signal,
            "temp": w.get("temp", 70),
            "wind_speed": w.get("wind_speed", 5),
            "wind_dir": w.get("wind_dir", "Neutral"),
            "status": w.get("status", "Neutral"),
            "notes": w.get("notes", ""),
            "risk_priority": risk_priority
        })
        
        
    # Sort games by highest risk priority first, then by temperature
    games.sort(key=lambda x: (-x["risk_priority"], -x["temp"]))
    
    return JSONResponse(
        content={"games": games, "count": len(games)},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# OMEGA Feedback Loop: Slate Lock Snapshotting Route
@app.post("/api/snapshot/lock", dependencies=[Depends(get_current_user)])
def post_snapshot_lock_api():
    """Clones the active latest_results.json to a dedicated results_[date]_lock.json snapshot."""
    import shutil
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="Active projections file (latest_results.json) not found.")
        
    try:
        from datetime import datetime, timezone, timedelta
        try:
            from zoneinfo import ZoneInfo
            et_now = datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            utc_now = datetime.now(timezone.utc)
            et_now = utc_now - timedelta(hours=4)
            
        date_str = et_now.strftime("%Y-%m-%d")
        
        archive_dir = os.path.join(base_dir, "reports", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        snapshot_path = os.path.join(archive_dir, f"results_{date_str}_lock.json")
        
        shutil.copy2(results_path, snapshot_path)

        try:
            from utils.dqi import persist_dqi_history
            from config import config
            with open(snapshot_path, "r", encoding="utf-8") as f:
                locked = json.load(f)
            persist_dqi_history(
                locked.get("teams", []),
                config.REPORTS_DIR,
                pitchers=locked.get("pitchers", []),
            )
        except Exception as lock_dqi_e:
            print(f"[LOCK SNAPSHOT WARNING]: DQI persist failed: {lock_dqi_e}")

        # OMEGA v13.8: Auto-run feedback loop on every snapshot lock (non-blocking)
        # Archives signal performance alongside the lock so every slate has a paired audit
        def _run_feedback_bg(d_str, arch_dir):
            try:
                print(f"[LOCK AUTO-AUDIT]: Starting background signal feedback loop for {d_str}...")
                from run_feedback_loop import run_feedback_loop
                run_feedback_loop(30)
                # Copy the freshly generated learning_feedback.json alongside the lock file
                import shutil as _shutil
                from config import config as _cfg
                fb_src = os.path.join(_cfg.REPORTS_DIR, "learning_feedback.json")
                fb_dst = os.path.join(arch_dir, f"feedback_{d_str}_lock.json")
                if os.path.exists(fb_src):
                    _shutil.copy2(fb_src, fb_dst)
                    print(f"[LOCK AUTO-AUDIT]: Signal audit archived to {fb_dst}")
                print(f"[LOCK AUTO-AUDIT]: ✅ Background feedback loop completed for {d_str}.")
            except Exception as fb_err:
                print(f"[LOCK AUTO-AUDIT ERROR]: {fb_err}")

        import threading as _threading
        _threading.Thread(
            target=_run_feedback_bg,
            args=(date_str, archive_dir),
            daemon=True
        ).start()

        print(f"[LOCK SNAPSHOT]: Saved lock snapshot to {snapshot_path}")
        return {"status": "success", "message": f"Lock snapshot saved successfully for {date_str}!", "file": f"results_{date_str}_lock.json"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save lock snapshot: {str(e)}")

# OMEGA Slate Center: Dynamic Betting Edges & DFS Playbook Calculations
@app.get("/api/slate-center", dependencies=[Depends(get_current_user)])
def get_slate_center_api(date: str = None):
    import json
    import os
    import math
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from config import config
    from utils.opening_lines import load_opening_lines_for_slate
    from data.lineup_fetcher import LineupFetcher
    from utils.normalization import normalize_player_name
    from data.bullpen_analyzer import BullpenAnalyzer

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load statcast cache
    statcast_path = os.path.join(base_dir, "data", "statcast_cache.json")
    statcast = {}
    if os.path.exists(statcast_path):
        try:
            with open(statcast_path, "r", encoding="utf-8") as f:
                statcast = json.load(f)
        except Exception as e:
            print(f"Error loading statcast cache: {e}")
            
    bp_analyzer = BullpenAnalyzer()
    
    # Load projections
    if not date:
        results_path = os.path.join(base_dir, "reports", "latest_results.json")
    else:
        results_path = os.path.join(base_dir, "reports", "archive", f"results_{date}_lock.json")
        if not os.path.exists(results_path):
            results_path = os.path.join(base_dir, "reports", "archive", f"results_{date}.json")
            if not os.path.exists(results_path):
                found = False
                reports_dir = os.path.join(base_dir, "reports")
                for f in os.listdir(reports_dir):
                    if date in f and f.endswith(".json"):
                        results_path = os.path.join(reports_dir, f)
                        found = True
                        break
                if not found:
                    raise HTTPException(status_code=404, detail=f"No lock file found containing date {date}")

    if not os.path.exists(results_path):
        results_path = os.path.join(base_dir, "reports", "latest_results.json")
        if not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="Projections data not found.")

    try:
        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read projections: {str(e)}")

    # Load market lines
    opening_lines = load_opening_lines_for_slate(date)

    # Load matchup data (pitch usages, hitter splits)
    matchup_path = os.path.join(base_dir, "data", "matchup_data.json")
    matchup_data = {"pitchers": {}, "hitters": {}, "league_avg": {}}
    if os.path.exists(matchup_path):
        try:
            with open(matchup_path, "r", encoding="utf-8") as f:
                raw_matchup = json.load(f)
                matchup_data = {
                    "pitchers": {normalize_player_name(k): v for k, v in raw_matchup.get("pitchers", {}).items()},
                    "hitters": {normalize_player_name(k): v for k, v in raw_matchup.get("hitters", {}).items()},
                    "league_avg": raw_matchup.get("league_avg", {})
                }
        except Exception as e:
            print(f"Error loading matchup radar: {e}")

    # Fetch confirmed and projected lineups
    try:
        fetcher = LineupFetcher()
        confirmed_lineups = fetcher.fetch_confirmed_lineups(date)
        projected_lineups = fetcher.fetch_projected_lineups(date)
    except Exception as e:
        print(f"Error fetching lineups: {e}")
        confirmed_lineups = {}
        projected_lineups = {}

    def ml_to_prob(ml):
        if not ml or ml == 0:
            return 0.5
        try:
            ml = float(ml)
            if ml < 0:
                return abs(ml) / (abs(ml) + 100)
            else:
                return 100 / (ml + 100)
        except:
            return 0.5

    def normal_cdf(x, mu, sigma):
        return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))

    def calculate_ev(prob, ml):
        if not ml:
            return 0.0
        try:
            ml = float(ml)
            if ml > 0:
                return (prob * (1.0 + ml / 100.0)) - 1.0
            else:
                return (prob * (1.0 + 100.0 / abs(ml))) - 1.0
        except:
            return 0.0

    # Pair teams into games
    games = []
    processed_teams = set()
    teams_list = results.get("teams", [])
    pitchers_list = results.get("pitchers", [])
    hitters_list = results.get("hitters", [])

    # Global franchise abbreviation map
    short_map = {
        'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
        'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
        'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
        'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
        'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
        'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
        'New York Yankees': 'NYY', 'Athletics': 'OAK', 'Oakland Athletics': 'OAK',
        'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
        'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL',
        'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR',
        'Washington Nationals': 'WSH'
    }
    
    def get_abbrev(full_name):
        return short_map.get(full_name, full_name)

    betting_edges = []
    dfs_playbook_teams = []

    for t in teams_list:
        team_name = t.get("team")
        if not team_name or team_name in processed_teams:
            continue

        opponent_name = t.get("opponent")
        opp_team_obj = next((x for x in teams_list if x.get("team") == opponent_name), None)
        if not opp_team_obj:
            continue

        processed_teams.add(team_name)
        processed_teams.add(opponent_name)

        # SP resolution
        team_sp = next((p for p in pitchers_list if p.get("team") == team_name), None)
        opp_sp = next((p for p in pitchers_list if p.get("team") == opponent_name), None)

        # Decide who is Away and who is Home
        is_team_away = True
        if team_sp and team_sp.get("side") == "home":
            is_team_away = False
        elif opp_sp and opp_sp.get("side") == "away":
            is_team_away = False

        away_team = team_name if is_team_away else opponent_name
        home_team = opponent_name if is_team_away else team_name
        
        away_team_obj = t if is_team_away else opp_team_obj
        home_team_obj = opp_team_obj if is_team_away else t

        away_sp_obj = team_sp if is_team_away else opp_sp
        home_sp_obj = opp_sp if is_team_away else team_sp

        # Match Vegas odds
        game_line = None
        for o in opening_lines:
            o_away = o.get("team_away") or ""
            o_home = o.get("team_home") or ""
            if (o_away == away_team and o_home == home_team) or \
               (get_abbrev(o_away) == get_abbrev(away_team) and get_abbrev(o_home) == get_abbrev(home_team)):
                game_line = o
                break

        away_ml = game_line.get("away_current_ml") if game_line else None
        home_ml = game_line.get("home_current_ml") if game_line else None
        open_away_ml = game_line.get("away_opening_ml") if game_line else None
        open_home_ml = game_line.get("home_opening_ml") if game_line else None

        if away_ml is None: away_ml = -110
        if home_ml is None: home_ml = -110
        if open_away_ml is None: open_away_ml = away_ml
        if open_home_ml is None: open_home_ml = home_ml

        curr_total = game_line.get("current_total") if game_line else 9.0
        open_total = game_line.get("opening_total") if game_line else curr_total
        if curr_total is None: curr_total = 9.0
        if open_total is None: open_total = curr_total

        # Win Probabilities
        raw_prob_away = ml_to_prob(away_ml)
        raw_prob_home = ml_to_prob(home_ml)
        sum_prob = raw_prob_away + raw_prob_home
        market_prob_away = raw_prob_away / sum_prob if sum_prob > 0 else 0.5
        market_prob_home = raw_prob_home / sum_prob if sum_prob > 0 else 0.5

        # OMEGA adjusted probability using logit (log-odds) space
        away_rating = float(away_team_obj.get("blended_rating") or away_team_obj.get("stack_score") or 75.0)
        home_rating = float(home_team_obj.get("blended_rating") or home_team_obj.get("stack_score") or 75.0)
        away_sp_rating = float(away_sp_obj.get("blended_rating") or away_sp_obj.get("alpha_score") or 75.0) if away_sp_obj else 75.0
        home_sp_rating = float(home_sp_obj.get("blended_rating") or home_sp_obj.get("alpha_score") or 75.0) if home_sp_obj else 75.0

        away_div = float(away_team_obj.get("divergence") or 0.0)
        home_div = float(home_team_obj.get("divergence") or 0.0)

        # Scale deltas appropriately for log-odds space
        rating_diff = (away_rating - home_rating) * 0.012
        sp_diff = (home_sp_rating - away_sp_rating) * 0.012
        div_diff = (away_div - home_div) * 0.02

        # Convert market probability to log-odds, add deltas, and map back to probability via sigmoid
        market_prob_away_clamped = max(0.01, min(0.99, market_prob_away))
        market_logit = math.log(market_prob_away_clamped / (1.0 - market_prob_away_clamped))
        omega_logit = market_logit + rating_diff + sp_diff + div_diff
        
        omega_prob_away = 1.0 / (1.0 + math.exp(-omega_logit))
        omega_prob_away = max(0.05, min(0.95, omega_prob_away)) # safe bounds
        omega_prob_home = 1.0 - omega_prob_away

        # ML EV
        away_ml_ev = calculate_ev(omega_prob_away, away_ml)
        home_ml_ev = calculate_ev(omega_prob_home, home_ml)

        # Spreads (Run Line)
        if abs(away_ml) > abs(home_ml) or (away_ml < 0 and home_ml > 0):
            away_spread = -1.5
            home_spread = 1.5
        else:
            away_spread = 1.5
            home_spread = -1.5

        away_implied = float(away_team_obj.get("implied_total") or 4.5)
        home_implied = float(home_team_obj.get("implied_total") or 4.5)

        runs_omega_away = max(1.5, away_implied * (1.0 + (away_div / 100.0) + (away_rating - 75.0) * 0.005))
        runs_omega_home = max(1.5, home_implied * (1.0 + (home_div / 100.0) + (home_rating - 75.0) * 0.005))

        margin_mu = runs_omega_away - runs_omega_home
        # Dynamic standard deviation based on Vegas game total (higher total -> higher run margin variance)
        margin_sigma = 1.25 * math.sqrt(curr_total)

        away_spread_cover_prob = 1.0 - normal_cdf(away_spread, margin_mu, margin_sigma)
        home_spread_cover_prob = 1.0 - normal_cdf(home_spread, -margin_mu, margin_sigma)

        away_spread_ev = (away_spread_cover_prob * (1.0 + 100.0/110.0)) - 1.0
        home_spread_ev = (home_spread_cover_prob * (1.0 + 100.0/110.0)) - 1.0

        # Game Totals
        projected_total = runs_omega_away + runs_omega_home
        total_edge = projected_total - curr_total
        if total_edge > 0.25:
            total_edge_type = "OVER"
            total_edge_val = total_edge
        elif total_edge < -0.25:
            total_edge_type = "UNDER"
            total_edge_val = abs(total_edge)
        else:
            total_edge_type = "NEUTRAL"
            total_edge_val = 0.0

        # ── OMEGA v13.8: Conviction Scoring + Suggested Bet Engine ──────────────
        # Conviction is based on (a) pp divergence from market and (b) corroborating signals

        away_pp_div = round((omega_prob_away - market_prob_away) * 100, 1)
        home_pp_div = round((omega_prob_home - market_prob_home) * 100, 1)

        def _conviction(pp_div, ml_ev, spread_ev, total_ev_type, is_favored_side):
            """Return (label, tier) where tier: LOCK/LEAN/PASS."""
            corroborating = 0
            abs_div = abs(pp_div)
            if ml_ev > 0:        corroborating += 1
            if spread_ev > 0:    corroborating += 1
            if total_ev_type != "NEUTRAL": corroborating += 1

            if abs_div >= 4.0 and corroborating >= 2:
                return "LOCK", "lock"
            elif abs_div >= 2.0 or corroborating >= 1:
                return "LEAN", "lean"
            else:
                return "PASS", "pass"

        # Determine which side (if any) has positive ML EV
        away_conv_label, away_conv_tier = _conviction(
            away_pp_div, away_ml_ev, away_spread_ev, total_edge_type, away_ml < home_ml
        )
        home_conv_label, home_conv_tier = _conviction(
            home_pp_div, home_ml_ev, home_spread_ev, total_edge_type, home_ml < away_ml
        )

        # edge_conviction: HIGH if both ML and spread agree on same team
        def _edge_conviction():
            if away_ml_ev > 0 and away_spread_ev > 0:
                return "HIGH"
            if home_ml_ev > 0 and home_spread_ev > 0:
                return "HIGH"
            if (away_ml_ev > 0 or home_ml_ev > 0) and total_edge_type != "NEUTRAL":
                return "MODERATE"
            if away_ml_ev > 0 or home_ml_ev > 0:
                return "SINGLE"
            return "NONE"

        edge_conviction = _edge_conviction()

        # ── Suggested Bet: pick the single best play per game ────────────────────
        def _build_suggested_bet():
            candidates = []

            # ML candidates
            for team, ml, ml_ev, pp_div, opp_ml in [
                (away_team, away_ml, away_ml_ev, away_pp_div, home_ml),
                (home_team, home_ml, home_ml_ev, home_pp_div, away_ml)
            ]:
                if ml_ev > 0:
                    candidates.append({
                        "side": team, "bet_type": "ML",
                        "line": f"+{ml}" if ml > 0 else str(ml),
                        "odds": ml, "ev": round(ml_ev, 4),
                        "pp_div": pp_div
                    })

            # Spread candidates — prefer underdog +1.5 when fav juice > -140
            for team, spread, spread_ev, ml, pp_div in [
                (away_team, away_spread, away_spread_ev, away_ml, away_pp_div),
                (home_team, home_spread, home_spread_ev, home_ml, home_pp_div)
            ]:
                if spread_ev > 0:
                    spread_str = f"+{spread}" if spread > 0 else str(spread)
                    candidates.append({
                        "side": team, "bet_type": "SPREAD",
                        "line": f"{spread_str} (-110)",
                        "odds": -110, "ev": round(spread_ev, 4),
                        "pp_div": pp_div
                    })

            # Total candidates
            if total_edge_type != "NEUTRAL" and total_edge_val >= 0.25:
                total_odds = -110
                total_ev_approx = (total_edge_val / max(curr_total, 1.0)) * 0.3
                candidates.append({
                    "side": f"{total_edge_type} {curr_total}",
                    "bet_type": "TOTAL",
                    "line": f"{total_edge_type} {curr_total} (-110)",
                    "odds": total_odds,
                    "ev": round(total_ev_approx, 4),
                    "pp_div": 0
                })

            if not candidates:
                return {
                    "side": "Pass", "bet_type": "PASS",
                    "line": "—", "odds": 0, "ev": 0.0,
                    "conviction": "PASS", "conviction_tier": "pass",
                    "reason": "No clear edge this game — juice eats any margin."
                }

            # Sort: prefer spread over ML if fav ML juice > -140 and both have positive EV
            def _score(c):
                bonus = 0
                # Prefer underdog run line when same-game fav ML is expensive
                if c["bet_type"] == "SPREAD" and c["odds"] == -110:
                    same_team_ml = next((x for x in candidates
                        if x["bet_type"] == "ML" and x["side"] == c["side"]), None)
                    if same_team_ml and same_team_ml["odds"] < -140:
                        bonus = 0.01  # tie-break toward run line
                return c["ev"] + bonus

            best = sorted(candidates, key=_score, reverse=True)[0]

            # Build the reason string
            if best["bet_type"] == "ML":
                pp = best["pp_div"]
                fav_juicy = best["odds"] < -140
                if fav_juicy:
                    other_spread = next((c for c in candidates
                        if c["bet_type"] == "SPREAD" and c["ev"] > 0), None)
                    if other_spread:
                        reason = (f"OMEGA projects {best['side']} at {best['odds']} "
                                  f"({'+' if pp > 0 else ''}{pp:.1f}pp edge vs market). "
                                  f"ML is the pick — run line ({other_spread['line']}) also has edge.")
                    else:
                        reason = (f"OMEGA projects {best['side']} at {best['odds']} "
                                  f"({'+' if pp > 0 else ''}{pp:.1f}pp edge vs market).")
                else:
                    reason = (f"OMEGA gives {best['side']} a {'+' if pp > 0 else ''}{pp:.1f}pp edge "
                              f"at {best['odds']} — reasonable juice for the ML play.")
            elif best["bet_type"] == "SPREAD":
                # Find the correlated ML
                same_ml = next((c for c in candidates
                    if c["bet_type"] == "ML" and c["side"] == best["side"]), None)
                if same_ml and same_ml["odds"] < -140:
                    reason = (f"OMEGA favors {best['side']} but ML juice ({same_ml['odds']}) is steep. "
                              f"Run line at -110 is better value — both signals agree.")
                else:
                    reason = (f"Spread edge on {best['side']} ({best['line']}) — "
                              f"OMEGA cover probability supports this play.")
            elif best["bet_type"] == "TOTAL":
                reason = (f"OMEGA projects {projected_total:.2f} total vs Vegas {curr_total} "
                          f"— {total_edge_type} edge of {total_edge_val:.2f} runs.")
            else:
                reason = "No clear directional edge."

            # Conviction tier for the best bet
            if abs(best["pp_div"]) >= 4.0 and edge_conviction == "HIGH":
                conv, conv_tier = "LOCK", "lock"
            elif abs(best["pp_div"]) >= 2.0 or best["ev"] > 0.01:
                conv, conv_tier = "LEAN", "lean"
            else:
                conv, conv_tier = "PASS", "pass"

            return {
                "side": best["side"],
                "bet_type": best["bet_type"],
                "line": best["line"],
                "odds": best["odds"],
                "ev": best["ev"],
                "ev_pct": f"+{best['ev']*100:.1f}%" if best["ev"] > 0 else f"{best['ev']*100:.1f}%",
                "conviction": conv,
                "conviction_tier": conv_tier,
                "reason": reason
            }

        suggested_bet = _build_suggested_bet()

        # Construct game edge response
        betting_edges.append({
            "game_id": game_line.get("game_id") if game_line else f"game_{len(betting_edges)}",
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_sp_obj.get("pitcher") if away_sp_obj else "TBD",
            "home_pitcher": home_sp_obj.get("pitcher") if home_sp_obj else "TBD",
            "commence_time": game_line.get("commence_time") if game_line else None,
            "market": {
                "away_ml": int(away_ml),
                "home_ml": int(home_ml),
                "away_spread": away_spread,
                "away_spread_odds": -110,
                "home_spread": home_spread,
                "home_spread_odds": -110,
                "total": curr_total,
                "open_away_ml": int(open_away_ml),
                "open_home_ml": int(open_home_ml),
                "open_total": open_total
            },
            "omega": {
                "away_win_prob": round(omega_prob_away, 3),
                "home_win_prob": round(omega_prob_home, 3),
                "away_pp_div": away_pp_div,
                "home_pp_div": home_pp_div,
                "away_ml_edge": round(away_ml_ev, 3),
                "home_ml_edge": round(home_ml_ev, 3),
                "away_spread_cover_prob": round(away_spread_cover_prob, 3),
                "home_spread_cover_prob": round(home_spread_cover_prob, 3),
                "away_spread_edge": round(away_spread_ev, 3),
                "home_spread_edge": round(home_spread_ev, 3),
                "projected_total": round(projected_total, 2),
                "total_edge": round(total_edge_val, 2),
                "total_edge_type": total_edge_type,
                "edge_conviction": edge_conviction
            },
            "suggested_bet": suggested_bet
        })

        # Process lineup and playbook for BOTH teams in the matchup
        for team_name_side, opp_sp_obj_side in [(away_team, home_sp_obj), (home_team, away_sp_obj)]:
            side_team_obj = away_team_obj if team_name_side == away_team else home_team_obj
            side_opp_name = home_team if team_name_side == away_team else away_team

            lineup_players = confirmed_lineups.get(team_name_side) or confirmed_lineups.get(get_abbrev(team_name_side))
            is_confirmed = (lineup_players is not None and len(lineup_players) >= 7)

            if not is_confirmed:
                projected = projected_lineups.get(team_name_side) or projected_lineups.get(get_abbrev(team_name_side))
                if projected:
                    projected_order = {normalize_player_name(p): idx for idx, p in enumerate(projected)}
                    lineup_players_obj = [h for h in hitters_list if h.get("team") == team_name_side and normalize_player_name(h.get("name", "")) in projected_order]
                    lineup_players_obj = sorted(lineup_players_obj, key=lambda x: projected_order[normalize_player_name(x.get("name", ""))])[:9]
                    lineup_players = [h.get("name") for h in lineup_players_obj]
                
                if not projected or len(lineup_players) < 7:
                    team_hitters = [h for h in hitters_list if h.get("team") == team_name_side]
                    # Filter active players who have played recently (rolling_pa > 0)
                    active_h = [
                        h for h in team_hitters
                        if int(statcast.get(normalize_player_name(h.get("name", "")), {}).get("rolling_pa", 0) or 0) > 0
                    ]
                    if len(active_h) < 9:
                        active_h = team_hitters
                    
                    # Sort active hitters by season PA descending to get everyday starters
                    active_h.sort(
                        key=lambda x: int(statcast.get(normalize_player_name(x.get("name", "")), {}).get("pa", 0) or 0),
                        reverse=True
                    )
                    lineup_players = [h.get("name") for h in active_h[:9]]

            # Fetch opposing bullpen stats
            try:
                opp_bp_fatigue = bp_analyzer.get_fatigue_score(side_opp_name)
                grade, bp_mult, fatigue_mod, bp_era, bp_whip, bp_k_bb = bp_analyzer.get_dynamic_bullpen_grade(side_opp_name)
                opp_bullpen_data = {
                    "fatigue_score": opp_bp_fatigue.get("score", 0.0),
                    "pitches": opp_bp_fatigue.get("pitches", 0),
                    "relievers_used": opp_bp_fatigue.get("relievers_used", 0),
                    "is_gassed": opp_bp_fatigue.get("is_gassed", False),
                    "is_fatigued": opp_bp_fatigue.get("is_fatigued", False),
                    "grade": grade,
                    "multiplier": bp_mult,
                    "era": bp_era,
                    "whip": bp_whip,
                    "k_bb_pct": round(bp_k_bb * 100, 1)
                }
            except Exception as bp_err:
                print(f"Error compiling bullpen data for playbook: {bp_err}")
                opp_bullpen_data = {
                    "fatigue_score": 0.0,
                    "pitches": 0,
                    "relievers_used": 0,
                    "is_gassed": False,
                    "is_fatigued": False,
                    "grade": "Average",
                    "multiplier": 1.0,
                    "era": 4.0,
                    "whip": 1.25,
                    "k_bb_pct": 12.0
                }

            # opposing SP pitch parameters
            opp_sp_name = opp_sp_obj_side.get("pitcher") if opp_sp_obj_side else "TBD"
            opp_sp_hand = opp_sp_obj_side.get("pitch_hand") if opp_sp_obj_side else "R"
            
            sp_pitch_usages = matchup_data["pitchers"].get(normalize_player_name(opp_sp_name), {})
            if not sp_pitch_usages:
                sp_pitch_usages = {"FF": 45.0, "SL": 25.0, "CH": 15.0, "CU": 10.0, "SI": 5.0}

            hitter_rows = []
            for idx, p_name in enumerate(lineup_players[:9]):
                hitter_obj = next((h for h in hitters_list if normalize_player_name(h.get("name", "")) == normalize_player_name(p_name)), None)
                if not hitter_obj:
                    p_norm = normalize_player_name(p_name)
                    hitter_obj = next((h for h in hitters_list if p_norm in normalize_player_name(h.get("name", "")) or normalize_player_name(h.get("name", "")) in p_norm), None)

                p_score = float(hitter_obj.get("player_score") or 0.0) if hitter_obj else 5.0
                attack_conf = float(hitter_obj.get("attack_conf") or 50.0) if hitter_obj else 50.0
                bat_side = hitter_obj.get("bat_side") if hitter_obj else "R"

                # Pitch advantages vs the SP's specific arsenal
                hitter_pitch_stats = matchup_data["hitters"].get(normalize_player_name(p_name), {})
                has_pitch_data = bool(hitter_pitch_stats)

                advantages = {}
                advantage_ratios = {}

                if has_pitch_data:
                    # Full Statcast pitch-type path
                    for ptype in ["FF", "SI", "SL", "CU", "CH"]:
                        league_avg_val = matchup_data["league_avg"].get(ptype, 0.300)
                        h_val = hitter_pitch_stats.get(ptype, league_avg_val)
                        advantages[ptype] = round(h_val, 3)
                        advantage_ratios[ptype] = round(h_val / league_avg_val, 2) if league_avg_val > 0 else 1.0
                else:
                    # OMEGA v13.8: Smart fallback — build multiplier from available hitter signals
                    # so the playbook never shows a flat row of 1.0 for every pitch type
                    platoon_lbl = hitter_obj.get("platoon_label", "NEUTRAL") if hitter_obj else "NEUTRAL"
                    matchup_xwoba = float(hitter_obj.get("matchup_xwoba", 0) or 0) if hitter_obj else 0
                    smash_f = bool(hitter_obj.get("smash_factor")) if hitter_obj else False
                    hot_msmi = bool(hitter_obj.get("is_hot_run_msmi")) if hitter_obj else False
                    cold_msmi = bool(hitter_obj.get("is_cold_streak_msmi")) if hitter_obj else False

                    # Base multiplier from platoon matchup quality
                    base = 1.00
                    if platoon_lbl == "ADVANTAGE":
                        base = 1.08
                    elif platoon_lbl == "DISADVANTAGE":
                        base = 0.92

                    # Adjustments from other signals
                    if matchup_xwoba >= 0.370:
                        base += 0.05
                    elif matchup_xwoba > 0 and matchup_xwoba < 0.280:
                        base -= 0.04

                    if smash_f:     base += 0.05
                    if hot_msmi:    base += 0.03
                    if cold_msmi:   base -= 0.05

                    base = round(max(0.70, min(base, 1.35)), 2)

                    for ptype in ["FF", "SI", "SL", "CU", "CH"]:
                        league_avg_val = matchup_data["league_avg"].get(ptype, 0.300)
                        advantages[ptype] = round(league_avg_val * base, 3)
                        advantage_ratios[ptype] = base

                ahr_price = hitter_obj.get("ahr_price", 0) if hitter_obj else 0
                hits_line = hitter_obj.get("hits_line", "-") if hitter_obj else "-"
                hits_price = hitter_obj.get("hits_price", 0) if hitter_obj else 0
                tb_line = hitter_obj.get("tb_line", "-") if hitter_obj else "-"
                tb_price = hitter_obj.get("tb_price", 0) if hitter_obj else 0
                platoon_label = hitter_obj.get("platoon_label", "NEUTRAL") if hitter_obj else "NEUTRAL"
                smash_factor = hitter_obj.get("smash_factor", False) if hitter_obj else False
                is_juiced_target = hitter_obj.get("is_juiced_target", False) if hitter_obj else False
                is_speed_target = hitter_obj.get("is_speed_target", False) if hitter_obj else False
                is_hot_run_msmi = hitter_obj.get("is_hot_run_msmi", False) if hitter_obj else False
                is_cold_streak_msmi = hitter_obj.get("is_cold_streak_msmi", False) if hitter_obj else False
                is_hot = hitter_obj.get("is_hot", False) if hitter_obj else False
                is_cold_streak = hitter_obj.get("is_cold_streak", False) if hitter_obj else False

                hitter_rows.append({
                    "name": hitter_obj.get("name") if hitter_obj else p_name,
                    "batting_order": idx + 1,
                    "bat_side": bat_side,
                    "player_score": p_score,
                    "attack_conf": attack_conf,
                    "pitch_advantages": advantages,
                    "pitch_advantage_ratios": advantage_ratios,
                    "ahr_price": ahr_price,
                    "hits_line": hits_line,
                    "hits_price": hits_price,
                    "tb_line": tb_line,
                    "tb_price": tb_price,
                    "platoon_label": platoon_label,
                    "smash_factor": smash_factor,
                    "is_juiced_target": is_juiced_target,
                    "is_speed_target": is_speed_target,
                    "is_hot_run_msmi": is_hot_run_msmi,
                    "is_cold_streak_msmi": is_cold_streak_msmi,
                    "is_hot": is_hot,
                    "is_cold_streak": is_cold_streak,
                    "barrel_pct": float(hitter_obj.get("barrel_pct", 0) or 0) if hitter_obj else 0.0,
                    "hard_hit_pct": float(hitter_obj.get("hard_hit_pct", 0) or 0) if hitter_obj else 0.0
                })

            # Top 3 consecutive 4-man stack paths
            paths = []
            if len(hitter_rows) >= 4:
                for start_idx in range(9):
                    path_hitters = []
                    path_score = 0.0
                    path_indices = []
                    for step in range(4):
                        cur_step_idx = (start_idx + step) % len(hitter_rows)
                        path_hitters.append(hitter_rows[cur_step_idx]["name"])
                        path_score += hitter_rows[cur_step_idx]["player_score"]
                        path_indices.append(str(hitter_rows[cur_step_idx]["batting_order"]))
                    
                    paths.append({
                        "path": "-".join(path_indices),
                        "hitters": path_hitters,
                        "score": round(path_score, 1)
                    })
                
                paths.sort(key=lambda x: x["score"], reverse=True)

            dfs_playbook_teams.append({
                "team": team_name_side,
                "opponent": side_opp_name,
                "opp_pitcher": opp_sp_name,
                "opp_pitcher_hand": opp_sp_hand,
                "lineup_status": "CONFIRMED" if is_confirmed else "PROJECTED",
                "lineup": hitter_rows,
                "sp_pitch_usages": sp_pitch_usages,
                "top_stack_paths": paths[:3],
                "opp_bullpen_data": opp_bullpen_data
            })

    return JSONResponse(
        content={
            "betting_edges": betting_edges,
            "dfs_playbook": {
                "teams": dfs_playbook_teams
            }
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# OMEGA Feedback Loop: Serve compiled feedback data
@app.get("/api/learning-feedback", dependencies=[Depends(get_current_user)])
def get_learning_feedback_api():
    """Serves the latest systematic learning loop JSON if it exists."""
    from config import config
    json_path = os.path.join(config.REPORTS_DIR, "learning_feedback.json")
    if not os.path.exists(json_path):
        return JSONResponse(content={"status": "empty", "message": "No learning feedback compiled yet."})
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={"status": "success", "data": data})
    except Exception as e:
        return JSONResponse(content={"error": f"Failed to read learning loop data: {str(e)}"}, status_code=500)

# OMEGA Feedback Loop: Run feedback loop scraping & compilation
@app.post("/api/learning/run", dependencies=[Depends(get_current_user)])
def post_run_learning_loop_api(background_tasks: BackgroundTasks):
    """Triggers background execution of the learning loop audit script."""
    def run_loop_bg():
        try:
            print("[SERVER BG-THREAD]: Running OMEGA Systematic Feedback Loop...")
            from run_feedback_loop import run_feedback_loop
            run_feedback_loop(7) # audit last 7 slates
            print("[SERVER BG-THREAD]: OMEGA Feedback Loop completed successfully.")
        except Exception as bg_err:
            print(f"[SERVER BG-THREAD ERROR]: Feedback loop failed: {bg_err}")
            
    background_tasks.add_task(run_loop_bg)
    return {"status": "started", "message": "Feedback loop learning analysis started in the background."}

# Chatbot endpoint
@app.post("/api/chat", dependencies=[Depends(get_current_user)])
def post_chat_api(body: dict):
    user_msg = body.get("message", "")
    history = body.get("history", [])
    custom_api_key = body.get("api_key", "")
    model_choice = body.get("model", "gemini-2.5-flash")
    
    if model_choice not in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        model_choice = "gemini-2.5-flash"
        
    api_key = custom_api_key or os.getenv("GEMINI_API_KEY") or ""
    
    if not api_key:
        return {
            "reply": "⚠️ **Gemini API Key Missing**\n\nI can't connect to the generative AI models because no `GEMINI_API_KEY` was found. You can either:\n1. Paste your Google Gemini API Key in the **API Key box** at the top right of the Chat Panel.\n2. Add `GEMINI_API_KEY=your_key` to your `.env` file in the project workspace and restart the server.\n\n*In the meantime, I am locked in standby mode. Feed me a key and let's crush this slate!*"
        }

    # Load slate metrics for context injection
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(base_dir, "reports", "latest_results.json")
    analysis_path = os.path.join(base_dir, "reports", "slate_analysis.md")
    
    team_summary = ""
    pitcher_summary = ""
    hitter_summary = ""
    slate_analysis_md = "No analysis available."
    
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                res = json.load(f)
                
            # Extract simple summaries for low token usage
            teams = sorted(res.get("teams", []), key=lambda x: x.get("stack_score", 0), reverse=True)
            teams_itt = {t['team']: t.get('implied_total', 'TBD') for t in teams}
            
            team_summary_items = []
            for t in teams[:10]:
                signals = []
                if t.get('is_shark'): signals.append('SHARK')
                if t.get('is_whale'): signals.append('WHALE')
                if t.get('is_sharp'): signals.append('SHARP')
                if t.get('is_steam'): signals.append('STEAM')
                if t.get('is_trap'): signals.append('TRAP')
                if t.get('is_fade_risk'): signals.append('FADE RISK')
                if t.get('is_sneaky'): signals.append('SNEAKY STACK')
                sig_str = ", ".join(signals) if signals else "None"
                
                from utils.dqi import calculate_dqi as _calc_dqi
                dqi_score, dqi_status, pos_f, warn_f = _calc_dqi(t, pitchers=res.get("pitchers", []))
                dqi_str = f"DQI: {dqi_score}% [{dqi_status}]"
                if pos_f: dqi_str += f" (Strengths: {', '.join(pos_f)})"
                if warn_f: dqi_str += f" (Warnings: {', '.join(warn_f)})"
                
                team_summary_items.append(
                    f"- {t['team']}: OMEGA {t['stack_score']} | ITT {t['implied_total']} | vs {t['opp_pitcher']} | "
                    f"Div {t.get('divergence', 0)}% | {dqi_str} | Signals: {sig_str}"
                )
            team_summary = "\n".join(team_summary_items)
            
            pitchers = sorted(res.get("pitchers", []), key=lambda x: x.get("alpha_score", 0), reverse=True)
            pitcher_summary_items = []
            for p in pitchers[:8]:
                signals = []
                if p.get('is_shark'): signals.append('SHARK')
                if p.get('is_whale'): signals.append('WHALE')
                if p.get('is_sharp'): signals.append('SHARP')
                if p.get('is_steam'): signals.append('STEAM')
                if p.get('is_trap'): signals.append('TRAP')
                sig_str = ", ".join(signals) if signals else "None"
                pitcher_summary_items.append(f"- {p['pitcher']} ({p['team']}): OMEGA {p['alpha_score']} | Opp ITT {teams_itt.get(p['opponent'], 'TBD')} | SIERA {p.get('siera', 'TBD')} | CSW {p.get('csw', 'TBD')} | Signals: {sig_str}")
            pitcher_summary = "\n".join(pitcher_summary_items)
            
            hitters = sorted(res.get("hitters", []), key=lambda x: x.get("player_score", 0), reverse=True)
            hitter_summary = "\n".join([
                f"- {h['name']} ({h['team']}): OMEGA {h['player_score']} | vs {h['opp_pitcher']} | AHR Price {h['ahr_price']}"
                for h in hitters[:12]
            ])
        except Exception as ex:
            print(f"[CHAT ERROR]: Failed to load database summary. {ex}")

    feedback_path = os.path.join(base_dir, "reports", "learning_feedback.md")
    feedback_md = "No performance feedback report compiled yet. Run the feedback audit script to generate."
    
    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, "r", encoding="utf-8") as f:
                slate_analysis_md = f.read()[:15000] # Cap raised to prevent context truncation
        except: pass
        
    if os.path.exists(feedback_path):
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedback_md = f.read()[:10000] # Cap raised to prevent feedback truncation
        except: pass

    # Dynamic Eastern Time zone calculation (prevents UTC container clock drift)
    from datetime import datetime, timezone, timedelta
    try:
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        # Robust fallback: May is in Daylight Saving Time (EDT = UTC-4)
        utc_now = datetime.now(timezone.utc)
        et_now = utc_now - timedelta(hours=4)
        
    current_date_str = et_now.date().isoformat()
    current_time_str = et_now.strftime("%I:%M %p ET")

    # Prepare system context
    system_prompt = f"""You are Antigravity, a world-class agentic AI baseball analyst built by the Google DeepMind team. You are pair-programming and strategizing with Konrad to help him dominate his high-stakes MLB DFS GPP tournaments.

Your personality is highly analytical, professional, confident, and deeply knowledgeable about sabermetrics, DFS roster construction, market psychology, and game-theory strategy. You speak with precision and clarity.

You have access to the absolute, raw OMEGA daily slate analysis and projections:
- CURRENT SLATE DATE: {current_date_str}
- CURRENT TIME: {current_time_str}

Daily Slate Analysis Overview:
{slate_analysis_md}

Top Team Stack Projections (with Divergence Quality Index - DQI):
{team_summary}

Top Starting Pitcher Projections:
{pitcher_summary}

Top Individual Hitter Projections:
{hitter_summary}

### OMEGA HISTORICAL ACCURACY & LEARNING LOOP:
{feedback_md}

### 🧠 OMEGA ELITE BACKTESTED COMBINATIONS:
You must understand and refer to these 7 high-probability combinations:
1. **ELITE OFFENSE (Elite Physics + Weak Arm):** Team xwOBA >= 0.330 and opposing SP Physics <= 35. This has a **66.3% hit rate** for scoring 4+ runs (and 51.7% for 5+ runs).
2. **GASSED BULLPEN ATTACK:** Attacking team xwOBA >= 0.315, opposing SP projected outs <= 15.5, and opposing bullpen fatigue >= 75%. Provides a strong late-inning ceiling (+8.0 pts).
3. **ANTI-CHALK SMASH:** Offense targeting highly popular starting pitcher with hidden contact/physical vulnerabilities (highest GPP leverage pivot).
4. **DQI TRUST:** DQI >= 80, Divergence >= 14%, and Implied Team Total >= 4.2. Extremely reliable sharp money alignment.
5. **PITCHER SHELLING ALERT (Low-Ceiling + Hazard):** SP has low K-upside (K-prop <= 4.5) and faces a high-power offense in a hitter-friendly park. **100% backtested hit rate** (5-for-5) for predicting pitchers getting shelled.
6. **TRUE TALENT & WALKS FADE:** Opposing SP has Walks Penalty + True Talent Penalty (rating reduced by -25.0 pts due to high control risks and bad metrics).
7. **TRAP FADE & WHALE CONVERGENCE:** SP is flagged as a value TRAP and has divergence < -10% (underperforms expectations, fade).

### ⚾ STARTING PITCHER SELECTION GUIDELINES:
- **SP1 Anchors (Safe plays):** Elite underlying Physics score (Physics >= 20), SURGING recent form (high K/9, low ERA L3 starts), and Pinnacle +4% moneyline boost.
- **SP2 GPP Leans (Value plays):** positive sharp money divergence (+10% to +20%), and playing in low game total environments (park/weather overlays like cold temps).
- **Fades / Traps (Avoid):** Flagged as TRAP (public value bait), Walks + True Talent penalty, or Paradox SP (good pitchers in lethal matchups).

### 🧠 UNDERSTANDING DQI (Divergence Quality Index):
DQI fires only when team divergence >= 10% (sharp money interest). Base score starts at 30 points; teams earn TRUST through layered evidence:
- **Baseline:** 30 points (must earn up to TRUST)
- **Gate:** No divergence >= 10% = no DQI shown
- **Positive layers:** Targetable SP physics, gassed bullpen, market steam, O-DIV, xwOBA, power stack, surging trend, run environment, storm/debut bonuses
- **Warning layers:** Reverse steam, U-DIV, fading trend, public chalk trap (-20 pts)
- **🚥 DQI Grades:**
  - `TRUST` (75-100): High-conviction divergence play
  - `CAUTION` (50-74): Mixed signals — proceed carefully
  - `FADE` (under 50): Likely retail trap despite divergence
- **HEAVY $ (`is_sharp`):** Money >= 65% AND divergence >= 10% (not chalk alone)
- **ML WHALE FADE:** Smart money (divergence >= 25%) backing a team while the public tickets go the other way (+2-4% ROI edge in ML betting).

When Konrad asks you questions:
1. Proactively refer to the **DQI (Divergence Quality Index)** scores, strengths, and warning factors of each team! For instance, if a team has DQI TRUST, highlight it as a top high-conviction play for today. If it has DQI CAUTION or FADE, explain the specific warning factors (like Public Chalk or weak opposing SP) causing the flag.
2. Refer directly to the OMEGA metrics, stacks, and pitching rankings listed above. Explain the physics-vs-market variables, weather overlays (like wind out to left), and bullpen fatigue factors in play.
3. Review the OMEGA HISTORICAL ACCURACY report above. Proactively integrate these empirical hit-rates directly into your recommendations! If a specific stack type (like STORM) or signal (like WHALE money on pitchers) has been hot recently, lean heavier into it.
4. Provide concrete, mathematically optimal GPP roster strategies (e.g., recommend specific 5-man or 3-man stacks, high-floor pitcher anchors like Skenes, and high-leverage pitcher values).
5. If Konrad asks about lineup decisions, analyze the xwOBA matchups and market pricing (AHR prices) of the hitters to give him highly actionable suggestions.
6. Maintain full awareness of structural public traps and chalk traps (flagged in the dataset and UI as TRAP, which Konrad visualizes using the 🚨 TRAP badge). Highlight these high-danger public chalk traps and explain why Konrad should fade them.

Keep your tone engaging, sharp, and focused on finding maximum expected value (EV) and leverage to win single-entry and multi-entry GPPs!"""

    # Package message with history
    messages_payload = [
        {"role": "user", "parts": [{"text": system_prompt}]},
        {"role": "model", "parts": [{"text": "Understood. I am Antigravity. I am locked and loaded with the live OMEGA v9.0 database. Let's analyze this slate and optimize some winning lineups, Konrad!"}]}
    ]
    
    # Add history
    for msg in history:
        messages_payload.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["text"]}]
        })
        
    # Add current user message
    messages_payload.append({
        "role": "user",
        "parts": [{"text": user_msg}]
    })

    # Call Gemini API directly via HTTP post
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_choice}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": messages_payload}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        res_json = res.json()
        
        if res.status_code == 200:
            candidates = res_json.get("candidates", [])
            if candidates:
                reply = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return {"reply": reply}
            return {"reply": "Error: Received empty response from generative model."}
        else:
            err_msg = res_json.get("error", {}).get("message", "Unknown error")
            return {"reply": f"⚠️ **API Call Failed**\n\nGemini API returned an error: `{err_msg}` (Status Code {res.status_code})."}
    except Exception as e:
        return {"reply": f"⚠️ **Connection Timeout**\n\nFailed to establish connection to generative services: `{str(e)}`"}

if __name__ == "__main__":
    import uvicorn
    # Run locally on all interfaces, port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
