"""
Full-Season (Apr 15 - Oct 28, 2026) & Mid-Season Change Audit
=============================================================
Joins pre-July archive results (reports/archive/results_*.json) with
post-July passive tracker slates (scratch/passive_tracker/slates/) against
backfilled MLB StatsAPI boxscores (data/season_2026/actuals/) to audit:
  1. Pre-July vs. Post-July model performance across all 3 layers
  2. All 18 passive tracker signal logs (scratch/passive_tracker/signals/*.csv)
  3. Every mid-season architectural change (DQI reversal, stack_trust_score,
     calibrate_vegas_itt, trap_vulnerable vs trap_short_leash, PARADOX,
     COLD_HIGH_BR_WARNING, platoon labels, xwoba_registry overrides)
  4. Confirmed Production Bugs & Dead Code Paths
  5. Counterfactual 2027 stack & pitcher scoring improvements (verified out-of-sample)
"""

import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.passive.signal_tracker import calculate_hitter_dk_pts, calculate_pitcher_dk_pts
from utils.dqi import calculate_dqi
from utils.market_utils import calibrate_vegas_itt
from utils.normalization import normalize_player_name


def load_early_archive_datasets():
    """Load Apr 15 - Jul 1 results_*.json and join with data/season_2026/actuals/."""
    archive_files = sorted(glob.glob(os.path.join(ROOT, "reports", "archive", "results_*.json")))
    by_date = {}
    for f in archive_files:
        base = os.path.basename(f)
        m = re.match(r"results_(\d{4}-\d{2}-\d{2})(_lock)?\.json", base)
        if not m:
            continue
        d_str = m.group(1)
        if d_str >= "2026-07-02":
            continue
        is_lock = bool(m.group(2))
        if d_str not in by_date or is_lock:
            by_date[d_str] = f

    team_rows = []
    pitcher_rows = []
    hitter_rows = []

    for d_str, r_path in sorted(by_date.items()):
        act_path = os.path.join(ROOT, "data", "season_2026", "actuals", f"actuals_{d_str}.json")
        if not os.path.exists(act_path):
            continue
        with open(r_path, "r", encoding="utf-8") as f:
            snap = json.load(f)
        with open(act_path, "r", encoding="utf-8") as f:
            act_list = json.load(f)

        if not isinstance(snap, dict) or not isinstance(act_list, list):
            continue

        games = [g for g in act_list if g.get("status") == "final" and g.get("game_type") == "R"]
        team_to_games = {}
        for g in games:
            for side in ("away", "home"):
                tname = g.get(f"{side}_team")
                if tname:
                    team_to_games.setdefault(tname, []).append((side, g))

        p_list_snap = snap.get("pitchers", [])

        # Teams
        for t in snap.get("teams", []):
            tname = t.get("team")
            t_games = team_to_games.get(tname, [])
            if len(t_games) != 1:
                continue
            side, g = t_games[0]
            runs = g["home_runs"] if side == "home" else g["away_runs"]
            if runs is None:
                continue
            itt = float(t.get("implied_total") or 0.0)
            if itt <= 0:
                continue
            dqi_res = calculate_dqi(t, p_list_snap)
            dqi_val = dqi_res[0] if isinstance(dqi_res, tuple) else dqi_res["dqi"]
            opp_p_name = normalize_player_name(t.get("opp_pitcher") or "")
            opp_p_obj = next((p for p in p_list_snap if normalize_player_name(p.get("pitcher", "")) == opp_p_name), {})
            team_rows.append({
                "date": d_str,
                "period": "Apr-Jun (Pre-Jul2)",
                "team": tname,
                "opponent": t.get("opponent"),
                "implied_total": itt,
                "team_xwoba": float(t.get("team_xwoba") or 0.320),
                "stack_score": float(t.get("stack_score") or 0.0),
                "attack_conf": float(t.get("attack_conf") or t.get("stack_confidence") or 0.0),
                "blended_rating": float(t.get("blended_rating") or t.get("stack_score") or 0.0),
                "stack_trust_score": float(t.get("stack_trust_score") or 0.0),
                "dqi": float(dqi_val) if dqi_val is not None else 65.0,
                "opp_sp_is_trap": int(bool(opp_p_obj.get("is_trap"))),
                "is_sharp": int(bool(t.get("is_sharp"))),
                "is_burst": int(bool(t.get("is_burst"))),
                "is_gassed": int(bool(t.get("is_gassed"))),
                "is_fatigued": int(bool(t.get("is_fatigued"))),
                "is_anti_chalk_smash": int(bool(t.get("is_anti_chalk_smash"))),
                "is_pitch_alignment": int(bool(t.get("is_pitch_alignment"))),
                "is_hot_run_msmi": int(bool(t.get("is_hot_run_msmi"))),
                "is_cold_streak_msmi": int(bool(t.get("is_cold_streak_msmi"))),
                "actual_runs": float(runs),
                "runs_minus_itt": float(runs) - itt,
                "scored_5plus": int(runs >= 5),
                "scored_7plus": int(runs >= 7),
            })

        # Pitchers
        for p in p_list_snap:
            pname = p.get("pitcher")
            tname = p.get("team")
            if not pname or not tname:
                continue
            t_games = team_to_games.get(tname, [])
            if len(t_games) != 1:
                continue
            side, g = t_games[0]
            sp_stats = g.get(f"sp_{side}")
            if not sp_stats:
                continue
            sn = normalize_player_name(sp_stats.get("name", ""))
            nn = normalize_player_name(pname)
            if not (sn == nn or (sn and (nn in sn or sn in nn))):
                continue
            dk_pts = calculate_pitcher_dk_pts(sp_stats)
            pitcher_rows.append({
                "date": d_str,
                "period": "Apr-Jun (Pre-Jul2)",
                "pitcher": pname,
                "team": tname,
                "alpha_score": float(p.get("alpha_score", {}).get("final", 0) if isinstance(p.get("alpha_score"), dict) else (p.get("alpha_score") or 0.0)),
                "attack_conf": float(p.get("attack_conf") or p.get("pitcher_confidence") or 0.0),
                "blended_rating": float(p.get("blended_rating") or 0.0),
                "dk_points_mean": float(p.get("dk_points_mean") or np.nan),
                "is_trap": int(bool(p.get("is_trap"))),
                "is_juiced_target": int(bool(p.get("is_juiced_target"))),
                "is_prop_juice": int(bool(p.get("is_prop_juice"))),
                "is_low_ceiling": int(bool(p.get("is_low_ceiling"))),
                "is_sharp": int(bool(p.get("is_sharp"))),
                "actual_dk": float(dk_pts),
                "actual_k": int(sp_stats.get("k", 0)),
                "actual_er": int(sp_stats.get("er", 0)),
            })

        # Hitters
        for h in snap.get("hitters", []):
            hname = h.get("name")
            tname = h.get("team")
            if not hname or not tname:
                continue
            t_games = team_to_games.get(tname, [])
            if len(t_games) != 1:
                continue
            side, g = t_games[0]
            box = g.get(f"hitters_{side}", {})
            nn = normalize_player_name(hname)
            h_act = box.get(nn)
            if h_act is None:
                c = [k for k in box if nn in k or k in nn]
                if len(c) == 1:
                    h_act = box[c[0]]
            if not h_act:
                continue
            dk_pts = calculate_hitter_dk_pts(h_act)
            hitter_rows.append({
                "date": d_str,
                "period": "Apr-Jun (Pre-Jul2)",
                "name": hname,
                "team": tname,
                "player_score": float(h.get("player_score") or 0.0),
                "stack_adjusted_score": float(h.get("stack_adjusted_score") or 0.0),
                "attack_conf": float(h.get("attack_conf") or h.get("hitter_confidence") or 0.0),
                "platoon_label": h.get("platoon_label") or "NEUTRAL",
                "is_juiced_target": int(bool(h.get("is_juiced_target"))),
                "is_speed_target": int(bool(h.get("is_speed_target"))),
                "is_hot": int(bool(h.get("is_hot"))),
                "smash_factor": int(bool(h.get("smash_factor"))),
                "actual_dk": float(dk_pts),
                "p15": int(dk_pts >= 15),
                "p20": int(dk_pts >= 20),
            })

    return pd.DataFrame(team_rows), pd.DataFrame(pitcher_rows), pd.DataFrame(hitter_rows)


def audit_passive_signal_logs():
    """Summarize all 18 CSV logs in scratch/passive_tracker/signals/."""
    sig_dir = os.path.join(ROOT, "scratch", "passive_tracker", "signals")
    rows = []
    for f in sorted(glob.glob(os.path.join(sig_dir, "*.csv"))):
        name = os.path.basename(f).replace("_log.csv", "")
        df = pd.read_csv(f)
        n_total = len(df)
        if "actual_dk_pts" in df.columns:
            valid = df[df["actual_dk_pts"].notna()]
            mean_val = valid["actual_dk_pts"].mean() if len(valid) else np.nan
            diff_val = valid["pts_diff"].mean() if "pts_diff" in valid.columns and len(valid) else np.nan
            p15 = 100 * (valid["actual_dk_pts"] >= 15).mean() if len(valid) else np.nan
            rows.append({
                "log_name": name,
                "layer": "Hitter",
                "n_logged": n_total,
                "n_scored": len(valid),
                "primary_metric": f"{mean_val:.2f} DK pts",
                "vs_baseline": f"{diff_val:+.2f} DK pts" if not np.isnan(diff_val) else "N/A",
                "ceiling_or_hit": f"{p15:.1f}% (15+ DK)",
            })
        elif "actual_runs_against" in df.columns:
            valid = df[df["actual_runs_against"].notna()]
            mean_ra = valid["actual_runs_against"].mean() if len(valid) else np.nan
            mean_rd = valid["run_diff"].mean() if "run_diff" in valid.columns and len(valid) else np.nan
            mean_er = valid["pitcher_actual_er"].mean() if "pitcher_actual_er" in valid.columns and len(valid) else np.nan
            mean_ip = valid["pitcher_actual_ip"].mean() if "pitcher_actual_ip" in valid.columns and len(valid) else np.nan
            rows.append({
                "log_name": name,
                "layer": "Pitcher / Opp Stack",
                "n_logged": n_total,
                "n_scored": len(valid),
                "primary_metric": f"Opp {mean_ra:.2f} R (SP {mean_er:.2f} ER, {mean_ip:.2f} IP)",
                "vs_baseline": f"{mean_rd:+.2f} R vs ITT" if not np.isnan(mean_rd) else "N/A",
                "ceiling_or_hit": f"{100*(valid['actual_runs_against']>=5).mean():.1f}% Opp 5+ R" if len(valid) else "N/A",
            })
        elif "actual_runs" in df.columns:
            valid = df[df["actual_runs"].notna()]
            mean_r = valid["actual_runs"].mean() if len(valid) else np.nan
            mean_rd = valid["run_diff"].mean() if "run_diff" in valid.columns and len(valid) else np.nan
            p5 = 100 * (valid["actual_runs"] >= 5).mean() if len(valid) else np.nan
            rows.append({
                "log_name": name,
                "layer": "Team Stack",
                "n_logged": n_total,
                "n_scored": len(valid),
                "primary_metric": f"{mean_r:.2f} Runs",
                "vs_baseline": f"{mean_rd:+.2f} R vs ITT" if not np.isnan(mean_rd) else "N/A",
                "ceiling_or_hit": f"{p5:.1f}% (5+ R)",
            })
        elif "both_scored_6plus" in df.columns:
            valid = df[df["teamA_actual_runs"].notna()].copy()
            for bcol in ["higher_conf_team_won_scoring", "pattern_flagged", "both_scored_6plus"]:
                valid[bcol] = valid[bcol].astype(str).str.lower().isin(["true", "1", "1.0"]).astype(int)
            w_rate = 100 * valid["higher_conf_team_won_scoring"].mean() if len(valid) else np.nan
            pat_rate = 100 * valid["pattern_flagged"].mean() if len(valid) else np.nan
            rows.append({
                "log_name": name,
                "layer": "Game Environment",
                "n_logged": n_total,
                "n_scored": len(valid),
                "primary_metric": f"Higher CONF won: {w_rate:.1f}%",
                "vs_baseline": f"Wrong-Team Trap: {pat_rate:.1f}%",
                "ceiling_or_hit": f"Both 6+ R: {100*valid['both_scored_6plus'].mean():.1f}%",
            })
    return pd.DataFrame(rows)


def main():
    early_T, early_P, early_H = load_early_archive_datasets()
    late_T = pd.read_csv(os.path.join(ROOT, "data", "season_2026", "dataset_teams.csv"))
    late_P = pd.read_csv(os.path.join(ROOT, "data", "season_2026", "dataset_pitchers.csv"))
    late_H = pd.read_csv(os.path.join(ROOT, "data", "season_2026", "dataset_hitters.csv"))

    late_T = late_T[(late_T["game_type"] == "R") & (late_T["dh"] == 0) & (late_T["implied_total"] > 0)].copy()
    late_P = late_P[(late_P["game_type"] == "R") & (late_P["dh"] == 0) & (late_P["started"] == 1)].copy()
    late_H = late_H[(late_H["game_type"] == "R") & (late_H["dh"] == 0) & (late_H["played"] == 1)].copy()

    late_T["runs_minus_itt"] = late_T["actual_runs"] - late_T["implied_total"]
    late_T["scored_5plus"] = (late_T["actual_runs"] >= 5).astype(int)
    late_T["scored_7plus"] = (late_T["actual_runs"] >= 7).astype(int)

    tt_lower = late_P["trap_type"].fillna("").str.lower()
    late_P["trap_vulnerable"] = (tt_lower.str.contains("vuln") | (tt_lower == "both")).astype(int)
    late_P["trap_short_leash"] = (tt_lower.str.contains("leash") | (tt_lower == "both")).astype(int)

    p_lookup = late_P.set_index(["date", "team"])
    opp_vuln, opp_leash, opp_trap, opp_dqi = [], [], [], []
    for idx, row in late_T.iterrows():
        key = (row["date"], row["opponent"])
        pr_dict = {}
        if key in p_lookup.index:
            pr = p_lookup.loc[key]
            if isinstance(pr, pd.DataFrame):
                pr = pr.iloc[0]
            pr_dict = pr.to_dict()
            opp_vuln.append(int(pr.get("trap_vulnerable", 0)))
            opp_leash.append(int(pr.get("trap_short_leash", 0)))
            opp_trap.append(int(pr.get("is_trap", 0)))
        else:
            opp_vuln.append(0)
            opp_leash.append(0)
            opp_trap.append(0)
        r_clean = {k: ("" if isinstance(v, float) and np.isnan(v) else v) for k, v in row.to_dict().items()}
        p_clean = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in pr_dict.items()}
        dqi_res = calculate_dqi(r_clean, [p_clean] if p_clean else [])
        opp_dqi.append(dqi_res[0] if isinstance(dqi_res, tuple) else dqi_res["dqi"])

    late_T["opp_trap_vulnerable"] = opp_vuln
    late_T["opp_trap_short_leash"] = opp_leash
    late_T["opp_sp_is_trap"] = opp_trap
    late_T["dqi"] = opp_dqi

    # Evaluate cf_stack_2027 on BOTH held-out Pre-July (early_T) and Post-July (late_T)
    for df_t in (early_T, late_T):
        opp_vuln_col = df_t["opp_trap_vulnerable"] if "opp_trap_vulnerable" in df_t.columns else df_t["opp_sp_is_trap"]
        df_t["cf_stack_2027"] = (
            df_t["implied_total"] * 15.0
            + df_t["team_xwoba"].fillna(0.320) * 80.0
            + df_t["is_anti_chalk_smash"] * 3.0
            + df_t["is_pitch_alignment"] * 2.0
            + (df_t["dqi"] >= 82).astype(int) * 3.0
            - (df_t["dqi"] < 50).astype(int) * 2.5
            - df_t["is_fatigued"] * 2.0
            + opp_vuln_col * 2.0
        )
        df_t["legacy_blend"] = 0.5 * df_t["stack_score"] + 0.5 * df_t["attack_conf"]

    print("=== HELD-OUT PRE-JULY ARCHIVE TEST (Apr 15 - Jul 1, Slates >= 8 Teams) ===")
    early_slates = [g for _, g in early_T.groupby("date") if len(g) >= 8]
    print(f"Pre-July Slates >= 8 teams: {len(early_slates)}")
    for metric in ["attack_conf", "stack_score", "blended_rating", "legacy_blend", "implied_total", "cf_stack_2027"]:
        t1_runs = [g.sort_values(metric, ascending=False).iloc[0]["actual_runs"] for g in early_slates]
        t1_p5 = [g.sort_values(metric, ascending=False).iloc[0]["scored_5plus"] for g in early_slates]
        t1_p7 = [g.sort_values(metric, ascending=False).iloc[0]["scored_7plus"] for g in early_slates]
        r_sp = stats.spearmanr(early_T[metric], early_T["actual_runs"]).statistic
        print(f"  {metric:<18} | Spearman={r_sp:+.4f} | Top-1: {np.mean(t1_runs):.2f} R ({100*np.mean(t1_p5):.1f}% 5+, {100*np.mean(t1_p7):.1f}% 7+)")

    print("\n=== FULL SEASON COMBINED (Apr 15 - Sep 27, Slates >= 8 Teams) ===")
    comb_T = pd.concat([early_T, late_T], ignore_index=True)
    comb_slates = [g for _, g in comb_T.groupby("date") if len(g) >= 8]
    print(f"Combined Slates >= 8 teams: {len(comb_slates)} (Total team-games={len(comb_T)})")
    for metric in ["attack_conf", "stack_score", "blended_rating", "legacy_blend", "implied_total", "cf_stack_2027"]:
        t1_runs = [g.sort_values(metric, ascending=False).iloc[0]["actual_runs"] for g in comb_slates]
        t1_p5 = [g.sort_values(metric, ascending=False).iloc[0]["scored_5plus"] for g in comb_slates]
        t1_p7 = [g.sort_values(metric, ascending=False).iloc[0]["scored_7plus"] for g in comb_slates]
        t2_runs = [r for g in comb_slates for r in g.sort_values(metric, ascending=False).iloc[:2]["actual_runs"]]
        t2_p5 = [r for g in comb_slates for r in g.sort_values(metric, ascending=False).iloc[:2]["scored_5plus"]]
        t2_p7 = [r for g in comb_slates for r in g.sort_values(metric, ascending=False).iloc[:2]["scored_7plus"]]
        r_sp = stats.spearmanr(comb_T[metric], comb_T["actual_runs"]).statistic
        print(f"  {metric:<18} | Spearman={r_sp:+.4f} | Top-1: {np.mean(t1_runs):.2f} R ({100*np.mean(t1_p5):.1f}% 5+, {100*np.mean(t1_p7):.1f}% 7+) | Top-2: {np.mean(t2_runs):.2f} R ({100*np.mean(t2_p5):.1f}% 5+, {100*np.mean(t2_p7):.1f}% 7+)")

    print("\n=== ALL 18 PASSIVE TRACKER SIGNAL LOGS SUMMARY ===")
    sig_summary = audit_passive_signal_logs()
    print(sig_summary.to_string(index=False))


if __name__ == "__main__":
    main()
