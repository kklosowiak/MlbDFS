import requests
import json
import os
import sys

def download_snapshots(server_url):
    # Ensure server_url starts with http/https
    if not server_url.startswith("http"):
        server_url = "https://" + server_url
    # Strip trailing slash
    server_url = server_url.rstrip("/")
    
    print(f"\nConnecting to OMEGA Engine on Render: {server_url}...")
    
    # Define cookies for authentication
    cookies = {"omega_session": "active"}
    
    # 1. Fetch the list of available snapshots
    list_url = f"{server_url}/api/snapshots"
    try:
        response = requests.get(list_url, cookies=cookies, timeout=15)
        if response.status_code == 401:
            print("ERROR: Authentication failed. Make sure the cookie configuration matches the server.")
            return
        elif response.status_code != 200:
            print(f"ERROR: Failed to list snapshots (HTTP {response.status_code})")
            return
            
        data = response.json()
        snapshots = data.get("snapshots", [])
    except Exception as e:
        print(f"ERROR connecting to server: {e}")
        return
        
    if not snapshots:
        print("No snapshots found on the server.")
        return
        
    print(f"Found {len(snapshots)} lock snapshot(s) on Render.")
    
    # Determine local archive directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archive_dir = os.path.join(base_dir, "reports", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    
    # 2. Download each snapshot if not already present locally
    downloaded_count = 0
    skipped_count = 0
    
    for filename in snapshots:
        local_path = os.path.join(archive_dir, filename)
        if os.path.exists(local_path):
            skipped_count += 1
            continue
            
        print(f"Downloading {filename}...")
        download_url = f"{server_url}/api/snapshot/download/{filename}"
        try:
            dl_resp = requests.get(download_url, cookies=cookies, timeout=20)
            if dl_resp.status_code == 200:
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(dl_resp.json(), f, indent=2)
                downloaded_count += 1
            else:
                print(f"  - Failed to download {filename} (HTTP {dl_resp.status_code})")
        except Exception as dl_err:
            print(f"  - Error downloading {filename}: {dl_err}")
            
    print(f"\nSync Complete!")
    print(f"  - New snapshots downloaded: {downloaded_count}")
    print(f"  - Already up-to-date (skipped): {skipped_count}")
    print(f"  - Saved to local directory: {archive_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_snapshots.py [YOUR_RENDER_URL]")
        print("Example: python scripts/download_snapshots.py mlb-dfs.onrender.com")
        url_input = input("\nEnter your Render Server URL: ").strip()
        if not url_input:
            sys.exit(0)
        server_url = url_input
    else:
        server_url = sys.argv[1]
        
    download_snapshots(server_url)
