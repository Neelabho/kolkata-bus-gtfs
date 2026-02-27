"""
build_gtfs.py
─────────────────────────────────────────────────────────────
Drop all trip JSON files (sent by friends) into received_trips/
Then run:  python build_gtfs.py
Output:    6 GTFS files written to gtfs/ folder
─────────────────────────────────────────────────────────────
"""

import json
import os
import pandas as pd
from pathlib import Path

# ── FOLDERS ──
INPUT_FOLDER  = Path("received_trips")
OUTPUT_FOLDER = Path("gtfs")
OUTPUT_FOLDER.mkdir(exist_ok=True)
INPUT_FOLDER.mkdir(exist_ok=True)

# ── LOAD ALL TRIP FILES ──
json_files = list(INPUT_FOLDER.glob("*.json"))
if not json_files:
    print("No JSON files found in received_trips/ folder.")
    print("Ask your friends to send their trip JSON files and drop them in that folder.")
    exit()

all_trips = []
for f in json_files:
    with open(f, encoding='utf-8') as file:
        trip = json.load(file)
        all_trips.append(trip)
        print(f"  Loaded: {f.name}  →  Route {trip['routeId']} by {trip.get('collectedBy','Unknown')}")

print(f"\n✓ {len(all_trips)} trip(s) loaded\n")

# ── 1. agency.txt ──
agencies_seen = {}
for t in all_trips:
    a = t['agency']
    if a not in agencies_seen:
        agencies_seen[a] = {
            "agency_id":       a,
            "agency_name":     "West Bengal Transport Corporation" if a == "WBTC" else "Private Operator" if a == "Private" else "Unknown",
            "agency_url":      "https://www.wbtc.co.in" if a == "WBTC" else "",
            "agency_timezone": "Asia/Kolkata"
        }
pd.DataFrame(list(agencies_seen.values())).to_csv(OUTPUT_FOLDER / "agency.txt", index=False)
print(f"agency.txt       — {len(agencies_seen)} agenc(ies)")

# ── 2. routes.txt ──
routes_seen = {}
for t in all_trips:
    rid = t['routeId']
    if rid not in routes_seen:
        routes_seen[rid] = {
            "route_id":         rid,
            "agency_id":        t['agency'],
            "route_short_name": rid,
            "route_long_name":  t.get('routeName', rid),
            "route_type":       3
        }
pd.DataFrame(list(routes_seen.values())).to_csv(OUTPUT_FOLDER / "routes.txt", index=False)
print(f"routes.txt       — {len(routes_seen)} route(s)")

# ── 3. stops.txt ──
# Deduplicated by stop name. If same stop appears in multiple trips,
# use the first GPS-verified coordinates found.
stops_seen = {}
for t in all_trips:
    for s in t['stops']:
        name = s['name']
        if name not in stops_seen:
            stops_seen[name] = {
                "stop_id":   s['stopId'],
                "stop_name": name,
                "stop_lat":  s['lat'],
                "stop_lon":  s['lon'],
                "verified":  s['verified']
            }
        else:
            # If we already have this stop but it was unverified,
            # upgrade it if this instance is GPS verified
            if not stops_seen[name]['verified'] and s['verified']:
                stops_seen[name]['stop_lat'] = s['lat']
                stops_seen[name]['stop_lon'] = s['lon']
                stops_seen[name]['verified'] = True

pd.DataFrame(list(stops_seen.values())).to_csv(OUTPUT_FOLDER / "stops.txt", index=False)
print(f"stops.txt        — {len(stops_seen)} unique stop(s)")

# ── 4. trips.txt ──
trip_rows = []
for t in all_trips:
    trip_rows.append({
        "route_id":       t['routeId'],
        "service_id":     t['serviceId'],
        "trip_id":        t['tripId'],
        "direction_id":   t['direction'],
        "trip_headsign":  t['headsign']
    })
pd.DataFrame(trip_rows).to_csv(OUTPUT_FOLDER / "trips.txt", index=False)
print(f"trips.txt        — {len(trip_rows)} trip(s)")

# ── 5. stop_times.txt ──
st_rows = []
for t in all_trips:
    for s in t['stops']:
        st_rows.append({
            "trip_id":        t['tripId'],
            "arrival_time":   s['arrivalTime'],
            "departure_time": s['departureTime'],
            "stop_id":        s['stopId'],
            "stop_sequence":  s['seq']
        })
pd.DataFrame(st_rows).to_csv(OUTPUT_FOLDER / "stop_times.txt", index=False)
print(f"stop_times.txt   — {len(st_rows)} row(s)")

# ── 6. calendar.txt ──
year = 2026
cal_patterns = {
    "WEEKDAY": [1,1,1,1,1,0,0],
    "WEEKEND": [0,0,0,0,0,1,1],
    "DAILY":   [1,1,1,1,1,1,1]
}
services_used = list({t['serviceId'] for t in all_trips})
cal_rows = []
for sid in services_used:
    days = cal_patterns.get(sid, cal_patterns['WEEKDAY'])
    cal_rows.append({
        "service_id": sid,
        "monday":    days[0], "tuesday":   days[1], "wednesday": days[2],
        "thursday":  days[3], "friday":    days[4],
        "saturday":  days[5], "sunday":    days[6],
        "start_date": f"{year}0101",
        "end_date":   f"{year}1231"
    })
pd.DataFrame(cal_rows).to_csv(OUTPUT_FOLDER / "calendar.txt", index=False)
print(f"calendar.txt     — {len(cal_rows)} service pattern(s)")

# ── SUMMARY ──
print(f"""
────────────────────────────────
✓ Done. GTFS files written to gtfs/

  Trips collected by:""")
collectors = {}
for t in all_trips:
    c = t.get('collectedBy', 'Unknown')
    collectors[c] = collectors.get(c, 0) + 1
for name, count in collectors.items():
    print(f"    {name}: {count} trip(s)")
print("────────────────────────────────")
