import json

with open("data/aircraft.json", encoding="utf-8") as f:
    aircraft = json.load(f)

name_map = {
    "A320": "Airbus A320-200",
    "A321": "Airbus A321-200",
    "B737-800": "Boeing 737-800",
    "B787-9": "Boeing 787-9 Dreamliner",
    "A380-800": "Airbus A380-800",
    "B777-300ER": "Boeing 777-300ER",
    "A330-300": "Airbus A330-300",
    "A350-900": "Airbus A350-900",
    "A340-300": "Airbus A340-300",
    "B757-200": "Boeing 757-200",
    "B777-200ER": "Boeing 777-200ER",
}

with open("data/flights_db.json", encoding="utf-8") as f:
    flights = json.load(f)

updated = 0
for f in flights:
    old = f["aircraft"]
    if old in name_map:
        f["aircraft"] = name_map[old]
        updated += 1

with open("data/flights_db.json", "w", encoding="utf-8") as f:
    json.dump(flights, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} flights with consistent aircraft names.")
