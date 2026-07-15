import time
import sys
import requests

def monitor():
    url = "https://api.github.com/repos/kklosowiak/MlbDFS/actions/runs?branch=audit/july-2026"
    print("Monitoring GHA runs (polling every 30 seconds to prevent rate limit)...")
    sys.stdout.flush()
    
    initial_run_id = None
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            runs = r.json().get("workflow_runs", [])
            if runs:
                initial_run_id = runs[0]["id"]
    except Exception:
        pass
        
    print(f"Ignoring last run ID: {initial_run_id}. Waiting for new manual trigger...")
    sys.stdout.flush()
    
    seen_runs = {}
    while True:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                runs = data.get("workflow_runs", [])
                if runs:
                    latest = runs[0]
                    run_id = latest["id"]
                    status = latest["status"]
                    conclusion = latest["conclusion"]
                    name = latest["name"]
                    run_num = latest["run_number"]
                    
                    if run_id == initial_run_id:
                        # No new run detected yet
                        time.sleep(30)
                        continue
                        
                    state = f"{status}_{conclusion}"
                    if run_id not in seen_runs or seen_runs[run_id] != state:
                        seen_runs[run_id] = state
                        print(f"Workflow '{name}' (Run #{run_num}, ID {run_id}) is currently: {status.upper()}" + (f" ({conclusion.upper()})" if conclusion else ""))
                        sys.stdout.flush()
                        
                        if status == "completed":
                            if conclusion == "success":
                                print("SUCCESS! New workflow run completed successfully.")
                            else:
                                print(f"FAILURE! New workflow run failed with: {conclusion}")
                            sys.stdout.flush()
                            break
                else:
                    print("No runs detected. Waiting for trigger...")
                    sys.stdout.flush()
            elif r.status_code == 403:
                print("GitHub API rate limited. Retrying...")
                sys.stdout.flush()
            else:
                print(f"GitHub API Error: {r.status_code}")
                sys.stdout.flush()
        except Exception as e:
            print(f"Network error: {e}")
            sys.stdout.flush()
        time.sleep(30)

if __name__ == "__main__":
    monitor()
