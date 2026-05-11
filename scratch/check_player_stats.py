from utils.audit_engine import AuditEngine
from datetime import datetime

audit = AuditEngine()
date_str = "2026-05-09"
results = audit.fetch_results(date=date_str)

print("--- White Sox Player Stats ---")
chw = results.get("Chicago White Sox", {})
if chw:
    for name, stats in chw.get('hitters', {}).items():
        if stats['hits'] > 0 or stats['hr'] > 0 or stats['rbi'] > 0:
            print(f"{name}: {stats['hits']}H, {stats['hr']}HR, {stats['rbi']}RBI")

print("\n--- Arizona Player Stats ---")
ari = results.get("Arizona Diamondbacks", {})
if ari:
    for name, stats in ari.get('hitters', {}).items():
        if stats['hits'] > 0 or stats['hr'] > 0 or stats['rbi'] > 0:
            print(f"{name}: {stats['hits']}H, {stats['hr']}HR, {stats['rbi']}RBI")

print("\n--- Cubs Player Stats ---")
chc = results.get("Chicago Cubs", {})
if chc:
    for name, stats in chc.get('hitters', {}).items():
        if "conforto" in name.lower():
            print(f"{name}: {stats['hits']}H, {stats['hr']}HR, {stats['rbi']}RBI")
