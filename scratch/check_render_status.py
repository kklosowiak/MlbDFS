import requests
import json

def check_status():
    session = requests.Session()
    
    # 1. Log in to get session cookie
    login_url = "https://mlbdfs.onrender.com/login"
    print(f"Logging in to {login_url}...")
    try:
        response = session.post(login_url, data={"password": "dasox"}, allow_redirects=True, timeout=15)
        print(f"Login Response Code: {response.status_code}")
        print(f"Cookies: {session.cookies.get_dict()}")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # 2. Check refresh status
    status_url = "https://mlbdfs.onrender.com/api/refresh-status"
    print(f"\nChecking status at {status_url}...")
    try:
        res = session.get(status_url, timeout=15)
        print(f"Status Code: {res.status_code}")
        print(f"Content: {res.text}")
    except Exception as e:
        print(f"Failed to check status: {e}")

    # 3. Check environment diagnostics
    debug_url = "https://mlbdfs.onrender.com/api/debug-env"
    print(f"\nChecking env diagnostics at {debug_url}...")
    try:
        res = session.get(debug_url, timeout=15)
        print(f"Status Code: {res.status_code}")
        print(f"Diagnostics: {json.dumps(res.json(), indent=2)}")
    except Exception as e:
        print(f"Failed to check environment diagnostics: {e}")

    # 4. Check results
    results_url = "https://mlbdfs.onrender.com/api/results"
    print(f"\nChecking results at {results_url}...")
    try:
        res = session.get(results_url, timeout=15)
        print(f"Status Code: {res.status_code}")
        res_json = res.json()
        print(f"Timestamp: {res_json.get('timestamp')}")
        print(f"Pitchers count: {len(res_json.get('pitchers', []))}")
        print(f"Teams count: {len(res_json.get('teams', []))}")
        print(f"Hitters count: {len(res_json.get('hitters', []))}")
        if 'error' in res_json:
            print(f"Error field present: {res_json['error']}")
    except Exception as e:
        print(f"Failed to check results: {e}")

if __name__ == "__main__":
    check_status()
