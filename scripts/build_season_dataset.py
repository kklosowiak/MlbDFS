"""Join OMEGA lock-time slate snapshots to backfilled boxscore actuals -> flat CSVs for season analysis.

Snapshot rule (same as scripts/passive/signal_tracker.py): 2220UTC if it has teams, else 1530UTC.
Scoring uses the production functions calculate_hitter_dk_pts / calculate_pitcher_dk_pts.

Inputs : scratch/passive_tracker/slates/omega-results_<date>_<slot>UTC.json
         data/season_2026/actuals/actuals_<date>.json  (scripts/backfill_season_actuals.py)
Outputs: data/season_2026/dataset_hitters.csv | dataset_teams.csv | dataset_pitchers.csv
"""
import csv
import glob
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scripts.passive.signal_tracker import calculate_hitter_dk_pts, calculate_pitcher_dk_pts  # noqa: E402
from utils.normalization import normalize_player_name as norm  # noqa: E402

SLATES = os.path.join(ROOT, "scratch", "passive_tracker", "slates")
ACT = os.path.join(ROOT, "data", "season_2026", "actuals")
OUT = os.path.join(ROOT, "data", "season_2026")

H_FIELDS = ["player_score", "stack_adjusted_score", "physics_score", "market_score", "blended_rating", "attack_conf",
            "matchup_xwoba", "NPAS_xwOBA", "platoon_multiplier", "recent_ops", "season_ops", "recent_k_pct",
            "barrel_pct", "hard_hit_pct", "bullpen_fatigue", "ahr_price", "hits_line", "tb_line"]
H_FLAGS = ["is_hot", "is_juiced_target", "is_prop_juice", "is_speed_target", "is_pitch_alignment", "walks_boost",
           "strikeouts_penalty", "is_anti_chalk_smash", "smash_factor", "is_cold_streak_msmi", "is_hot_run_msmi",
           "is_cold_high_br_warning"]
H_CATS = ["platoon_label", "bat_side", "pitch_hand"]
T_FIELDS = ["stack_score", "stack_score_raw", "physics_score", "market_score", "attack_conf", "blended_rating",
            "stack_trust_score", "implied_total", "opening_total", "current_total", "divergence", "team_xwoba",
            "power_concentration", "bullpen_boost", "bullpen_fatigue", "vulnerability", "ml_move", "tt_move",
            "ticket_pct", "money_pct", "umpire_factor", "conf_delta", "prop_pressure_score"]
T_FLAGS = ["is_anti_chalk_smash", "is_blind_spot", "is_burst", "is_cold_streak", "is_cold_streak_msmi", "is_fade_risk",
           "is_fatigued", "is_gassed", "is_hot_run_msmi", "is_physics_override", "is_pinnacle_offense_boost",
           "is_pitch_alignment", "is_public_steam_trap", "is_shark", "is_sharp", "is_steam", "is_trap",
           "is_true_talent_penalty", "is_velocity_boost", "is_volatile"]
T_CATS = ["lineup_status", "weather_label", "trend", "prop_pressure_label", "total_signal"]
P_FIELDS = ["alpha_score", "physics_score", "market_score", "attack_conf", "blended_rating", "bm_score", "confidence",
            "csw", "siera", "dk_points_mean", "dk_points_std", "k_line", "outs_line", "er_line", "walks_line",
            "recent_era", "recent_k9", "recent_bb9", "ml_move", "tt_move", "umpire_factor", "true_talent_penalty",
            "walks_penalty"]
P_FLAGS = ["is_trap", "is_hazard", "is_low_ceiling", "is_high_variance", "is_volatile", "is_paradox", "is_sharp",
           "is_shark", "sharp_fade", "sticky_trap", "is_debut", "is_coors", "is_home", "is_confirmed",
           "is_juiced_target", "is_prop_juice", "is_outlier_driven"]
P_CATS = ["trap_type", "form_status", "pitch_hand", "weather_label"]


def load_lock(ds):
    for slot in ("2220", "1530"):
        p = os.path.join(SLATES, "omega-results_%s_%sUTC.json" % (ds, slot))
        if os.path.exists(p):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            if d.get("teams"):
                return d, slot
    return None, None


def flag(v):
    return 1 if v else 0


def build():
    acts = {}
    for f in glob.glob(os.path.join(ACT, "actuals_*.json")):
        ds = os.path.basename(f)[8:18]
        acts[ds] = json.load(open(f, encoding="utf-8"))
    dates = sorted({os.path.basename(f).split("_")[1] for f in glob.glob(os.path.join(SLATES, "omega-results_*.json"))})
    H, T, P = [], [], []
    stats = defaultdict(int)
    for ds in dates:
        games = [g for g in acts.get(ds, []) if g["status"] == "final"]
        if not games:
            stats["dates_no_final_games"] += 1
            continue
        lock, slot = load_lock(ds)
        if not lock:
            stats["dates_no_lock"] += 1
            continue
        stats["dates_used"] += 1
        by_team = defaultdict(list)  # team -> [(game, side)]
        for g in games:
            by_team[g["home_team"]].append((g, "home"))
            by_team[g["away_team"]].append((g, "away"))
        base = {"date": ds, "snap": slot}

        for t in lock["teams"]:
            tg = by_team.get(t["team"])
            if not tg:
                stats["team_no_game"] += 1
                continue
            dh = 1 if len(tg) > 1 else 0
            g, side = tg[0]  # first game of the day (DH rows are flagged and excluded downstream)
            runs = g["home_runs"] if side == "home" else g["away_runs"]
            opp_runs = g["away_runs"] if side == "home" else g["home_runs"]
            row = dict(base, team=t["team"], opponent=t.get("opponent"), opp_pitcher=t.get("opp_pitcher"), dh=dh,
                       game_type=g["game_type"], actual_runs=runs, opp_runs=opp_runs, is_home_team=flag(side == "home"))
            for k in T_FIELDS + T_CATS:
                row[k] = t.get(k)
            for k in T_FLAGS:
                row[k] = flag(t.get(k))
            T.append(row)
            stats["team_rows"] += 1

        for h in lock["hitters"]:
            tg = by_team.get(h["team"])
            if not tg:
                continue
            dh = 1 if len(tg) > 1 else 0
            nn = norm(h["name"])
            hit = None
            gid = None
            matched = "none"
            for g, side in tg:
                box = g["hitters_" + side]
                if nn in box:
                    hit, gid, matched = box[nn], g, "exact"
                    break
            if hit is None:
                for g, side in tg:
                    box = g["hitters_" + side]
                    c = [k for k in box if nn in k or k in nn]
                    if len(c) == 1:
                        hit, gid, matched = box[c[0]], g, "substr"
                        break
            g0 = gid or tg[0][0]
            row = dict(base, name=h["name"], team=h["team"], opponent=h.get("opponent"), dh=dh,
                       game_type=g0["game_type"], played=flag(hit is not None), match=matched,
                       actual_dk=calculate_hitter_dk_pts(hit) if hit else None,
                       actual_pa=hit["plate_appearances"] if hit else None,
                       actual_order=hit["batting_order"] if hit else None,
                       actual_starter=flag(hit and hit["is_starter"]), snap_order=h.get("batting_order"))
            for k in H_FIELDS + H_CATS:
                row[k] = h.get(k)
            for k in H_FLAGS:
                row[k] = flag(h.get(k))
            H.append(row)
            stats["hitter_rows"] += 1
            stats["hitter_match_" + matched] += 1

        for p in lock["pitchers"]:
            tg = by_team.get(p["team"])
            if not tg:
                continue
            dh = 1 if len(tg) > 1 else 0
            nn = norm(p["pitcher"])
            sp = None
            for g, side in tg:
                s = g["sp_" + side]
                sn = norm(s["name"])
                if sn == nn or (sn and (nn in sn or sn in nn)):
                    sp, g0 = s, g
                    break
            row = dict(base, pitcher=p["pitcher"], team=p["team"], opponent=p.get("opponent"), dh=dh,
                       game_type=tg[0][0]["game_type"], started=flag(sp is not None), actual_dk=calculate_pitcher_dk_pts(sp) if sp else None,
                       actual_ip=sp["ip"] if sp else None, actual_er=sp["er"] if sp else None,
                       actual_k=sp["k"] if sp else None)
            for k in P_FIELDS + P_CATS:
                row[k] = p.get(k)
            for k in P_FLAGS:
                row[k] = flag(p.get(k))
            P.append(row)
            stats["pitcher_rows"] += 1
            stats["pitcher_started"] += flag(sp is not None)

    for name, rows in (("dataset_hitters.csv", H), ("dataset_teams.csv", T), ("dataset_pitchers.csv", P)):
        cols = list(rows[0].keys())
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print("%s: %d rows, %d cols" % (name, len(rows), len(cols)))
    for k in sorted(stats):
        print("  %s = %d" % (k, stats[k]))


if __name__ == "__main__":
    build()
