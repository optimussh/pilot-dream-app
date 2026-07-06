#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""한국 항공사(LCC 등) 주요 항공편 4개씩 flights_db.json에 추가"""
import json

with open("data/flights_db.json", encoding="utf-8") as f:
    flights = json.load(f)

existing_numbers = {f["flight_number"] for f in flights}

new_flights = [
    # 제주항공 (7C)
    {"airline": "7C", "airline_name": "제주항공", "flight_number": "7C1101", "route": "ICN-CJU", "aircraft": "Boeing 737-800", "typical_duration": 1.0},
    {"airline": "7C", "airline_name": "제주항공", "flight_number": "7C1102", "route": "CJU-ICN", "aircraft": "Boeing 737-800", "typical_duration": 1.0},
    {"airline": "7C", "airline_name": "제주항공", "flight_number": "7C1401", "route": "ICN-NRT", "aircraft": "Boeing 737-800", "typical_duration": 2.3},
    {"airline": "7C", "airline_name": "제주항공", "flight_number": "7C2401", "route": "ICN-BKK", "aircraft": "Airbus A321-200", "typical_duration": 5.5},
    # 진에어 (LJ)
    {"airline": "LJ", "airline_name": "진에어", "flight_number": "LJ111", "route": "ICN-CJU", "aircraft": "Boeing 737-800", "typical_duration": 1.0},
    {"airline": "LJ", "airline_name": "진에어", "flight_number": "LJ201", "route": "ICN-NRT", "aircraft": "Boeing 737-800", "typical_duration": 2.3},
    {"airline": "LJ", "airline_name": "진에어", "flight_number": "LJ221", "route": "ICN-FUK", "aircraft": "Boeing 737-800", "typical_duration": 1.5},
    {"airline": "LJ", "airline_name": "진에어", "flight_number": "LJ501", "route": "ICN-TPE", "aircraft": "Boeing 737-800", "typical_duration": 2.5},
    # 티웨이항공 (TW)
    {"airline": "TW", "airline_name": "티웨이항공", "flight_number": "TW101", "route": "ICN-CJU", "aircraft": "Boeing 737-800", "typical_duration": 1.0},
    {"airline": "TW", "airline_name": "티웨이항공", "flight_number": "TW301", "route": "ICN-NRT", "aircraft": "Boeing 737-800", "typical_duration": 2.3},
    {"airline": "TW", "airline_name": "티웨이항공", "flight_number": "TW303", "route": "ICN-KIX", "aircraft": "Boeing 737-800", "typical_duration": 2.0},
    {"airline": "TW", "airline_name": "티웨이항공", "flight_number": "TW405", "route": "ICN-BKK", "aircraft": "Boeing 737-800", "typical_duration": 5.5},
    # 에어부산 (BX)
    {"airline": "BX", "airline_name": "에어부산", "flight_number": "BX813", "route": "PUS-ICN", "aircraft": "Airbus A321-200", "typical_duration": 0.8},
    {"airline": "BX", "airline_name": "에어부산", "flight_number": "BX814", "route": "ICN-PUS", "aircraft": "Airbus A321-200", "typical_duration": 0.8},
    {"airline": "BX", "airline_name": "에어부산", "flight_number": "BX748", "route": "PUS-NRT", "aircraft": "Airbus A320-200", "typical_duration": 1.8},
    {"airline": "BX", "airline_name": "에어부산", "flight_number": "BX791", "route": "PUS-CJU", "aircraft": "Boeing 737-800", "typical_duration": 0.7},
    # 에어서울 (RS)
    {"airline": "RS", "airline_name": "에어서울", "flight_number": "RS801", "route": "ICN-NRT", "aircraft": "Airbus A321-200", "typical_duration": 2.3},
    {"airline": "RS", "airline_name": "에어서울", "flight_number": "RS811", "route": "ICN-KIX", "aircraft": "Airbus A321-200", "typical_duration": 2.0},
    {"airline": "RS", "airline_name": "에어서울", "flight_number": "RS901", "route": "ICN-CXR", "aircraft": "Airbus A321-200", "typical_duration": 5.0},
    {"airline": "RS", "airline_name": "에어서울", "flight_number": "RS711", "route": "ICN-TPE", "aircraft": "Airbus A321-200", "typical_duration": 2.5},
    # 에어프레미아 (YP)
    {"airline": "YP", "airline_name": "에어프레미아", "flight_number": "YP601", "route": "ICN-EWR", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 13.5},
    {"airline": "YP", "airline_name": "에어프레미아", "flight_number": "YP651", "route": "ICN-SFO", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 11.0},
    {"airline": "YP", "airline_name": "에어프레미아", "flight_number": "YP701", "route": "ICN-LAX", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 11.5},
    {"airline": "YP", "airline_name": "에어프레미아", "flight_number": "YP751", "route": "ICN-SIN", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 6.5},
]

added = 0
for flight in new_flights:
    if flight["flight_number"] not in existing_numbers:
        flights.append(flight)
        existing_numbers.add(flight["flight_number"])
        added += 1

with open("data/flights_db.json", "w", encoding="utf-8") as f:
    json.dump(flights, f, ensure_ascii=False, indent=2)

print(f"Added {added} Korean airline flights. Total: {len(flights)}")