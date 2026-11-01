import io
import json
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BRAIN_DIR = pathlib.Path(r"C:\Users\konra\.gemini\antigravity\brain")
INDEX_PATH = pathlib.Path("data/season_2026/chat_history_index.json")

idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

target_prefixes = (
    "2026-04-09", "2026-04-10",
    "2026-04-29", "2026-04-30",
    "2026-05-09", "2026-05-10",
    "2026-07-17", "2026-07-18", "2026-07-19", "2026-07-20",
)

print("=== PART 1: ALL USER MESSAGES ACROSS 162 CHATS MENTIONING WINS / CASHES / RESULTS / LINEUPS ===")
win_kw = re.compile(r"\b(won|win|1st|first place|2nd|3rd|cash|cashed|bogaerts|granny|grand slam|20k|5k|battery|gpp|single entry|crushed|bink|binked|took down|205\.25|147\.2|137\.8|222\.45)\b", re.I)

for c in idx:
    cid = c["cid"]
    t_path = BRAIN_DIR / cid / ".system_generated" / "logs" / "transcript.jsonl"
    if not t_path.exists():
        continue
    with open(t_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") == "USER_INPUT" and isinstance(obj.get("content"), str):
                m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", obj["content"], re.S)
                txt = m.group(1).strip() if m else obj["content"].strip()
                txt_one = " ".join(txt.split())
                if win_kw.search(txt_one):
                    print(f"[{obj.get('created_at', '')[:16]} | {cid[:8]}] USER: {txt_one[:320]}")

print("\n=== PART 2: CHATS ON WINNING DATES (APR 9-10, APR 29-30, MAY 9-10, JUL 17-20) ===")
for c in idx:
    dt = (c.get("date_start") or "")[:10]
    ldt = (c.get("date_end") or "")[:10]
    if dt in target_prefixes or ldt in target_prefixes:
        cid = c["cid"]
        print(f"\n------------------------------------------")
        print(f"CHAT {cid[:8]} | {c['date_start']} -> {c['date_end']} | User Msgs: {c['n_user_msgs']} | Files: {c['md_files']}")
        t_path = BRAIN_DIR / cid / ".system_generated" / "logs" / "transcript.jsonl"
        if t_path.exists():
            with open(t_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    t = obj.get("type", "")
                    ts = obj.get("created_at", "")
                    content = obj.get("content", "")
                    if t == "USER_INPUT" and isinstance(content, str):
                        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.S)
                        txt = m.group(1).strip() if m else content.strip()
                        txt_one = " ".join(txt.split())
                        print(f"  [{ts[:16]}] USER: {txt_one[:280]}")
                    elif t == "PLANNER_RESPONSE" and isinstance(content, str) and content.strip():
                        txt_one = " ".join(content.strip().split())
                        if any(k in txt_one.lower() for k in ["lineup", "stack", "bogaerts", "padres", "nationals", "ashcraft", "skenes", "yamamoto", "goodman", "cincinnati", "colorado", "tier 1", "sp1", "sp2", "conviction"]):
                            print(f"  [{ts[:16]}] AGENT: {txt_one[:320]}")
