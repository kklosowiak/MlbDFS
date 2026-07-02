import os
import sys
import argparse
import subprocess
import shutil
import json
from datetime import datetime, timezone

def main():
    parser = argparse.ArgumentParser(description="OMEGA Nightly Prediction Capture Script")
    parser.add_argument("--time", choices=["1530", "2220"], required=True, help="Capture time slot (1530 or 2220)")
    args = parser.parse_args()

    time_slot = args.time
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    target_dir = os.path.join("scratch", "passive_tracker", "slates")
    os.makedirs(target_dir, exist_ok=True)

    timestamped_filename = f"omega-results_{today_str}_{time_slot}UTC.json"
    timestamped_path = os.path.join(target_dir, timestamped_filename)
    latest_path = os.path.join(target_dir, f"omega-results_{today_str}_latest.json")
    log_path = os.path.join("scratch", "passive_tracker", "capture_log.txt")

    # Idempotency Check
    if os.path.exists(timestamped_path):
        print(f"Capture for {today_str} {time_slot} already exists. Skipping.")
        sys.exit(0)

    print(f"Starting OMEGA capture for {today_str} {time_slot}UTC...")

    # Step 1: Run Ingestion
    print("Running data fetch (run_fetch.py)...")
    fetch_result = subprocess.run([sys.executable, "run_fetch.py"], capture_output=True, text=True)
    if fetch_result.returncode != 0:
        log_message(log_path, today_str, time_slot, "FAIL", "run_fetch.py failed")
        print(f"Error running run_fetch.py:\n{fetch_result.stderr}")
        sys.exit(1)

    # Step 2: Run Analysis
    print("Running model analysis (main.py)...")
    analysis_result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)
    if analysis_result.returncode != 0:
        log_message(log_path, today_str, time_slot, "FAIL", "main.py failed")
        print(f"Error running main.py:\n{analysis_result.stderr}")
        sys.exit(1)

    # Step 3: Verify and Save Output
    source_results_path = os.path.join("reports", "latest_results.json")
    if not os.path.exists(source_results_path):
        log_message(log_path, today_str, time_slot, "FAIL", "latest_results.json not produced")
        print("Error: reports/latest_results.json was not generated.")
        sys.exit(1)

    try:
        with open(source_results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log_message(log_path, today_str, time_slot, "FAIL", f"JSON load failed: {str(e)}")
        print(f"Error parsing latest_results.json: {e}")
        sys.exit(1)

    teams = data.get("teams", [])
    if not teams:
        log_message(log_path, today_str, time_slot, "EMPTY", "No games/teams active on this slate")
        print("No active games or teams found in results (off day). Exiting cleanly.")
        # Save an empty marker results file so we know the run occurred but was empty
        with open(timestamped_path, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "teams": [], "pitchers": [], "hitters": []}, f, indent=4)
        shutil.copy(timestamped_path, latest_path)
        sys.exit(0)

    # Copy to timestamped and latest path
    try:
        shutil.copy(source_results_path, timestamped_path)
        shutil.copy(source_results_path, latest_path)
    except Exception as e:
        log_message(log_path, today_str, time_slot, "FAIL", f"File copy failed: {str(e)}")
        print(f"Error copying results files: {e}")
        sys.exit(1)

    log_message(log_path, today_str, time_slot, "SUCCESS", f"Captured {len(teams)} teams")
    print(f"Successfully captured OMEGA results for {today_str} {time_slot}UTC.")

def log_message(log_path, date_str, time_slot, status, message):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] DATE: {date_str} | TIME: {time_slot} | STATUS: {status} | {message}\n")

if __name__ == "__main__":
    main()
