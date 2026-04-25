"""
OMEGA Trend Tag Tracker — v6.3
-------------------------------
Usage:
  python scratch/check_trends.py          → Show today's tags + running stats
  python scratch/check_trends.py --update → Input actual runs for open entries
  python scratch/check_trends.py --all    → Show full history table
"""

import json
import csv
import os
import sys
import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH    = os.path.join(BASE_DIR, "logs", "trend_tag_log.csv")
RESULTS_PATH = os.path.join(BASE_DIR, "reports", "latest_results.json")

FIELDNAMES = [
    'date', 'slate_timestamp', 'team', 'opponent', 'tag',
    'divergence', 'prev_divergence', 'delta',
    'ml_move', 'tt_move', 'implied_total',
    'actual_runs', 'hit'
]

# ── Helpers ─────────────────────────────────────────────────────────────────

def load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline='') as f:
        return list(csv.DictReader(f))

def save_log(rows):
    with open(LOG_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

def pct(n, d):
    return f"{round(n/d*100, 1)}%" if d else "N/A"

# ── Views ────────────────────────────────────────────────────────────────────

def show_todays_tags():
    """Print today's SURGING/FADING tags with ITT from the live results file."""
    today = datetime.date.today().isoformat()

    print("\n" + "="*60)
    print("  OMEGA TREND TAG TRACKER — Today's Tags")
    print(f"  Slate date: {today}")
    print("="*60)

    # Pull live tags from latest_results.json
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as f:
            data = json.load(f)
        ts = data.get('timestamp', 'unknown')[:16]
        tagged = [t for t in data.get('teams', []) if t.get('trend') in ('SURGING', 'FADING')]
        if tagged:
            print(f"\n  Last OMEGA run: {ts}\n")
            print(f"  {'TEAM':<26} {'TAG':<9} {'DIV':>5} {'ML':>6} {'TT':>5} {'ITT':>6}")
            print(f"  {'-'*26} {'-'*8} {'-'*5} {'-'*6} {'-'*5} {'-'*6}")
            for t in tagged:
                tag_icon = "🔥 SURGING" if t['trend'] == 'SURGING' else "❄️  FADING"
                print(f"  {t['team']:<26} {tag_icon:<9} "
                      f"{t.get('divergence', '?'):>5} "
                      f"{t.get('ml_move', '?'):>6} "
                      f"{t.get('tt_move', '?'):>5} "
                      f"{t.get('implied_total', '?'):>6}")
        else:
            print("\n  No SURGING/FADING tags fired today.")
    else:
        print("\n  [WARNING] No latest_results.json found. Run the model first.")

    # Also show any open (unfilled) log entries
    rows = load_log()
    open_rows = [r for r in rows if r.get('actual_runs') == '' and r.get('date') == today]
    if open_rows:
        print(f"\n  ⏳ {len(open_rows)} open entry(ies) awaiting actual runs.")
        print("  Run with --update to fill them in.\n")


def show_all_history():
    """Print the full trend tag log as a formatted table."""
    rows = load_log()
    if not rows:
        print("\n  No trend tag history found yet.\n")
        return

    print("\n" + "="*80)
    print("  OMEGA TREND TAG FULL HISTORY")
    print("="*80)
    print(f"  {'DATE':<11} {'TEAM':<26} {'TAG':<9} {'ITT':>5} {'ACTUAL':>7} {'HIT':<5}")
    print(f"  {'-'*11} {'-'*26} {'-'*8} {'-'*5} {'-'*7} {'-'*5}")
    for r in rows:
        hit_str = "✅" if r['hit'] == '1' else ("❌" if r['hit'] == '0' else "⏳")
        actual  = r['actual_runs'] if r['actual_runs'] != '' else "—"
        print(f"  {r['date']:<11} {r['team']:<26} {r['tag']:<9} "
              f"{r.get('implied_total','?'):>5} {actual:>7} {hit_str}")
    print()
    _print_stats(rows)


def _print_stats(rows):
    """Print running hit rate breakdown."""
    resolved = [r for r in rows if r.get('hit') in ('0', '1')]
    if not resolved:
        print("  No resolved entries yet — fill in actual_runs with --update.\n")
        return

    surging = [r for r in resolved if r['tag'] == 'SURGING']
    fading  = [r for r in resolved if r['tag'] == 'FADING']

    s_hits = sum(1 for r in surging if r['hit'] == '1')
    f_hits = sum(1 for r in fading  if r['hit'] == '1')
    total_hits = s_hits + f_hits

    print("─"*50)
    print("  📊 RUNNING HIT RATES")
    print("─"*50)
    print(f"  SURGING → scored ≥ ITT  : {s_hits}/{len(surging)}  ({pct(s_hits, len(surging))})")
    print(f"  FADING  → scored < ITT  : {f_hits}/{len(fading)}   ({pct(f_hits, len(fading))})")
    print(f"  Combined accuracy       : {total_hits}/{len(resolved)}  ({pct(total_hits, len(resolved))})")
    print()
    if len(resolved) >= 10:
        combined_rate = total_hits / len(resolved)
        if combined_rate >= 0.60:
            print("  🟢 Signal is STRONG (≥60%) — consider wiring into score modifier.")
        elif combined_rate >= 0.55:
            print("  🟡 Signal is PROMISING (≥55%) — watch another week before wiring in.")
        else:
            print("  🔴 Signal is WEAK (<55%) — tighten thresholds before wiring in.")
    else:
        print(f"  ⏳ Need {10 - len(resolved)} more resolved entries for statistical confidence.")
    print()


def update_actuals():
    """Interactive prompt to fill in actual_runs for open log entries."""
    rows = load_log()
    open_rows = [r for r in rows if r.get('actual_runs') == '']

    if not open_rows:
        print("\n  ✅ No open entries — everything is filled in.\n")
        return

    print("\n" + "="*60)
    print("  OMEGA TREND TAG — Enter Actual Runs")
    print("  (Press Enter to skip, 'q' to quit)\n")

    changed = False
    for r in rows:
        if r.get('actual_runs') != '':
            continue
        itt = float(r['implied_total']) if r['implied_total'] else None
        tag = r['tag']
        print(f"  [{r['date']}] {r['team']} vs {r['opponent']}  |  Tag: {tag}  |  ITT: {itt}")
        raw = input("  Actual runs scored → ").strip()

        if raw.lower() == 'q':
            break
        if raw == '':
            continue

        try:
            actual = float(raw)
            r['actual_runs'] = raw
            # Hit logic: SURGING = scored at/above ITT; FADING = scored below ITT
            if itt is not None:
                if tag == 'SURGING':
                    r['hit'] = '1' if actual >= itt else '0'
                elif tag == 'FADING':
                    r['hit'] = '1' if actual < itt else '0'
            changed = True
            hit_label = "✅ HIT" if r['hit'] == '1' else "❌ MISS"
            print(f"  Logged {actual} runs — {hit_label}\n")
        except ValueError:
            print("  Invalid input, skipping.\n")

    if changed:
        save_log(rows)
        print("  💾 Log saved.\n")

    _print_stats(rows)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if '--update' in args:
        update_actuals()
    elif '--all' in args:
        show_all_history()
    else:
        show_todays_tags()
        # Always show running stats at the bottom if there's history
        rows = load_log()
        resolved = [r for r in rows if r.get('hit') in ('0', '1')]
        if resolved:
            _print_stats(rows)
