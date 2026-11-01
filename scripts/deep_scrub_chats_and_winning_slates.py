"""
Deep Scrub of All 162 MlbDFS Conversations & Winning Slate Reconstruction
=========================================================================
1. Inspects all 162 MlbDFS conversations (98 transcripts + 445 markdown artifacts)
   in C:/Users/konra/.gemini/antigravity/brain/.
2. Reconstructs the 4 confirmed big wins from user screenshots:
   - Win 1: April 9, 2026 Night Slate (Screenshot Apr 10 7:33 AM) - 1st Place $20,000 (147.20 FPTS, Bogaerts Grand Slam vs COL)
   - Win 2: April 29, 2026 Slate (Screenshot Apr 29 11:01 PM) - 1st Place $5,000 (205.25 FPTS, $121 SE Battery)
   - Win 3: May 9, 2026 Slate (Screenshot May 10 9:39 AM) - 2nd Place $2,600 (137.80 FPTS, $121 SE Battery)
   - Win 4: July 19, 2026 Slate (Screenshot Jul 19 6:56 PM) - 4th Place $1,500 + 74th $100 = $1,600 (222.45 FPTS, $121 SE Battery + $18 Bat Flip)
3. Extracts every lineup, post-mortem, and model architecture decision across all 162 chats
   and cross-references them against full-season empirical performance.
"""

import glob
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BRAIN_DIR = r"C:\Users\konra\.gemini\antigravity\brain"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.passive.signal_tracker import calculate_hitter_dk_pts, calculate_pitcher_dk_pts
from utils.normalization import normalize_player_name


def inspect_winning_date_boxscores(date_str):
    """Return top-scoring teams, pitchers, and hitters on a winning date."""
    act_path = os.path.join(ROOT, "data", "season_2026", "actuals", f"actuals_{date_str}.json")
    if not os.path.exists(act_path):
        return None
    games = json.load(open(act_path, "r", encoding="utf-8"))
    team_scores = []
    sp_scores = []
    hitter_scores = []
    for g in games:
        if g.get("status") != "final":
            continue
        for side, opp_side in (("home", "away"), ("away", "home")):
            tname = g.get(f"{side}_team")
            opp = g.get(f"{opp_side}_team")
            runs = g.get(f"{side}_runs", 0)
            team_scores.append((runs, tname, opp, g.get("commence_time", "")))
            sp = g.get(f"sp_{side}")
            if sp and sp.get("name"):
                pts = calculate_pitcher_dk_pts(sp)
                sp_scores.append((pts, sp["name"], tname, opp, sp.get("ip"), sp.get("k"), sp.get("er"), sp.get("win")))
            for k, h in g.get(f"hitters_{side}", {}).items():
                hpts = calculate_hitter_dk_pts(h)
                hitter_scores.append((hpts, h.get("name"), tname, opp, h.get("hr", 0), h.get("rbi", 0), h.get("runs_scored", 0), h.get("stolen_bases", 0), h.get("hits", 0)))
    team_scores.sort(reverse=True)
    sp_scores.sort(reverse=True)
    hitter_scores.sort(reverse=True)
    return {
        "teams": team_scores[:8],
        "sps": sp_scores[:10],
        "hitters": hitter_scores[:15],
    }


def inspect_model_predictions_for_date(date_str):
    """Check reports/archive/results_<date>*.json or passive tracker slates."""
    candidates = [
        os.path.join(ROOT, "reports", "archive", f"results_{date_str}_lock.json"),
        os.path.join(ROOT, "reports", "archive", f"results_{date_str}.json"),
        os.path.join(ROOT, "scratch", "passive_tracker", "slates", f"omega-results_{date_str}_2220UTC.json"),
        os.path.join(ROOT, "scratch", "passive_tracker", "slates", f"omega-results_{date_str}_1530UTC.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                d = json.load(open(c, "r", encoding="utf-8"))
                if isinstance(d, dict) and d.get("teams"):
                    return os.path.basename(c), d
            except Exception:
                pass
    return None, None


def find_conversations_around_dates():
    """Find all conversations and artifacts created on or discussing the 4 win dates."""
    index_path = os.path.join(ROOT, "data", "season_2026", "chat_history_index.json")
    convs = json.load(open(index_path, "r", encoding="utf-8"))

    print("=== CHRONOLOGICAL BREAKDOWN OF ALL 162 MLBDFS CHATS ===")
    # Categorize all 162 chats by topic / phase
    categories = defaultdict(list)
    lineup_chats = []
    postmortem_chats = []
    version_mentions = defaultdict(set)

    for c in convs:
        cid = c["cid"]
        cpath = os.path.join(BRAIN_DIR, cid)
        tpath = os.path.join(cpath, ".system_generated", "logs", "transcript.jsonl")
        md_files = glob.glob(os.path.join(cpath, "*.md"))

        all_user_text = []
        all_planner_text = []
        if os.path.exists(tpath):
            with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    st = obj.get("type")
                    cnt = str(obj.get("content") or "")
                    if st == "USER_INPUT":
                        clean = re.sub(r"<[^>]+>", "", cnt).strip()
                        if clean:
                            all_user_text.append(clean)
                    elif st == "PLANNER_RESPONSE" and cnt:
                        all_planner_text.append(cnt)

        md_text = ""
        for mf in md_files:
            try:
                md_text += "\n" + open(mf, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                pass

        combined = ("\n".join(all_user_text) + "\n" + md_text)
        comb_low = combined.lower()

        # Find version tags (e.g. v4.5, v6.2, v12.1, v17.3, v20.1)
        for vm in re.findall(r"\bv(\d+\.\d+(?:\.\d+)?)\b", comb_low):
            major = int(vm.split(".")[0])
            if 3 <= major <= 25:
                version_mentions[f"v{vm}"].add(c["date_start"][:10] or "early")

        # Classify chat
        if any(w in comb_low for w in ["lineup #1", "sp1:", "dksalaries", "single entry", "lock:", "stack lock"]):
            categories["Slate Lineup Construction & Optimizer Runs"].append(c)
            lineup_chats.append((c["date_start"][:10], cid, c["n_user_msgs"], c["md_files"], c["first_user_msg"]))
        if any(w in comb_low for w in ["post-mortem", "post_mortem", "backtest", "audit", "feedback loop", "validator"]):
            categories["Post-Mortem Audits & Backtesting"].append(c)
            postmortem_chats.append((c["date_start"][:10], cid, c["n_user_msgs"], c["md_files"], c["first_user_msg"]))
        if any(w in comb_low for w in ["dqi", "decision quality", "stack_trust_score", "gpp_leverage"]):
            categories["DQI & Stack Decision Layer Engineering"].append(c)
        if any(w in comb_low for w in ["pitcher_trap", "trap_vulnerable", "short_leash", "opener_detector", "paradox"]):
            categories["Pitcher Trap, Opener & Paradox Engineering"].append(c)
        if any(w in comb_low for w in ["platoon", "matchup_radar", "savant", "xwoba", "statcast", "msmi"]):
            categories["Statcast, Platoon Splits, Matchup DNA & MSMI"].append(c)
        if any(w in comb_low for w in ["consensus", "scoresandodds", "whale", "shark", "steam", "opening_lines", "pinnacle"]):
            categories["Sharp Market, Consensus Splits & Opening Lines"].append(c)
        if any(w in comb_low for w in ["propfinder", "weather", "roth", "umpire", "lineup_fetcher", "rotowire"]):
            categories["Scrapers (Weather, Lineups, Umpires, Props)"].append(c)

    for cat, clist in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  - {cat:<48}: {len(clist):>3} conversations")

    return categories, lineup_chats, postmortem_chats, version_mentions


def inspect_specific_win_chats():
    """Print detailed artifacts and chat excerpts for Apr 9/10, Apr 29, May 9/10, Jul 19."""
    win_dates = [
        ("2026-04-09", "Win #1: $20,000 1st Place (MLB $80K Relay Throw Night - 147.20 FPTS, Bogaerts Grand Slam vs COL)"),
        ("2026-04-29", "Win #2: $5,000 1st Place (MLB $50K Battery Single Entry $121 - 205.25 FPTS)"),
        ("2026-05-09", "Win #3: $2,600 2nd Place (MLB $30K Battery Single Entry $121 - 137.80 FPTS)"),
        ("2026-07-19", "Win #4: $1,600 4th Place (MLB $30K Battery SE $1,500 + $150K Bat Flip $100 - 222.45 FPTS)"),
    ]

    for d_str, title in win_dates:
        print(f"\n======================================================================")
        print(f"  {title}")
        print(f"======================================================================")
        box = inspect_winning_date_boxscores(d_str)
        if box:
            print(f"  [ACTUAL BOXSCORE TOP TEAMS ON {d_str}]:")
            for runs, tname, opp, ct in box["teams"][:6]:
                print(f"    - {tname:<24} vs {opp:<24}: {runs} Runs ({ct})")
            print(f"  [ACTUAL BOXSCORE TOP PITCHERS ON {d_str}]:")
            for pts, pname, tname, opp, ip, k, er, win in box["sps"][:6]:
                print(f"    - {pname:<22} ({tname:<20} vs {opp:<20}): {pts:>5.1f} DK pts ({ip} IP, {k} K, {er} ER, W={win})")
            print(f"  [ACTUAL BOXSCORE TOP HITTERS ON {d_str}]:")
            for hpts, hname, tname, opp, hr, rbi, r, sb, h in box["hitters"][:8]:
                print(f"    - {hname:<22} ({tname:<20} vs {opp:<20}): {hpts:>5.1f} DK pts ({h} H, {hr} HR, {rbi} RBI, {r} R, {sb} SB)")

        snap_name, snap = inspect_model_predictions_for_date(d_str)
        if snap:
            print(f"\n  [OMEGA MODEL PROJECTIONS ON {d_str} ({snap_name})]:")
            teams_sorted = sorted(snap.get("teams", []), key=lambda x: float(x.get("blended_rating") or x.get("stack_score") or 0), reverse=True)
            print("    Top 5 Projected Stacks:")
            for idx, t in enumerate(teams_sorted[:5], 1):
                print(f"      #{idx}: {t.get('team'):<22} vs {str(t.get('opp_pitcher')):<18} | StackScore={t.get('stack_score')} | CONF={t.get('attack_conf')} | Blend={t.get('blended_rating')} | ITT={t.get('implied_total')}")
            ps_sorted = sorted(snap.get("pitchers", []), key=lambda x: float(x.get("blended_rating") or (x.get("alpha_score",{}).get("final",0) if isinstance(x.get("alpha_score"),dict) else x.get("alpha_score") or 0)), reverse=True)
            print("    Top 5 Projected Pitchers:")
            for idx, p in enumerate(ps_sorted[:5], 1):
                alp = p.get("alpha_score", {}).get("final") if isinstance(p.get("alpha_score"), dict) else p.get("alpha_score")
                print(f"      #{idx}: {p.get('pitcher'):<22} ({p.get('team'):<20}) | Alpha={alp} | CONF={p.get('attack_conf')} | Blend={p.get('blended_rating')} | K_Line={p.get('k_line')}")


def inspect_chat_artifacts_for_win_dates():
    """Read the exact markdown artifacts created on Apr 9, Apr 29, May 9/10, and Jul 19."""
    print("\n======================================================================")
    print("  ARTIFACTS & CHATS FROM THE 4 WINNING SLATES")
    print("======================================================================")
    target_cids = [
        ("2026-04-09 ($20K Win)", "a104160c-3e01-4d45-b644-da003076123a"),
        ("2026-04-09 ($20K Win)", "261bf836-50ca-4522-a102-26dd30af8dbd"),
        ("2026-04-10 (Morning After $20K Win)", "68dcbec0-37db-4a61-b39a-4f249564eefa"),
        ("2026-04-28/29 ($5K Win)", "481bcf1c-82b8-4d74-a008-a6b10bfe9875"),
        ("2026-04-29 ($5K Win)", "57cf1293-6076-4e55-bbb1-3b5fb750d06b"),
        ("2026-04-29 ($5K Win)", "3617a4be-f26d-4264-95ec-10f965ffe729"),
        ("2026-04-29 ($5K Win)", "f4868e21-894f-4b2b-8b0e-e71fdcd40f50"),
        ("2026-05-09 ($2.6K Win)", "27a5fdb8-f38b-4a54-b417-faa4ffc82ca2"),
        ("2026-05-10 (Morning After $2.6K Win)", "52a22027-049d-449f-a2ee-c8a0cf593a29"),
        ("2026-05-10 (White Paper)", "609676c0-4210-40d7-9446-ed68b782f855"),
    ]
    for label, cid in target_cids:
        cpath = os.path.join(BRAIN_DIR, cid)
        if not os.path.exists(cpath):
            continue
        for fn in sorted(os.listdir(cpath)):
            if fn.endswith(".md"):
                txt = open(os.path.join(cpath, fn), "r", encoding="utf-8", errors="ignore").read()
                print(f"\n--- [{label}] {cid[:8]} / {fn} (len={len(txt)}) ---")
                print(txt[:1800])


if __name__ == "__main__":
    find_conversations_around_dates()
    inspect_specific_win_chats()
    inspect_chat_artifacts_for_win_dates()
