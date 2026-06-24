import csv
import io
import os
import json
import requests
from utils.normalization import normalize_player_name

# Standard Baseball Savant pitch types mapped to expected output keys
# FF: 4-seam, SI: sinker, SL: slider, CU: curveball, CH: changeup, FC: cutter, FS: splitter
PITCH_MAP = {
    "FF": ["ff_percent", "n_ff", "ff_pa", "ff_avg_speed"],
    "SI": ["si_percent", "n_si", "si_pa", "si_avg_speed"],
    "SL": ["sl_percent", "n_sl", "sl_pa", "sl_avg_speed"],
    "CU": ["cu_percent", "n_cu", "cu_pa", "cu_avg_speed"],
    "CH": ["ch_percent", "n_ch", "ch_pa", "ch_avg_speed"],
    "FC": ["fc_percent", "n_fc", "fc_pa", "fc_avg_speed"],
    "FS": ["fs_percent", "n_fs", "fs_pa", "fs_avg_speed"]
}

def fetch_pitcher_arsenal(year: int) -> dict:
    """Returns {normalized_name: {pitch_type: usage_pct, ...}, ip: float}"""
    # Use exact CSV endpoint requested
    url = f"https://baseballsavant.mlb.com/leaderboard/pitch-arsenals?year={year}&min=25&type=pa&csv=true"
    print(f"[MATCHUP DNA]: Fetching pitcher arsenal from URL: {url}")
    
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    
    text = r.text
    if text.startswith('\ufeff'):
        text = text[1:]
        
    f = io.StringIO(text)
    reader = csv.reader(f)
    try:
        headers = [h.strip() for h in next(reader)]
    except StopIteration:
        headers = []
        
    print(f"[MATCHUP DNA]: Actual CSV headers found for pitcher_arsenal {year} (type=pa):")
    print(headers)
    
    # We fetch type=n_ as fallback/real source of usage percentages since type=pa columns are returned empty on Savant
    url_n = f"https://baseballsavant.mlb.com/leaderboard/pitch-arsenals?year={year}&min=25&type=n_&csv=true"
    print(f"[MATCHUP DNA]: Fetching real usage data from fallback URL: {url_n}")
    
    r_n = requests.get(url_n, timeout=15)
    r_n.raise_for_status()
    
    text_n = r_n.text
    if text_n.startswith('\ufeff'):
        text_n = text_n[1:]
        
    f_n = io.StringIO(text_n)
    reader_n = csv.reader(f_n)
    try:
        headers_n = [h.strip() for h in next(reader_n)]
    except StopIteration:
        headers_n = []
        
    print(f"[MATCHUP DNA]: Fallback CSV headers found for pitcher_arsenal {year} (type=n_):")
    print(headers_n)
    
    col_mapping = {}
    missing_cols = []
    
    # We verify the columns against headers_n (which is where we extract data)
    for ptype, aliases in PITCH_MAP.items():
        found_col = None
        for alias in aliases:
            if alias in headers_n:
                found_col = alias
                break
        if found_col:
            col_mapping[ptype] = found_col
        else:
            missing_cols.append(ptype)
            
    if missing_cols:
        print(f"[MATCHUP DNA]: Missing columns for pitch types: {missing_cols}. Expected aliases: {[PITCH_MAP[p] for p in missing_cols]}. Available headers: {headers_n}")
        
    name_col = next((c for c in ['last_name, first_name', 'player_name', 'name'] if c in headers_n), None)
    if not name_col:
        raise ValueError(f"Could not find name column in pitcher arsenal headers: {headers_n}")
        
    # Load statcast_cache to resolve pitcher IP
    cache = {}
    cache_path = os.path.join("data", "statcast_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as file:
                cache = json.load(file)
        except Exception as e:
            print(f"[MATCHUP DNA]: Could not read {cache_path} for IP resolution: {e}")
            
    result = {}
    for row in reader_n:
        if not row:
            continue
        try:
            row_dict = dict(zip(headers_n, row))
            raw_name = row_dict.get(name_col, "").strip()
            if not raw_name:
                continue
            norm_name = normalize_player_name(raw_name)
            
            player_pitches = {}
            for ptype, col_name in col_mapping.items():
                val_str = row_dict.get(col_name, "").strip()
                try:
                    val = float(val_str) if val_str else 0.0
                except ValueError:
                    val = 0.0
                player_pitches[ptype] = val
                
            # Default missing keys to 0.0 rather than crashing
            for ptype in PITCH_MAP:
                if ptype not in player_pitches:
                    player_pitches[ptype] = 0.0
                    
            # Retrieve IP
            ip_key = "ip" if year == 2026 else "ip_2025"
            ip = float(cache.get(norm_name, {}).get(ip_key, 0.0) or 0.0)
            
            # Default to 25.0 if IP is 0.0 but pitcher has recorded usage
            if ip == 0.0 and any(v > 0.0 for k, v in player_pitches.items() if k != "ip"):
                ip = 25.0
                
            player_pitches["ip"] = ip
            result[norm_name] = player_pitches
        except Exception as e:
            print(f"[MATCHUP DNA]: Skipped row for pitcher due to error: {e}")
            
    return result

def fetch_hitter_pitch_xwoba(year: int) -> dict:
    """Returns {normalized_name: {pitch_type: xwoba, pa: int}}"""
    url = f"https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=batter&year={year}&min={25}&csv=true"
    print(f"[MATCHUP DNA]: Fetching hitter xwOBA from URL: {url}")
    
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    
    text = r.text
    if text.startswith('\ufeff'):
        text = text[1:]
        
    f = io.StringIO(text)
    reader = csv.reader(f)
    try:
        headers = [h.strip() for h in next(reader)]
    except StopIteration:
        headers = []
        
    print(f"[MATCHUP DNA]: Actual CSV headers found for hitter_xwoba {year}:")
    print(headers)
    
    is_long = 'pitch_type' in headers
    result = {}
    
    if is_long:
        name_col = next((c for c in ['last_name, first_name', 'player_name', 'name'] if c in headers), None)
        pitch_type_col = 'pitch_type'
        xwoba_col = next((c for c in ['est_woba', 'est_xwoba', 'xwoba'] if c in headers), None)
        pa_col = next((c for c in ['pa'] if c in headers), None)
        
        if not name_col or not xwoba_col:
            raise ValueError(f"Missing player name or xwoba column in headers: {headers}")
            
        for row in reader:
            if not row:
                continue
            row_dict = dict(zip(headers, row))
            raw_name = row_dict.get(name_col, "").strip()
            if not raw_name:
                continue
            norm_name = normalize_player_name(raw_name)
            
            pitch_type = row_dict.get(pitch_type_col, "").strip().upper()
            if pitch_type not in PITCH_MAP:
                continue
                
            xwoba_val_str = row_dict.get(xwoba_col, "").strip()
            pa_val_str = row_dict.get(pa_col, "0").strip() if pa_col else "0"
            
            try:
                xwoba_val = float(xwoba_val_str) if xwoba_val_str else 0.0
                if xwoba_val > 0.0:
                    xwoba_val = max(0.150, min(0.600, xwoba_val))
            except ValueError:
                xwoba_val = 0.0
                
            try:
                pa_val = int(pa_val_str) if pa_val_str else 0
            except ValueError:
                pa_val = 0
                
            if norm_name not in result:
                result[norm_name] = {"pa": 0}
                    
            if xwoba_val > 0.0:
                result[norm_name][pitch_type] = xwoba_val
            result[norm_name]["pa"] += pa_val
            
    else:
        # Support wide-format hitter stats if Baseball Savant changes format
        name_col = next((c for c in ['last_name, first_name', 'player_name', 'name'] if c in headers), None)
        pa_col = next((c for c in ['pa'] if c in headers), None)
        
        wide_map = {
            "FF": ['ff_avg_xwoba', 'ff_xwoba', 'ff_est_woba'],
            "SI": ['si_avg_xwoba', 'si_xwoba', 'si_est_woba'],
            "SL": ['sl_avg_xwoba', 'sl_xwoba', 'sl_est_woba'],
            "CU": ['cu_avg_xwoba', 'cu_xwoba', 'cu_est_woba'],
            "CH": ['ch_avg_xwoba', 'ch_xwoba', 'ch_est_woba'],
            "FC": ['fc_avg_xwoba', 'fc_xwoba', 'fc_est_woba'],
            "FS": ['fs_avg_xwoba', 'fs_xwoba', 'fs_est_woba']
        }
        
        col_mapping = {}
        missing_cols = []
        for ptype, aliases in wide_map.items():
            found_col = None
            for alias in aliases:
                if alias in headers:
                    found_col = alias
                    break
            if found_col:
                col_mapping[ptype] = found_col
            else:
                missing_cols.append(ptype)
                
        if missing_cols:
            print(f"[MATCHUP DNA]: Hitter missing wide columns: {missing_cols}")
            
        if not name_col:
            raise ValueError(f"Could not find name column in hitter headers: {headers}")
            
        for row in reader:
            if not row:
                continue
            row_dict = dict(zip(headers, row))
            raw_name = row_dict.get(name_col, "").strip()
            if not raw_name:
                continue
            norm_name = normalize_player_name(raw_name)
            
            player_data = {"pa": 0}
            for ptype, col_name in col_mapping.items():
                val_str = row_dict.get(col_name, "").strip()
                try:
                    val = float(val_str) if val_str else 0.0
                    if val > 0.0:
                        val = max(0.150, min(0.600, val))
                except ValueError:
                    val = 0.0
                if val > 0.0:
                    player_data[ptype] = val
                    
            if pa_col:
                pa_val_str = row_dict.get(pa_col, "0").strip()
                try:
                    pa_val = int(pa_val_str) if pa_val_str else 0
                except ValueError:
                    pa_val = 0
                player_data["pa"] = pa_val
            else:
                player_data["pa"] = 100
                
            result[norm_name] = player_data
            
    return result

def fetch_league_avg_xwoba(year: int) -> dict:
    """Returns {pitch_type: league_avg_xwoba}"""
    # Fetch 2026 and 2025 hitter datasets
    hitters_2026 = fetch_hitter_pitch_xwoba(2026)
    hitters_2025 = fetch_hitter_pitch_xwoba(2025)
    
    pitch_types = ['FF', 'SI', 'SL', 'CU', 'CH', 'FC', 'FS']
    result = {}
    
    # Absolute fallback averages from current schema
    default_averages = {
        "FF": 0.335,
        "SI": 0.330,
        "SL": 0.290,
        "CU": 0.280,
        "CH": 0.285,
        "FC": 0.300,
        "FS": 0.295
    }
    
    for ptype in pitch_types:
        # Filter for batters with non-zero xwOBA
        vals_2026 = [player[ptype] for player in hitters_2026.values() if ptype in player and player[ptype] > 0.0]
        if len(vals_2026) >= 100:
            result[ptype] = sum(vals_2026) / len(vals_2026)
        else:
            print(f"[MATCHUP DNA]: Insufficient 2026 data for {ptype} (N={len(vals_2026)} < 100). Falling back to 2025...")
            vals_2025 = [player[ptype] for player in hitters_2025.values() if ptype in player and player[ptype] > 0.0]
            if len(vals_2025) >= 100:
                result[ptype] = sum(vals_2025) / len(vals_2025)
            else:
                print(f"[MATCHUP DNA]: Insufficient 2025 data for {ptype} (N={len(vals_2025)} < 100). Using hardcoded default.")
                result[ptype] = default_averages.get(ptype, 0.300)
                
        result[ptype] = round(result[ptype], 3)
        
    return result

def build_matchup_data() -> dict:
    """Pulls 2025 + 2026, blends, returns full matchup_data.json structure"""
    try:
        print("[MATCHUP DNA]: Pulling 2026 and 2025 pitcher arsenals...")
        pitchers_2026 = fetch_pitcher_arsenal(2026)
        pitchers_2025 = fetch_pitcher_arsenal(2025)
        
        print("[MATCHUP DNA]: Pulling 2026 and 2025 hitter xwOBAs...")
        hitters_2026 = fetch_hitter_pitch_xwoba(2026)
        hitters_2025 = fetch_hitter_pitch_xwoba(2025)
        
        print("[MATCHUP DNA]: Computing league average xwOBAs...")
        league_avg = fetch_league_avg_xwoba(2026)
        
        pitch_types = ['FF', 'SI', 'SL', 'CU', 'CH', 'FC', 'FS']
        
        # 1. Blend Pitchers
        blended_pitchers = {}
        all_pitchers = set(list(pitchers_2026.keys()) + list(pitchers_2025.keys()))
        for name in all_pitchers:
            p26 = pitchers_2026.get(name)
            p25 = pitchers_2025.get(name)
            
            if p26 and p25:
                ip_2026 = p26.get("ip", 0.0)
                weight_2026 = min(1.0, ip_2026 / 50.0)
                
                blended = {}
                for ptype in pitch_types:
                    usage_2026 = p26.get(ptype, 0.0)
                    usage_2025 = p25.get(ptype, 0.0)
                    blended_usage = (weight_2026 * usage_2026) + ((1.0 - weight_2026) * usage_2025)
                    blended[ptype] = round(blended_usage, 1)
                blended_pitchers[name] = blended
            elif p26:
                blended_pitchers[name] = {ptype: round(p26.get(ptype, 0.0), 1) for ptype in pitch_types}
            elif p25:
                blended_pitchers[name] = {ptype: round(p25.get(ptype, 0.0), 1) for ptype in pitch_types}
                
        # 2. Blend Hitters
        blended_hitters = {}
        all_hitters = set(list(hitters_2026.keys()) + list(hitters_2025.keys()))
        for name in all_hitters:
            h26 = hitters_2026.get(name)
            h25 = hitters_2025.get(name)
            
            if h26 and h25:
                pa_2026 = h26.get("pa", 0)
                weight_2026 = min(1.0, pa_2026 / 100.0)
                
                blended = {}
                for ptype in pitch_types:
                    xwoba_2026 = h26.get(ptype, 0.0)
                    xwoba_2025 = h25.get(ptype, 0.0)
                    if xwoba_2026 > 0.0 and xwoba_2025 > 0.0:
                        blended_xw = (weight_2026 * xwoba_2026) + ((1.0 - weight_2026) * xwoba_2025)
                        blended[ptype] = round(blended_xw, 3)
                    elif xwoba_2026 > 0.0:
                        blended[ptype] = round(xwoba_2026, 3)
                    elif xwoba_2025 > 0.0:
                        blended[ptype] = round(xwoba_2025, 3)
                blended_hitters[name] = blended
            elif h26:
                blended_hitters[name] = {ptype: round(h26.get(ptype, 0.0), 3) for ptype in pitch_types if h26.get(ptype, 0.0) > 0.0}
            elif h25:
                blended_hitters[name] = {ptype: round(h25.get(ptype, 0.0), 3) for ptype in pitch_types if h25.get(ptype, 0.0) > 0.0}
                
        # 3. Build result structure
        import datetime
        today = datetime.date.today().isoformat()
        
        meta = {
            "last_refresh": today,
            "pitcher_count": len(blended_pitchers),
            "hitter_count": len(blended_hitters),
            "source": "baseball_savant_csv"
        }
        
        return {
            "meta": meta,
            "pitchers": blended_pitchers,
            "hitters": blended_hitters,
            "league_avg": league_avg
        }
    except Exception as e:
        print(f"[MATCHUP DNA ERROR]: Failed to build matchup data: {e}")
        raise
