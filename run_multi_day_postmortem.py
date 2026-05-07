"""
OMEGA v7.1: Multi-Day Retroactive Post-Mortem
Analyzes multiple days of archived predictions vs actual MLB results.
Tracks signal accuracy (WHALE, SURGING, PARADOX, etc.) across days.

Usage:
    python run_multi_day_postmortem.py 2026-04-30 2026-05-03
    python run_multi_day_postmortem.py  # defaults to last 4 days
"""

import json
import os
import sys
from datetime import datetime, timedelta
from utils.audit_engine import AuditEngine
from config import config


def run_multi_day_postmortem(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  OMEGA v7.1: MULTI-DAY POST-MORTEM")
    print(f"  Range: {start_date_str} to {end_date_str}")
    print(f"{'='*60}\n")

    audit = AuditEngine()
    archive_dir = os.path.join(config.REPORTS_DIR, "archive")

    # Aggregate trackers
    signal_tracker = {
        'WHALE': {'total': 0, 'hit': 0},
        'SHARK': {'total': 0, 'hit': 0},
        'SHARP': {'total': 0, 'hit': 0},
        'STORM': {'total': 0, 'hit': 0},
        'STEAM': {'total': 0, 'hit': 0},
        'BURST': {'total': 0, 'hit': 0},
        'SURGING': {'total': 0, 'hit': 0},
        'FADING_FADE': {'total': 0, 'hit': 0},  # Did fading teams actually underperform?
        'PARADOX_FADE': {'total': 0, 'hit': 0},  # Did paradox pitchers get shelled?
        'GASSED_BP': {'total': 0, 'hit': 0},     # Did gassed bullpen games produce runs?
    }

    top3_stack_tracker = {'total': 0, 'hit': 0}  # Top 3 stacks scoring 4+ runs
    top5_hitter_tracker = {'total': 0, 'hit': 0}  # Top 5 hitters getting 2+ hits or 1+ HR
    top3_pitcher_tracker = {'total': 0, 'hit': 0}  # Top 3 pitchers having quality starts
    daily_summaries = []

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        archive_path = os.path.join(archive_dir, f"results_{date_str}.json")

        if not os.path.exists(archive_path):
            print(f"[SKIP]: No archived results for {date_str}")
            current += timedelta(days=1)
            continue

        print(f"\n[PROCESSING]: {date_str}...")

        with open(archive_path, 'r', encoding='utf-8') as f:
            projections = json.load(f)

        actuals = audit.fetch_results(date=date_str)
        if not actuals:
            print(f"  - WARNING: Could not fetch actuals for {date_str}")
            current += timedelta(days=1)
            continue

        teams = projections.get('teams', [])
        pitchers = projections.get('pitchers', [])
        hitters = projections.get('hitters', [])

        day_summary = {
            'date': date_str,
            'games': len(teams) // 2,
            'signals_fired': 0,
            'signals_hit': 0,
        }

        # Score Teams
        t_audit = audit.score_performance(teams, actuals)

        for t in t_audit:
            actual_runs = t.get('actual_runs', 0)
            hit = actual_runs >= 4  # 4+ runs = stack success

            # Track signals
            for signal, key in [
                ('is_whale', 'WHALE'), ('is_shark', 'SHARK'),
                ('is_sharp', 'SHARP'), ('is_storm', 'STORM'),
                ('is_steam', 'STEAM'), ('is_burst', 'BURST'),
            ]:
                if t.get(signal):
                    signal_tracker[key]['total'] += 1
                    day_summary['signals_fired'] += 1
                    if hit:
                        signal_tracker[key]['hit'] += 1
                        day_summary['signals_hit'] += 1

            # SURGING tracker
            if t.get('trend') == 'SURGING':
                signal_tracker['SURGING']['total'] += 1
                day_summary['signals_fired'] += 1
                if hit:
                    signal_tracker['SURGING']['hit'] += 1
                    day_summary['signals_hit'] += 1

            # FADING fade tracker (success = team scores UNDER 4 runs)
            if t.get('trend') == 'FADING':
                signal_tracker['FADING_FADE']['total'] += 1
                if actual_runs < 4:
                    signal_tracker['FADING_FADE']['hit'] += 1

            # GASSED BP tracker (success = opposing team scores 5+ runs)
            if t.get('is_gassed'):
                signal_tracker['GASSED_BP']['total'] += 1
                if actual_runs >= 5:
                    signal_tracker['GASSED_BP']['hit'] += 1

        # Top 3 stacks accuracy
        for t in t_audit[:3]:
            top3_stack_tracker['total'] += 1
            if t.get('actual_runs', 0) >= 4:
                top3_stack_tracker['hit'] += 1

        # Score Pitchers
        p_audit = audit.score_performance(pitchers, actuals)

        # PARADOX fade tracker
        for p in p_audit:
            if p.get('is_paradox'):
                signal_tracker['PARADOX_FADE']['total'] += 1
                er = p.get('actual_er', 0)
                if er >= 4:  # Paradox pitcher gave up 4+ ER = fade success
                    signal_tracker['PARADOX_FADE']['hit'] += 1

        # Top 3 pitchers accuracy
        for p in p_audit[:3]:
            top3_pitcher_tracker['total'] += 1
            if p.get('success_flag') == '[WIN]':
                top3_pitcher_tracker['hit'] += 1

        # Score Hitters
        h_audit = audit.score_performance(hitters, actuals)
        for h in h_audit[:5]:
            top5_hitter_tracker['total'] += 1
            if h.get('success_flag') == '[WIN]':
                top5_hitter_tracker['hit'] += 1

        daily_summaries.append(day_summary)
        current += timedelta(days=1)

    # Generate Report
    _generate_report(
        start_date_str, end_date_str,
        signal_tracker, top3_stack_tracker, top5_hitter_tracker,
        top3_pitcher_tracker, daily_summaries
    )


def _generate_report(start, end, signals, stacks, hitters, pitchers, daily):
    lines = []
    lines.append(f"# 📊 OMEGA Multi-Day Post-Mortem: {start} → {end}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Signal Accuracy Table
    lines.append("## Signal Accuracy Report")
    lines.append("")
    lines.append("| Signal | Fired | Hit | Rate | Status |")
    lines.append("|--------|-------|-----|------|--------|")

    for name, data in signals.items():
        total = data['total']
        hit = data['hit']
        if total == 0:
            rate_str = "N/A"
            status = "⚪ No Data"
        else:
            rate = (hit / total) * 100
            rate_str = f"{rate:.0f}%"
            if rate >= 60:
                status = "🟢 Strong"
            elif rate >= 45:
                status = "🟡 Moderate"
            else:
                status = "🔴 Weak"
        lines.append(f"| **{name}** | {total} | {hit} | {rate_str} | {status} |")

    lines.append("")

    # Core Accuracy
    lines.append("## Core Projection Accuracy")
    lines.append("")
    lines.append("| Metric | Total | Hit | Rate |")
    lines.append("|--------|-------|-----|------|")

    for label, tracker in [
        ("Top 3 Stacks (4+ runs)", stacks),
        ("Top 3 Pitchers (QS)", pitchers),
        ("Top 5 Hitters (2H/1HR)", hitters),
    ]:
        total = tracker['total']
        hit = tracker['hit']
        rate = f"{(hit/total)*100:.0f}%" if total > 0 else "N/A"
        lines.append(f"| {label} | {total} | {hit} | {rate} |")

    lines.append("")

    # Daily Summary
    lines.append("## Daily Summary")
    lines.append("")
    lines.append("| Date | Games | Signals Fired | Signals Hit | Hit Rate |")
    lines.append("|------|-------|---------------|-------------|----------|")

    for d in daily:
        rate = f"{(d['signals_hit']/d['signals_fired'])*100:.0f}%" if d['signals_fired'] > 0 else "N/A"
        lines.append(
            f"| {d['date']} | {d['games']} | {d['signals_fired']} | {d['signals_hit']} | {rate} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")

    # Auto-generate recommendations based on signal accuracy
    for name, data in signals.items():
        if data['total'] >= 3:
            rate = (data['hit'] / data['total']) * 100
            if rate >= 65:
                lines.append(f"- ✅ **{name}** is hitting at {rate:.0f}% — **increase weight or trust**")
            elif rate < 40:
                lines.append(f"- ⚠️ **{name}** is hitting at only {rate:.0f}% — **review and potentially downweight**")

    lines.append("")

    # Write report
    report_path = os.path.join(
        config.REPORTS_DIR,
        f"multi_day_postmortem_{start}_to_{end}.md"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[REPORT]: Multi-day post-mortem saved to {report_path}")
    print(f"[SUMMARY]: Analyzed {len(daily)} day(s)")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    elif len(sys.argv) == 2:
        # Single date
        start_date = sys.argv[1]
        end_date = sys.argv[1]
    else:
        # Default: last 4 days
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")

    run_multi_day_postmortem(start_date, end_date)
