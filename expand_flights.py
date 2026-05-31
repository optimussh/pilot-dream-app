import json

with open("data/flights_db.json", encoding="utf-8") as f:
    flights = json.load(f)

additional = [
    {"airline": "KE", "airline_name": "대한항공", "flight_number": "KE075", "route": "ICN-MNL", "aircraft": "Boeing 737-800", "typical_duration": 4.2},
    {"airline": "KE", "airline_name": "대한항공", "flight_number": "KE095", "route": "ICN-TPE", "aircraft": "Airbus A321-200", "typical_duration": 2.8},
    {"airline": "OZ", "airline_name": "아시아나항공", "flight_number": "OZ751", "route": "ICN-HKG", "aircraft": "Airbus A330-300", "typical_duration": 3.8},
    {"airline": "JL", "airline_name": "일본항공", "flight_number": "JL077", "route": "HND-SIN", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 7.3},
    {"airline": "NH", "airline_name": "전일본공수", "flight_number": "NH219", "route": "HND-BKK", "aircraft": "Boeing 787-9 Dreamliner", "typical_duration": 6.5},
    {"airline": "EK", "airline_name": "에미레이트", "flight_number": "EK306", "route": "DXB-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 9.8},
    {"airline": "QR", "airline_name": "카타르항공", "flight_number": "QR857", "route": "DOH-HKG", "aircraft": "Airbus A350-900", "typical_duration": 7.8},
    {"airline": "SQ", "airline_name": "싱가포르항공", "flight_number": "SQ221", "route": "SIN-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 6.1},
    {"airline": "CX", "airline_name": "캐세이퍼시픽", "flight_number": "CX501", "route": "HKG-ICN", "aircraft": "Airbus A330-300", "typical_duration": 3.5},
    {"airline": "DL", "airline_name": "델타항공", "flight_number": "DL198", "route": "ATL-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 14.5},
    {"airline": "UA", "airline_name": "유나이티드항공", "flight_number": "UA892", "route": "SFO-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 11.8},
    {"airline": "LH", "airline_name": "루프트한자", "flight_number": "LH716", "route": "FRA-ICN", "aircraft": "Airbus A340-300", "typical_duration": 10.8},
    {"airline": "AF", "airline_name": "에어프랑스", "flight_number": "AF275", "route": "CDG-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 10.8},
    {"airline": "BA", "airline_name": "영국항공", "flight_number": "BA029", "route": "LHR-ICN", "aircraft": "Boeing 777-300ER", "typical_duration": 11.2},
]

for f in additional:
    flights.append(f)

with open("data/flights_db.json", "w", encoding="utf-8") as f:
    json.dump(flights, f, ensure_ascii=False, indent=2)

print("flights_db expanded to", len(flights), "flights.")
