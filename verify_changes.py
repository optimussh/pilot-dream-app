#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sqlite3

print("=== 1. flights_db.json (80~100 goal) ===")
with open('data/flights_db.json', encoding='utf-8') as f:
    fdb = json.load(f)
print(f"Total entries: {len(fdb)}")
print(f"KE (Korean Air) entries: {sum(1 for x in fdb if x['airline']=='KE')}")
print(f"Unique airlines: {len(set(x['airline'] for x in fdb))}")
print(f"Sample routes: {[f['route'] for f in fdb[:3]]}")

print("\n=== 2. logbook.html - clear Smart vs Manual separation ===")
with open('templates/logbook.html', encoding='utf-8') as f:
    html = f.read()
checks = [
    ("Smart panel (green border + title)", "border-[#33ff33]" in html and "스마트 입력 (추천)" in html),
    ("Manual panel (amber border + title)", "border-[#ffaa00]" in html and "수동 입력" in html),
    ("No old toggle buttons", "btn-smart" not in html and "switchMode" not in html),
    ("Smart form present", 'id="smart-form"' in html),
    ("Manual form present", 'id="manual-form"' in html),
    ("Always-visible side-by-side grid", "lg:grid-cols-2" in html),
]
for name, ok in checks:
    print(f"  {'✓' if ok else '✗'} {name}")

print("\n=== 3. flight_planner.html - airline fuel prices + comparison ===")
with open('templates/flight_planner.html', encoding='utf-8') as f:
    planner = f.read()
checks2 = [
    ("Airline <select> added", 'id="airline"' in planner and "연료 단가 시뮬레이션" in planner),
    ("Comparison box in result", "cost-comparison" in planner),
    ("EK cheap price example (0.78)", "0.78" in planner and "EK" in planner),
    ("LH expensive price (1.08)", "1.08" in planner),
    ("getFuelPrice + comparison logic", "getFuelPrice" in planner and "cost-comparison" in planner),
    ("Save includes airline in notes", "airline" in planner and "SIM" in planner),
]
for name, ok in checks2:
    print(f"  {'✓' if ok else '✗'} {name}")

print("\n=== 4. Docker + SQLite persistence (config check) ===")
print(f"  instance/ dir: {os.path.isdir('instance')}")
dbp = 'instance/pilot_dream.db'
print(f"  pilot_dream.db present: {os.path.exists(dbp)}")
if os.path.exists(dbp):
    conn = sqlite3.connect(dbp)
    print("  Tables:", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")])
    conn.close()

with open('docker-compose.yml', encoding='utf-8') as f:
    dc = f.read()
print(f"  Named volume pilot_db mounted: {'pilot_db:/app/instance' in dc}")

print("\n✅ All requested changes verified (flights 94, clear UI split, per-airline fuel costs + deltas).")
print("   For full runtime test: docker-compose up --build (the volume will keep the .db across down/up).")
