import json

with open("data/badges.json", encoding="utf-8") as f:
    badges = json.load(f)

existing_ids = {b["id"] for b in badges}

new_badges = []

# More 비행 시간
hour_milestones = [15, 75, 125, 175, 400, 600, 800, 1200, 1800, 2500, 4000]
for h in hour_milestones:
    bid = f"total_hours_{h}"
    if bid not in existing_ids:
        rarity = "legendary" if h >= 3000 else ("epic" if h >= 1000 else ("rare" if h >= 100 else "common"))
        new_badges.append({
            "id": bid,
            "category": "비행 시간",
            "name": f"{h}시간 파일럿",
            "description": f"총 비행 시간 {h}시간 달성",
            "icon": "⏱️",
            "rarity": rarity,
            "requirement": {"type": "total_hours", "value": h}
        })

# More 기종별 전문가 (add more tiers and missing types)
more_aircraft = [
    ("Boeing 737-800", [25, 75]),
    ("Airbus A320-200", [25, 75]),
    ("Airbus A330-300", [25, 75]),
    ("Airbus A350-900", [25, 75]),
    ("Boeing 777-300ER", [25, 75]),
    ("Boeing 787-9 Dreamliner", [25, 75]),
    ("Airbus A380-800", [25, 75]),
    ("Boeing 757-200", [10, 30]),
    ("Airbus A340-300", [10, 30]),
]

for ac_name, tiers in more_aircraft:
    for t in tiers:
        bid = f"{ac_name.replace(' ', '_').replace('-', '_')}_{t}h"
        if bid not in existing_ids:
            rarity = "epic" if t >= 50 else ("rare" if t >= 10 else "common")
            new_badges.append({
                "id": bid,
                "category": "기종별 전문가",
                "name": f"{ac_name} {t}시간",
                "description": f"{ac_name} 기종으로 {t}시간 비행 달성",
                "icon": "🛫",
                "rarity": rarity,
                "requirement": {"type": "aircraft_hours", "aircraft": ac_name, "value": t}
            })

# More ATC
atc_more = [15, 40, 60, 80, 120, 160, 180, 210, 230]
for m in atc_more:
    bid = f"atc_{m}"
    if bid not in existing_ids:
        rarity = "epic" if m >= 150 else ("rare" if m >= 50 else "common")
        new_badges.append({
            "id": bid,
            "category": "ATC 영어 정복",
            "name": f"ATC {m}문장",
            "description": f"항공 통신 영어 {m}개 이상 학습",
            "icon": "🎧",
            "rarity": rarity,
            "requirement": {"type": "atc_phrases", "value": m}
        })

# More 로그북
more_flights = [15, 30, 75, 150, 250]
for c in more_flights:
    bid = f"flights_{c}"
    if bid not in existing_ids:
        new_badges.append({
            "id": bid,
            "category": "로그북 성실도",
            "name": f"비행 {c}회 기록",
            "description": f"로그북에 비행 {c}회 기록",
            "icon": "📖",
            "rarity": "epic" if c >= 100 else ("rare" if c >= 25 else "common"),
            "requirement": {"type": "flight_count", "value": c}
        })

# More 대한민국 항공사 꿈
korean_more = [
    ("ke_first_officer", "대한항공 부기장 트랙", "대한항공 부기장 최소 시간 달성", "epic"),
    ("oz_first_officer", "아시아나 부기장 트랙", "아시아나 부기장 최소 시간 달성", "epic"),
    ("type_rating_777", "B777 타입 레이팅", "B777 기종 전환 훈련 완료 상징", "rare"),
    ("type_rating_a380", "A380 타입 레이팅", "A380 기종 전환 훈련 완료 상징", "epic"),
    ("incheon_captain", "인천 기장 꿈", "인천 기반 기장으로서의 꿈", "legendary"),
]

for bid, name, desc, rarity in korean_more:
    if bid not in existing_ids:
        new_badges.append({
            "id": bid,
            "category": "대한민국 항공사 꿈",
            "name": name,
            "description": desc,
            "icon": "🇰🇷",
            "rarity": rarity,
            "requirement": {"type": "special", "id": bid}
        })

# More 장거리 & 특수
special_more = [
    ("pacific_crossing", "태평양 횡단 전문가", "태평양 횡단 노선 20회", "epic"),
    ("europe_explorer", "유럽 노선 개척자", "유럽 5개국 이상 노선 경험", "rare"),
    ("cargo_veteran", "화물 베테랑", "화물기 50시간", "rare"),
    ("night_flight_50", "나이트 파일럿 50", "야간 비행 50회", "epic"),
]

for bid, name, desc, rarity in special_more:
    if bid not in existing_ids:
        new_badges.append({
            "id": bid,
            "category": "장거리 & 특수 도전",
            "name": name,
            "description": desc,
            "icon": "🌍",
            "rarity": rarity,
            "requirement": {"type": "special", "id": bid}
        })

# More 지식 & 시뮬레이터
knowledge_more = [
    ("radar_master", "레이더 마스터", "레이더에서 500대 관찰", "rare"),
    ("planner_100", "슈퍼 플래너", "비행 계획 100회", "epic"),
    ("all_aircraft", "전 기종 마스터", "모든 기종 설계도 열람", "epic"),
]

for bid, name, desc, rarity in knowledge_more:
    if bid not in existing_ids:
        new_badges.append({
            "id": bid,
            "category": "지식 & 시뮬레이터 마스터",
            "name": name,
            "description": desc,
            "icon": "📚",
            "rarity": rarity,
            "requirement": {"type": "special", "id": bid}
        })

# More 전설
legend_more = [
    ("ke_5000h", "대한항공 5000시간", "대한항공에서 5000시간 누적", "legendary"),
    ("global_10000", "글로벌 1만 시간", "전 세계 노선 1만 시간", "legendary"),
    ("true_captain_2", "진짜 기장 II", "총 8000시간 + 4개 타입 경험", "legendary"),
]

for bid, name, desc, rarity in legend_more:
    if bid not in existing_ids:
        new_badges.append({
            "id": bid,
            "category": "전설의 업적",
            "name": name,
            "description": desc,
            "icon": "🏆",
            "rarity": rarity,
            "requirement": {"type": "special", "id": bid}
        })

badges.extend(new_badges)

with open("data/badges.json", "w", encoding="utf-8") as f:
    json.dump(badges, f, ensure_ascii=False, indent=2)

print(f"Badges expanded to {len(badges)} total.")
print(f"Added {len(new_badges)} new badges.")
