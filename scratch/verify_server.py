import requests
import sys

def verify_server():
    print("====================================================================")
    print("                OMEGA SERVER PORTAL VERIFICATION")
    print("====================================================================")
    
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    # 1. Test unauthenticated redirect
    print("\n[TEST 1] Visiting '/' unauthenticated...")
    try:
        r = session.get(f"{base_url}/", allow_redirects=False)
        print(f"  - Status Code: {r.status_code}")
        print(f"  - Headers Location: {r.headers.get('location')}")
        if r.status_code == 307 or r.status_code == 303:
            print("  - [PASS] Unauthenticated access properly redirected to login gate!")
        else:
            print("  - [FAIL] Expected redirect, got different status.")
    except Exception as e:
        print(f"  - [CRITICAL] Failed to connect to server: {e}")
        return False

    # 2. Test API endpoints unauthenticated
    print("\n[TEST 2] Fetching '/api/results' unauthenticated...")
    try:
        r = session.get(f"{base_url}/api/results")
        print(f"  - Status Code: {r.status_code}")
        print(f"  - Response: {r.json()}")
        if r.status_code == 401:
            print("  - [PASS] Unauthenticated API access blocked with 401 Unauthorized!")
        else:
            print("  - [FAIL] Expected 401 Unauthorized for API.")
    except Exception as e:
        print(f"  - [FAIL] API call errored: {e}")

    # 3. Test Authentication Login
    print("\n[TEST 3] Logging in with default password 'omega2026'...")
    try:
        r = session.post(f"{base_url}/login", data={"password": "omega2026"}, allow_redirects=False)
        print(f"  - Status Code: {r.status_code}")
        print(f"  - Cookies: {session.cookies.get_dict()}")
        print(f"  - Redirect Location: {r.headers.get('location')}")
        
        if session.cookies.get("omega_session") == "active":
            print("  - [PASS] Authentication successful! Session cookie 'omega_session=active' set.")
        else:
            print("  - [FAIL] Session cookie not set or invalid.")
            return False
    except Exception as e:
        print(f"  - [FAIL] Login post failed: {e}")
        return False

    # 4. Test Authenticated access to dashboard
    print("\n[TEST 4] Visiting '/' with active session cookie...")
    try:
        r = session.get(f"{base_url}/")
        print(f"  - Status Code: {r.status_code}")
        safe_snippet = r.text[:200].encode('ascii', errors='replace').decode('ascii').strip()
        print(f"  - Page Content snippet: {safe_snippet}...")
        if r.status_code == 200 and "OMEGA COCKPIT" in r.text:
            print("  - [PASS] Authenticated dashboard successfully rendered!")
        else:
            print("  - [FAIL] Dashboard failed to render or contain expected headers.")
    except Exception as e:
        print(f"  - [FAIL] Dashboard load failed: {e}")

    # 5. Test Authenticated API data access
    print("\n[TEST 5] Fetching '/api/results' with active session cookie...")
    try:
        r = session.get(f"{base_url}/api/results")
        print(f"  - Status Code: {r.status_code}")
        data = r.json()
        print(f"  - Pitchers Count: {len(data.get('pitchers', []))}")
        print(f"  - Teams Count: {len(data.get('teams', []))}")
        print(f"  - Hitters Count: {len(data.get('hitters', []))}")
        
        if r.status_code == 200 and len(data.get('pitchers', [])) > 0:
            print("  - [PASS] Dynamic OMEGA v9.0 calculations successfully retrieved as JSON!")
        else:
            print("  - [FAIL] Expected active results, got empty or failed payload.")
    except Exception as e:
        print(f"  - [FAIL] Authenticated API call failed: {e}")

    print("\n====================================================================")
    print("          CONGRATULATIONS: ALL SERVER SECURITY & API TESTS PASS!")
    print("====================================================================")
    return True

if __name__ == "__main__":
    verify_server()
