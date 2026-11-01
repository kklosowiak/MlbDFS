"""
Scrub All 197 Brain Conversations & Cross-Reference Winning Slates
==================================================================
Scans C:/Users/konra/.gemini/antigravity/brain/* (transcript.jsonl and *.md)
to catalog every MlbDFS conversation, extract user prompts, lineup builds,
model decisions, and cross-reference winning contest dates (Apr 9/10, Apr 29,
May 9/10, Jul 19, plus any other wins mentioned in chats).
"""

import glob
import json
import os
import re
from datetime import datetime

BRAIN_DIR = r"C:\Users\konra\.gemini\antigravity\brain"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT_CONV = "bfac6aa8-034e-4b29-a4d5-7a39566ace33"

MLB_KEYWORDS = [
    "omega", "mlbdfs", "draftkings", "stack", "pitcher", "hitter",
    "xwoba", "dqi", "bogaerts", "slate", "lineup", "vegas", "itt",
    "statcast", "platoon", "bullpen", "single entry", "gpp"
]

WIN_KEYWORDS = [
    "won", "1st place", "first place", "2nd place", "3rd place", "4th place",
    "cashed", "bink", "20k", "20,000", "5,000", "5k", "2,600", "1,500", "1,600",
    "bogaerts", "grand slam", "granny", "battery", "relay throw", "bat flip"
]


def parse_conversations():
    conv_dirs = sorted([
        d for d in os.listdir(BRAIN_DIR)
        if os.path.isdir(os.path.join(BRAIN_DIR, d)) and d != CURRENT_CONV
    ])

    conversations = []
    win_mentions = []
    target_date_chats = []

    for cid in conv_dirs:
        cpath = os.path.join(BRAIN_DIR, cid)
        tpath = os.path.join(cpath, ".system_generated", "logs", "transcript.jsonl")
        md_files = glob.glob(os.path.join(cpath, "*.md"))

        user_inputs = []
        planner_texts = []
        created_first = None
        created_last = None

        if os.path.exists(tpath):
            try:
                with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        ts = obj.get("created_at")
                        if ts:
                            if not created_first or ts < created_first:
                                created_first = ts
                            if not created_last or ts > created_last:
                                created_last = ts
                        stype = obj.get("type")
                        content = str(obj.get("content") or "")
                        if stype == "USER_INPUT" and content:
                            # Strip tags if present
                            clean_c = re.sub(r"<[^>]+>", "", content).strip()
                            if clean_c:
                                user_inputs.append((ts or "", clean_c))
                        elif stype == "PLANNER_RESPONSE" and content:
                            planner_texts.append((ts or "", content))
            except Exception:
                pass

        md_contents = {}
        for mf in md_files:
            mname = os.path.basename(mf)
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    md_contents[mname] = f.read()
            except Exception:
                pass
            if not created_first:
                mtime = os.path.getmtime(mf)
                dt_str = datetime.fromtimestamp(mtime).isoformat()
                created_first = dt_str
                created_last = dt_str

        full_blob = (
            " ".join(u[1] for u in user_inputs)
            + " "
            + " ".join(p[1] for p in planner_texts)
            + " "
            + " ".join(md_contents.values())
        ).lower()

        is_mlb = any(k in full_blob for k in MLB_KEYWORDS)
        if not is_mlb:
            continue

        date_prefix = (created_first or "unknown")[:10]
        conversations.append({
            "cid": cid,
            "date_start": (created_first or "")[:19],
            "date_end": (created_last or "")[:19],
            "date_day": date_prefix,
            "n_user_msgs": len(user_inputs),
            "n_planner_msgs": len(planner_texts),
            "md_files": list(md_contents.keys()),
            "first_user_msg": user_inputs[0][1][:220].replace("\n", " ") if user_inputs else "(Artifact-only session)",
            "user_inputs": user_inputs,
            "planner_texts": planner_texts,
            "md_contents": md_contents,
        })

        # Check for win keywords in user inputs
        for ts, u_txt in user_inputs:
            u_low = u_txt.lower()
            if any(wk in u_low for wk in WIN_KEYWORDS):
                win_mentions.append({
                    "cid": cid,
                    "ts": ts[:19],
                    "text": u_txt[:400].replace("\n", " "),
                })

        # Check if conversation falls near our 4 screenshot dates:
        # Apr 9-11, Apr 28-30, May 9-11, Jul 18-20
        for target_prefix in ("2026-04-09", "2026-04-10", "2026-04-11",
                              "2026-04-28", "2026-04-29", "2026-04-30",
                              "2026-05-09", "2026-05-10", "2026-05-11",
                              "2026-07-18", "2026-07-19", "2026-07-20"):
            if target_prefix in (created_first or "") or target_prefix in (created_last or "") or target_prefix in full_blob:
                target_date_chats.append((target_prefix, cid, (created_first or "")[:19], len(user_inputs), list(md_contents.keys())))
                break

    conversations.sort(key=lambda x: x["date_start"])
    return conversations, win_mentions, target_date_chats


def main():
    convs, wins, target_chats = parse_conversations()
    print(f"Total MlbDFS Conversations Found: {len(convs)}")
    print(f"Total User Messages Across All MlbDFS Chats: {sum(c['n_user_msgs'] for c in convs)}")
    print(f"Total Artifact Markdown Files in MlbDFS Chats: {sum(len(c['md_files']) for c in convs)}")

    # Group by month
    by_month = {}
    for c in convs:
        m = c["date_day"][:7]
        by_month[m] = by_month.get(m, 0) + 1
    print("Conversations by Month:", by_month)

    print("\n=== CONVERSATIONS MATCHING WIN SCREENSHOT DATES (Apr 9/10, Apr 29, May 9/10, Jul 19) ===")
    for tp, cid, ds, n_u, mds in sorted(target_chats):
        print(f"  [{tp}] conv={cid} | started={ds} | user_msgs={n_u} | artifacts={mds}")

    print(f"\n=== USER MESSAGES MENTIONING WINS / CONTEST RESULTS ({len(wins)} found) ===")
    for w in wins[:35]:
        print(f"  [{w['ts']}] ({w['cid'][:8]}): {w['text']}")

    # Save full structured index for deeper inspection
    out_summary = []
    for c in convs:
        out_summary.append({
            "cid": c["cid"],
            "date_start": c["date_start"],
            "date_end": c["date_end"],
            "n_user_msgs": c["n_user_msgs"],
            "md_files": c["md_files"],
            "first_user_msg": c["first_user_msg"],
        })
    os.makedirs(os.path.join(ROOT, "data", "season_2026"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "season_2026", "chat_history_index.json"), "w", encoding="utf-8") as f:
        json.dump(out_summary, f, indent=2)
    print("\nSaved data/season_2026/chat_history_index.json")


if __name__ == "__main__":
    main()
