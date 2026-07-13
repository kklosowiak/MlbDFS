import os
import sys
import csv
import argparse
import json
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

def get_yesterday_et_str():
    dt_utc = datetime.now(timezone.utc)
    if ZoneInfo:
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    else:
        dt_et = dt_utc - timedelta(hours=4)
    yesterday_et = dt_et - timedelta(days=1)
    return yesterday_et.strftime("%Y-%m-%d")

def run_calibration_check(date_str):
    print(f"Running pitcher calibration check for {date_str}...")
    
    base_dir = "."
    snapshots_dir = os.path.join(base_dir, "scratch", "passive_tracker", "snapshots")
    pitchers_snap_path = os.path.join(snapshots_dir, f"all_pitchers_{date_str}.csv")
    
    if not os.path.exists(pitchers_snap_path):
        print(f"No pitcher snapshot CSV found for {date_str}: {pitchers_snap_path}")
        return
        
    log_dir = os.path.join(base_dir, "docs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "pitcher_calibration_log.md")
    
    # Check if we need to write header
    write_header = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
    
    bust_records = []
    
    with open(pitchers_snap_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Target Recommended Pitchers: attack_conf >= 70
                conf = float(row.get('attack_conf', 50.0) or 50.0)
                if conf < 70.0:
                    continue
                    
                actual_dk = float(row.get('actual_dk_pts', 0.0) or 0.0)
                # Busted: actual_dk_pts <= 10.0
                if actual_dk > 10.0:
                    continue
                    
                pitcher = row.get('pitcher', 'Unknown')
                team = row.get('team', 'Unknown')
                recent_era = row.get('recent_era', 'N/A')
                recent_era_5g = row.get('recent_era_5g', 'N/A')
                if not recent_era_5g or recent_era_5g == '':
                    recent_era_5g = 'N/A'
                siera = row.get('siera', 'N/A')
                
                # We can also fetch the L3 BB/9 walks indicator if available
                # Let's search the form cache to get the walks indicator for more details
                form_cache_path = os.path.join(base_dir, "data", "pitcher_form_cache.json")
                recent_bb9 = 'N/A'
                if os.path.exists(form_cache_path):
                    try:
                        with open(form_cache_path, 'r', encoding='utf-8') as cf:
                            cache = json.load(cf)
                        p_norm = pitcher.replace(".", "").replace("'", "").replace("-", "").lower().strip()
                        if p_norm in cache:
                            recent_bb9 = f"{cache[p_norm].get('recent_bb9', 'N/A')}"
                    except Exception:
                        pass
                
                actual_ip = row.get('actual_ip', '0.0')
                actual_er = row.get('actual_er', '0')
                actual_k = row.get('actual_k', '0')
                actual_bb = row.get('actual_bb', '0')
                
                result_str = f"{actual_ip} IP / {actual_er} ER / {actual_k} K / {actual_bb} BB"
                
                bust_records.append({
                    'date': date_str,
                    'pitcher': pitcher,
                    'team': team,
                    'conf': f"{conf:.0f}%",
                    'l3_era': recent_era,
                    'l5_era': recent_era_5g,
                    'siera': siera,
                    'l3_bb9': recent_bb9,
                    'result': result_str,
                    'dk_pts': f"{actual_dk:.1f}"
                })
            except Exception as e:
                print(f"Error parsing row for {row.get('pitcher')}: {e}")
                
    if not bust_records:
        print("No pitcher calibration busts found.")
        return
        
    print(f"Found {len(bust_records)} pitcher calibration busts.")
    
    with open(log_path, 'a', encoding='utf-8') as lf:
        if write_header:
            lf.write("# OMEGA Pitcher Calibration Bust Log\n\n")
            lf.write("Tracks recommended starting pitchers (`attack_conf >= 70`) who scored `actual_dk_pts <= 10.0` points.\n\n")
            lf.write("| Date | Pitcher | Team | Conf | L3 ERA | L5 ERA | SIERA | L3 BB/9 | Result | Actual DK Pts |\n")
            lf.write("|---|---|---|---|---|---|---|---|---|---|\n")
            
        for r in bust_records:
            lf.write(f"| {r['date']} | {r['pitcher']} | {r['team']} | {r['conf']} | {r['l3_era']} | {r['l5_era']} | {r['siera']} | {r['l3_bb9']} | {r['result']} | {r['dk_pts']} |\n")
            
    print(f"Appended {len(bust_records)} entries to {log_path}")

def main():
    parser = argparse.ArgumentParser(description="OMEGA Pitcher Calibration Checker")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to yesterday")
    args = parser.parse_args()
    
    date_str = args.date or get_yesterday_et_str()
    run_calibration_check(date_str)

if __name__ == '__main__':
    main()
