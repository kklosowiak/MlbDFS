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
app = FastAPI(title="OMEGA Cockpit v9.0")

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

# Auth config
PASSWORD = os.getenv("OMEGA_PASSWORD", "omega2026")
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
        perform_fetch()
        
        with refresh_lock:
            refresh_progress = "Running OMEGA engine analysis..."
            
        print("[SERVER BG-THREAD]: Starting model calculations...")
        from main import run_full_analysis
        run_full_analysis()
        
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
            refresh_progress = f"Error: {str(e)}"
            is_refreshing = False

# Background scheduler thread
def scheduler_loop():
    global is_refreshing, last_refresh_timestamp_raw, last_scheduled_hour_key
    print("[SERVER]: Auto-Refresh Hourly Scheduler thread started (Active: 8AM-8PM EST).")
    
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
        
        # Is Eastern Time between 8:00 AM (8) and 8:00 PM (20) inclusive?
        is_active_window = (8 <= et_hour <= 20)
        
        if is_active_window:
            if current_hour_key != last_scheduled_hour_key:
                print(f"[SERVER]: Scheduled Auto-Refresh triggered for hour: {et_now.strftime('%I:%M %p ET')}.")
                perform_refresh_sync()
            
        # Sleep for 10 seconds before checking time again
        time.sleep(10)

# Start scheduler in daemon thread
scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
scheduler_thread.start()

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
        <title>OMEGA ENGINE - SECURE PORTAL</title>
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
            <h2>OMEGA COCKPIT</h2>
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
    if password == PASSWORD:
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
            return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8")
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
        return JSONResponse(
            content=data,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        return {"error": "No results available yet. Run a slate refresh."}

@app.get("/api/analysis", dependencies=[Depends(get_current_user)])
def get_analysis_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_path = os.path.join(base_dir, "reports", "slate_analysis.md")
    
    if os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8") as f:
            return {"markdown": f.read()}
    else:
        return {"markdown": "No analysis available yet."}

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
    import os
    apiKey = os.getenv("ODDS_API_KEY", "")
    key_status = "Missing"
    if apiKey:
        key_status = f"Present (Len: {len(apiKey)}, Start: {apiKey[:4]}...)"
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    reports_dir = os.path.join(base_dir, "reports")
    
    data_files = os.listdir(data_dir) if os.path.exists(data_dir) else []
    reports_files = os.listdir(reports_dir) if os.path.exists(reports_dir) else []
    
    from run_fetch import get_slate_date
    try:
        slate_date = str(get_slate_date())
    except Exception as e:
        slate_date = f"Error: {e}"
        
    return {
        "odds_api_key_status": key_status,
        "data_files": data_files,
        "reports_files": reports_files,
        "base_date_slate": slate_date
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

# Chatbot endpoint
@app.post("/api/chat", dependencies=[Depends(get_current_user)])
def post_chat_api(body: dict):
    user_msg = body.get("message", "")
    history = body.get("history", [])
    custom_api_key = body.get("api_key", "")
    
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
            team_summary = "\n".join([
                f"- {t['team']}: OMEGA {t['stack_score']} | ITT {t['implied_total']} | vs {t['opp_pitcher']} | Div {t.get('divergence', 0)}%"
                for t in teams[:10]
            ])
            
            pitchers = sorted(res.get("pitchers", []), key=lambda x: x.get("alpha_score", 0), reverse=True)
            pitcher_summary = "\n".join([
                f"- {p['pitcher']} ({p['team']}): OMEGA {p['alpha_score']} | Opp ITT {teams_itt.get(p['opponent'], 'TBD') if 'teams_itt' in locals() else 'TBD'} | SIERA {p.get('siera', 'TBD')} | CSW {p.get('csw', 'TBD')}"
                for p in pitchers[:8]
            ])
            
            hitters = sorted(res.get("hitters", []), key=lambda x: x.get("player_score", 0), reverse=True)
            hitter_summary = "\n".join([
                f"- {h['name']} ({h['team']}): OMEGA {h['player_score']} | vs {h['opp_pitcher']} | AHR Price {h['ahr_price']}"
                for h in hitters[:12]
            ])
        except Exception as ex:
            print(f"[CHAT ERROR]: Failed to load database summary. {ex}")

    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, "r", encoding="utf-8") as f:
                slate_analysis_md = f.read()[:5000] # Cap to prevent context blowup
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

You have access to the absolute, raw OMEGA v9.0 daily slate analysis and projections:
- CURRENT SLATE DATE: {current_date_str}
- CURRENT TIME: {current_time_str}

Daily Slate Analysis Overview:
{slate_analysis_md}

Top Team Stack Projections (v8.9.1 Golden Ratio):
{team_summary}

Top Starting Pitcher Projections (v9.0 Cy Young Patch):
{pitcher_summary}

Top Individual Hitter Projections:
{hitter_summary}

When Konrad asks you questions:
1. Refer directly to the OMEGA v9.0 metrics, stacks, and pitching rankings listed above. Explain the physics-vs-market variables, weather overlays (like wind out to left), and bullpen fatigue factors in play.
2. Provide concrete, mathematically optimal GPP roster strategies (e.g., recommend specific 5-man or 3-man stacks, high-floor pitcher anchors like Skenes, and high-leverage pitcher values like Pallante).
3. If Konrad asks about lineup decisions, analyze the xwOBA matchups and market pricing (AHR prices) of the hitters to give him highly actionable suggestions.
4. Maintain full awareness of structural traps (e.g., the St. Louis contact trap, Wheeler's previous negative divergence markdown which we solved under v9.0, etc.).

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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
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
