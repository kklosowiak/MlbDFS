"""
Batted-Ball Profile Backtest
============================
Tests whether the hitter_confidence.py rule:
    barrel_pct >= 12.0 AND hard_hit_pct >= 45.0 -> +8 CONF

...actually predicts superior fantasy performance.

Cross-references:
  - data/statcast_cache.json          -> barrel_pct, hard_hit_pct per player
  - reports/archive/actuals_cache_*.json -> daily hits, HR, RBI per player

Usage:
    python scripts/backtest_batted_ball.py
"""

import json
import os
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils.normalization import normalize_player_name

STATCAST_PATH = os.path.join(ROOT, "data", "statcast_cache.json")
ARCHIVE_DIR   = os.path.join(ROOT, "reports", "archive")

# DK fantasy scoring (approximate — singles 3pt, HR 10pt, RBI 2pt, R 2pt)
def dk_score(hits, hr, rbi, runs=0):
    singles = max(0, hits - hr)
    return (singles * 3.0) + (hr * 10.0) + (rbi * 2.0) + (runs * 2.0)


def load_statcast():
    """Load barrel_pct and hard_hit_pct for every hitter in statcast cache."""
    with open(STATCAST_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    profiles = {}
    for name, data in raw.items():
        if data.get("type") != "hitter":
            continue
        barrel = float(data.get("barrel_pct") or 0)
        hard   = float(data.get("hard_hit_pct") or 0)
        if barrel > 0 or hard > 0:
            profiles[normalize_player_name(name)] = {
                "barrel_pct":   barrel,
                "hard_hit_pct": hard,
            }
    return profiles


def load_actuals():
    """Returns dict: {player_norm: [{hits, hr, rbi, date}, ...]}"""
    player_games = {}
    pattern = os.path.join(ARCHIVE_DIR, "actuals_cache_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"[WARNING] No actuals_cache_*.json files found in {ARCHIVE_DIR}")
    for path in files:
        date_str = os.path.basename(path).replace("actuals_cache_", "").replace(".json", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # actuals format: {team_name: {hitters: {player: {hits, hr, rbi}}}}
        for team_data in data.values():
            if not isinstance(team_data, dict):
                continue
            hitters = team_data.get("hitters", {})
            if not isinstance(hitters, dict):
                continue
            for raw_name, stats in hitters.items():
                if not isinstance(stats, dict):
                    continue
                norm = normalize_player_name(raw_name)
                game = {
                    "hits": int(stats.get("hits") or 0),
                    "hr":   int(stats.get("hr")   or 0),
                    "rbi":  int(stats.get("rbi")  or 0),
                    "date": date_str,
                }
                player_games.setdefault(norm, []).append(game)
    return player_games


def classify(barrel, hard, b_thresh, h_thresh):
    elite      = barrel >= b_thresh and hard >= h_thresh
    barrel_only = barrel >= b_thresh and not elite
    hard_only   = hard >= h_thresh and not elite
    if elite:       return "ELITE"
    if barrel_only: return "BARREL_ONLY"
    if hard_only:   return "HARD_ONLY"
    return "BASELINE"


def run_backtest(b_thresh=12.0, h_thresh=45.0):
    print(f"\n{'='*62}")
    print(f"  Batted-Ball Backtest  |  Barrel>={b_thresh}%  AND  HardHit>={h_thresh}%")
    print(f"{'='*62}")

    profiles  = load_statcast()
    all_games = load_actuals()

    tiers = {"ELITE": [], "BARREL_ONLY": [], "HARD_ONLY": [], "BASELINE": []}
    matched = 0

    for norm_name, games in all_games.items():
        profile = profiles.get(norm_name)
        if not profile:
            continue
        matched += 1
        tier = classify(profile["barrel_pct"], profile["hard_hit_pct"], b_thresh, h_thresh)
        for g in games:
            score = dk_score(g["hits"], g["hr"], g["rbi"])
            tiers[tier].append({
                "score":   score,
                "hits":    g["hits"],
                "hr":      g["hr"],
                "rbi":     g["rbi"],
                "has_hit": g["hits"] >= 1,
                "has_xbh": g["hr"] >= 1 or g["hits"] >= 2,
            })

    print(f"\n  Players matched to Statcast profiles : {matched:,}")
    print(f"  Total player-game observations       : {sum(len(v) for v in tiers.values()):,}\n")

    rows = []
    for tier, games in tiers.items():
        if not games:
            continue
        n       = len(games)
        avg_dk  = sum(g["score"] for g in games) / n
        hit_rt  = sum(1 for g in games if g["has_hit"]) / n * 100
        xbh_rt  = sum(1 for g in games if g["has_xbh"]) / n * 100
        avg_hr  = sum(g["hr"]   for g in games) / n
        avg_hit = sum(g["hits"] for g in games) / n
        rows.append((tier, n, avg_dk, hit_rt, xbh_rt, avg_hr, avg_hit))

    header = f"  {'Tier':<14} {'N':>7} {'AvgDK':>8} {'Hit%':>7} {'XBH%':>7} {'HR/G':>7} {'H/G':>6}"
    print(header)
    print("  " + "-" * 58)
    for tier, n, avg_dk, hit_rt, xbh_rt, avg_hr, avg_hit in sorted(rows, key=lambda x: -x[2]):
        print(f"  {tier:<14} {n:>7,} {avg_dk:>8.2f} {hit_rt:>6.1f}% {xbh_rt:>6.1f}% {avg_hr:>7.3f} {avg_hit:>6.2f}")

    # Calibration recommendation
    elite_row    = next((r for r in rows if r[0] == "ELITE"),    None)
    baseline_row = next((r for r in rows if r[0] == "BASELINE"), None)
    if elite_row and baseline_row:
        delta_dk = elite_row[2] - baseline_row[2]
        pct_lift = (delta_dk / max(0.01, baseline_row[2])) * 100
        # Map DK score delta to CONF point delta (rough calibration: 1 DK pt ~ 2.5 CONF pts)
        suggested_boost = max(0, round(delta_dk * 2.5))
        print(f"\n  Calibration Summary (barrel>={b_thresh}% AND hard>={h_thresh}%)")
        print(f"  {'ELITE vs BASELINE avg DK delta':<36}: {delta_dk:+.2f} pts/game")
        print(f"  {'Lift over baseline':<36}: {pct_lift:+.1f}%")
        print(f"  {'Current CONF boost in model':<36}: +8")
        print(f"  {'Suggested CONF boost':<36}: {'+' if suggested_boost >= 0 else ''}{suggested_boost}")
        if abs(suggested_boost - 8) <= 2:
            print(f"  VERDICT: Current +8 boost is well-calibrated.")
        elif suggested_boost > 8:
            print(f"  VERDICT: Consider RAISING boost to +{suggested_boost}.")
        else:
            print(f"  VERDICT: Consider LOWERING boost to +{max(1, suggested_boost)}.")

    return rows


def sweep_thresholds():
    """Test multiple barrel%/hard_hit% gate combinations to find the optimal pair."""
    print(f"\n{'='*62}")
    print("  THRESHOLD SWEEP -- Finding Optimal Gates")
    print(f"{'='*62}")

    profiles  = load_statcast()
    all_games = load_actuals()

    flat = []
    for norm_name, games in all_games.items():
        profile = profiles.get(norm_name)
        if not profile:
            continue
        for g in games:
            flat.append({
                "barrel_pct":   profile["barrel_pct"],
                "hard_hit_pct": profile["hard_hit_pct"],
                "dk_score":     dk_score(g["hits"], g["hr"], g["rbi"]),
            })

    if not flat:
        print("  No matched observations. Ensure actuals_cache files exist in reports/archive/")
        return

    baseline_avg = sum(r["dk_score"] for r in flat) / len(flat)
    print(f"\n  Baseline avg DK score (all hitters): {baseline_avg:.2f} pts/game")
    print(f"\n  {'Barrel>=':>9} {'Hard>=':>7} {'N':>7} {'AvgDK':>8} {'Delta':>8} {'HitAny%':>8}")
    print("  " + "-"*55)

    best = None
    for b in [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]:
        for h in [40.0, 42.0, 44.0, 45.0, 47.0, 50.0]:
            elite = [r for r in flat if r["barrel_pct"] >= b and r["hard_hit_pct"] >= h]
            if len(elite) < 20:
                continue
            avg   = sum(r["dk_score"] for r in elite) / len(elite)
            delta = avg - baseline_avg
            hit_rt = sum(1 for r in elite if r["dk_score"] > 0) / len(elite) * 100
            print(f"  {b:>9.1f}% {h:>7.1f}% {len(elite):>7,} {avg:>8.2f} {delta:>+8.2f} {hit_rt:>7.1f}%")
            if best is None or delta > best[2]:
                best = (b, h, delta)

    if best:
        print(f"\n  Best gate found: Barrel>={best[0]}% AND HardHit>={best[1]}%  (delta: {best[2]:+.2f} DK pts)")


if __name__ == "__main__":
    run_backtest(b_thresh=12.0, h_thresh=45.0)
    sweep_thresholds()
