import requests
import json

HEADERS = {"User-Agent": "Mozilla/5.0"}

def list_mlb_draft_groups():
    url = "https://www.draftkings.com/lobby/getcontests?sport=MLB"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Look for DraftGroups in the contests
            draft_groups = {}
            for contest in data.get('Contests', []):
                dg_id = contest.get('dg')
                if dg_id and dg_id not in draft_groups:
                    name = contest.get('n', '')
                    # Filter for Main Slates or Early Slates
                    if "Main" in name or "Early" in name:
                        draft_groups[dg_id] = name
            
            print("Active MLB DraftGroups found:")
            for dg_id, name in draft_groups.items():
                print(f"  ID: {dg_id} - Name: {name}")
                
            return list(draft_groups.keys())
        else:
            print(f"Error fetching lobby: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    list_mlb_draft_groups()
