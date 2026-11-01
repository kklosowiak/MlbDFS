import ast
import io
import json
import pathlib
import re
import sqlite3
import sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = pathlib.Path(r"C:\Users\konra\.gemini\antigravity\conversation_summaries.db")
PB_DIR = pathlib.Path(r"C:\Users\konra\.gemini\antigravity\conversations")
BRAIN_DIR = pathlib.Path(r"C:\Users\konra\.gemini\antigravity\brain")

con = sqlite3.connect(str(DB_PATH))
cur = con.cursor()

# Get all MlbDFS conversation_ids from both conversation_summaries and conversations_fts
cids_fts = {
    r[0] for r in cur.execute("SELECT DISTINCT conversation_id FROM conversations_fts WHERE workspace = 'MlbDFS'").fetchall()
}
cids_sum = {
    r[0] for r in cur.execute("SELECT conversation_id FROM conversation_summaries WHERE workspace_uris LIKE '%MlbDFS%'").fetchall()
}
all_mlb_cids = (cids_fts | cids_sum) - {"bfac6aa8-034e-4b29-a4d5-7a39566ace33"}
print(f"FTS MlbDFS CIDs (excl current): {len(cids_fts - {'bfac6aa8-034e-4b29-a4d5-7a39566ace33'})} | Summary DB MlbDFS CIDs: {len(cids_sum - {'bfac6aa8-034e-4b29-a4d5-7a39566ace33'})} | Union: {len(all_mlb_cids)}")

# Load all FTS rows for these CIDs
placeholders = ",".join("?" for _ in all_mlb_cids)
fts_rows = cur.execute(
    f"SELECT conversation_id, chunk_index, chunk_first_step, chunk_last_step, "
    f"last_modified_time, step_count, title, workspace, user_body, agent_body "
    f"FROM conversations_fts WHERE conversation_id IN ({placeholders}) ORDER BY chunk_index ASC",
    list(all_mlb_cids),
).fetchall()

sum_rows = cur.execute(
    f"SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary "
    f"FROM conversation_summaries WHERE conversation_id IN ({placeholders})",
    list(all_mlb_cids),
).fetchall()

def parse_dt_str(val):
    if not val:
        return "unknown"
    s = str(val)
    if "-" in s and ":" in s:
        return s[:16]
    try:
        ns = int(s)
        ts_sec = ns / 1e9 if ns > 1e15 else ns / 1e6
        return datetime.fromtimestamp(ts_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "unknown"

by_cid = {}
for cid, title, preview, sc, lmt, raw_sum in sum_rows:
    by_cid[cid] = {
        "cid": cid,
        "title": title or "",
        "preview": preview or "",
        "dt_str": parse_dt_str(lmt),
        "step_count": int(sc or 0),
        "raw_summary_len": len(raw_sum) if raw_sum else 0,
        "raw_summary": raw_sum,
        "user_chunks": [],
        "agent_chunks": [],
    }

for cid, cidx, cfirst, clast, lmt, sc, title, ws, ubody, abody in fts_rows:
    entry = by_cid.setdefault(cid, {
        "cid": cid,
        "title": title or "",
        "preview": "",
        "dt_str": parse_dt_str(lmt),
        "step_count": int(sc or 0),
        "raw_summary_len": 0,
        "raw_summary": None,
        "user_chunks": [],
        "agent_chunks": [],
    })
    if title and not entry["title"]:
        entry["title"] = title
    dt_cand = parse_dt_str(lmt)
    if dt_cand != "unknown" and (entry["dt_str"] == "unknown" or dt_cand > entry["dt_str"]):
        entry["dt_str"] = dt_cand
    if int(sc or 0) > entry["step_count"]:
        entry["step_count"] = int(sc or 0)
    if ubody:
        entry["user_chunks"].append(ubody)
    if abody:
        entry["agent_chunks"].append(abody)

sorted_chats = sorted(by_cid.values(), key=lambda x: x["dt_str"])
with_fts_text = sum(1 for c in sorted_chats if c["user_chunks"] or c["agent_chunks"])
print(f"Chats with FTS user_body/agent_body text: {with_fts_text} / {len(sorted_chats)}")

# Also check brain/ transcript.jsonl and .md artifacts and .pb files for each chat
total_u_chars = 0
total_a_chars = 0
total_md_chars = 0

chat_records = []
for i, ch in enumerate(sorted_chats, 1):
    cid = ch["cid"]
    dt_str = ch["dt_str"]
    u_text = "\n".join(ch["user_chunks"])
    a_text = "\n".join(ch["agent_chunks"])

    # Check brain folder
    b_dir = BRAIN_DIR / cid
    md_text_list = []
    md_names = []
    if b_dir.exists():
        for mf in sorted(b_dir.glob("*.md")):
            md_names.append(mf.name)
            md_text_list.append(mf.read_text(encoding="utf-8", errors="replace"))
        # If u_text is empty, check transcript.jsonl
        t_path = b_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if not u_text and t_path.exists():
            u_lines, a_lines = [], []
            with open(t_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get("type") == "USER_INPUT" and isinstance(o.get("content"), str):
                        u_lines.append(o["content"])
                    elif o.get("type") == "PLANNER_RESPONSE" and isinstance(o.get("content"), str):
                        a_lines.append(o["content"])
            u_text = "\n".join(u_lines)
            a_text = "\n".join(a_lines)

    md_text = "\n".join(md_text_list)
    total_u_chars += len(u_text)
    total_a_chars += len(a_text)
    total_md_chars += len(md_text)

    chat_records.append({
        "idx": i,
        "cid": cid,
        "date_utc": dt_str,
        "title": ch["title"],
        "steps": ch["step_count"],
        "u_chars": len(u_text),
        "a_chars": len(a_text),
        "md_chars": len(md_text),
        "md_files": md_names,
        "u_sample": " ".join(u_text.split())[:300],
        "u_full": u_text,
        "a_full": a_text,
        "md_full": md_text,
    })

print(f"Total User Text Extracted Across All Chats:  {total_u_chars:,} chars")
print(f"Total Agent Text Extracted Across All Chats: {total_a_chars:,} chars")
print(f"Total Artifact Text Extracted Across Chats:  {total_md_chars:,} chars")
with_any_content = sum(1 for r in chat_records if (r["u_chars"] + r["a_chars"] + r["md_chars"]) > 0)
print(f"Chats with extracted content: {with_any_content} / {len(chat_records)}")

# Print any chats that had 0 FTS text before May 19 to see what we just unlocked!
early_unlocked = [r for r in chat_records if r["date_utc"] < "2026-05-19" and r["u_chars"] > 0]
print(f"\nEarly (Pre-May-19) chats now unlocked with full user & agent text from SQLite FTS: {len(early_unlocked)}")
for r in early_unlocked[:25]:
    print(f"  [{r['date_utc']}] {r['cid'][:8]} | {r['title']:42s} | u={r['u_chars']:6d} a={r['a_chars']:6d} | U: {r['u_sample'][:140]}")
