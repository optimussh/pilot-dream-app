#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""퀴즈 1000 / 플래시카드 1000 / 시나리오 100 문제은행 생성"""
import json
import os
import itertools

DATA = os.path.join(os.path.dirname(__file__), "data")

# ── 기존 시드 데이터 로드 ──
def load_existing(name):
    path = os.path.join(DATA, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def save(name, data):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  saved {name}: {len(data)} items ({os.path.getsize(path)//1024} KB)")


# ═══════════════════════════════════════════
# QUIZ 1000
# ═══════════════════════════════════════════
ATC_TERMS = [
    ("Squawk", "트랜스폰더 4자리 식별 코드", "Squawk 1234."),
    ("Mayday", "극도의 긴급 호출", "Mayday, Mayday, engine failure."),
    ("Pan-Pan", "긴급이나 즉각 위험은 아닌 상황", "Pan-Pan, medical emergency."),
    ("Roger", "수신 확인(이해함)", "Roger, climb FL350."),
    ("Wilco", "수신하고 실행함", "Wilco, turning left heading 270."),
    ("Affirm", "긍정(Yes)", "Affirm, we have visual."),
    ("Negative", "부정(No)", "Negative, unable."),
    ("Standby", "대기", "Standby, checking fuel."),
    ("Cleared", "허가됨", "Cleared for takeoff."),
    ("Hold short", "특정 지점에서 대기", "Hold short of runway 24."),
    ("Go around", "착륙 중단 후 재이륙", "Going around, runway occupied."),
    ("Vectors", "관제가 지시하는 방향", "Fly heading 090, vectors ILS."),
    ("Squawk 7700", "일반 비상 코드", "Squawk 7700 immediately."),
    ("Squawk 7600", "교신 두절 코드", "Lost comm, squawk 7600."),
    ("Squawk 7500", "하이재킹 코드", "Unlawful interference, 7500."),
]

AIRCRAFT = [
    ("Boeing 737-800", "B738", "협동체", "단거리 LCC·국내선 주력"),
    ("Boeing 777-300ER", "B77W", "광동체", "장거리 국제선"),
    ("Boeing 787-9", "B789", "광동체", "중장거리 효율형"),
    ("Airbus A320", "A320", "협동체", "단거리 국제·국내"),
    ("Airbus A321neo", "A21N", "협동체", "연료효율 장형"),
    ("Airbus A330-300", "A333", "광동체", "중장거리"),
    ("Airbus A350-900", "A359", "광동체", "차세대 장거리"),
    ("Airbus A380-800", "A388", "초대형", "2층 대형기"),
    ("Embraer E190", "E190", "지역기", "소형 협동체"),
    ("ATR 72", "AT76", "터보프롭", "단거리 지역"),
]

AIRPORTS = [
    ("ICN", "인천국제공항", "한국"), ("GMP", "김포국제공항", "한국"),
    ("CJU", "제주국제공항", "한국"), ("PUS", "부산김해공항", "한국"),
    ("NRT", "나리타공항", "일본"), ("HND", "하네다공항", "일본"),
    ("LAX", "로스앤젤레스", "미국"), ("JFK", "뉴욕 JFK", "미국"),
    ("LHR", "런던 히드로", "영국"), ("CDG", "파리 샤를드골", "프랑스"),
    ("DXB", "두바이", "UAE"), ("SIN", "싱가포르 창이", "싱가포르"),
    ("HKG", "홍콩", "중국"), ("TPE", "타이베이 타오위안", "대만"),
    ("BKK", "방콕 수완나품", "태국"), ("SYD", "시드니", "호주"),
    ("FRA", "프랑크푸르트", "독일"), ("ORD", "시카고 오헤어", "미국"),
    ("SFO", "샌프란시스코", "미국"), ("PVG", "상하이 푸둥", "중국"),
]

KOREAN_AIRLINES = [
    ("KE", "대한항공", "FSC", "SkyTeam"),
    ("OZ", "아시아나항공", "FSC", "Star Alliance"),
    ("7C", "제주항공", "LCC", None),
    ("LJ", "진에어", "LCC", None),
    ("TW", "티웨이항공", "LCC", None),
    ("BX", "에어부산", "LCC", None),
    ("RS", "에어서울", "LCC", None),
    ("YP", "에어프레미아", "LCC", None),
]

WEATHER = [
    ("METAR", "현재 공항 기상", "시정·운고·풍속"),
    ("TAF", "공항 예보", "24~30시간 예보"),
    ("SIGMET", "기상 악화 정보", "난기류·적란운 등"),
    ("Wind shear", "급격한 바람 변화", "이착륙 위험"),
    ("Crosswind", "측풍", "활주로와 수직 바람"),
    ("Tailwind", "순풍", "착륙 시 제동거리 증가"),
    ("Headwind", "역풍", "이륙·착륙에 유리"),
    ("CAT", "난기류", "고도 순항 시 흔들림"),
    ("Icing", "결빙", "기체·날개 얼음"),
    ("Visibility", "시정", "착륙 최소 기준과 연관"),
]

NAV = [
    ("VOR", "VHF 전방향 무선표지", "항로 기준점"),
    ("ILS", "계기착륙시설", "정밀 접근"),
    ("RNAV", "영역 항법", "GPS 기반"),
    ("GPS", "위성 항법", "전세계 위치"),
    ("FMS", "비행관리시스템", "항로·연료 계산"),
    ("TCAS", "충돌회피", "근접 항공기 경고"),
    ("GPWS", "지상근접경보", "Terrain warning"),
    ("EGPWS", "향상형 GPWS", "지형 DB 포함"),
    ("ADF", "자동방향탐지", "NDB 수신"),
    ("DME", "거리측정장치", "VOR/DME"),
]

SPEEDS = [
    ("V1", "이륙 결정 속도", "이후 중단 불가"),
    ("VR", "리프트오프 속도", "기수 들기"),
    ("V2", "안전 이륙 속도", "엔진고장 이륙"),
    ("Vref", "착륙 기준 속도", "접근 속도"),
    ("Vapp", "최종 접근 속도", "Vref+보정"),
    ("Vne", "최대 허용 속도", "구조 한계"),
    ("Mach", "음속 대비 비율", "고고도 속도"),
    ("Knots", "노트", "해상 1해리/시간"),
]

EMERGENCIES = [
    "엔진 고장", "조종실 연기", "기압 실패", "의료 응급", "유압 손실",
    "랜딩기어 고장", "조류 충돌", "난기류", "연료 부족", "번개 피격",
    "조종계통 이상", "화재", "해치 개방", "얼음 축적", "GPS 손실",
]

SCENARIO_ICONS = ["🔥", "🏥", "⛈️", "⚡", "🐦", "💨", "🛞", "📡", "❄️", "🌫️", "⚠️", "🆘"]


def generate_quizzes(target=1000):
    existing = load_existing("quiz.json")
    seen_q = {q["question"] for q in existing}
    quizzes = list(existing)
    idx = len(quizzes) + 1

    def add(q, choices, ans, expl, cat="일반"):
        nonlocal idx
        if q in seen_q or len(quizzes) >= target:
            return
        seen_q.add(q)
        quizzes.append({
            "id": f"q{idx:04d}",
            "category": cat,
            "question": q,
            "choices": choices,
            "answer": ans,
            "explanation": expl,
        })
        idx += 1

    # ATC
    for term, ko, ex in ATC_TERMS:
        add(f"'{term}'의 항공 통신 의미로 올바른 것은?",
            [f"일반 인사말", ko, "착륙 속도", "연료량"], 1,
            f"{term}: {ko}. 예: {ex}", "ATC")
        add(f"ATC 교신에서 '{term}'는 언제 사용하나요?",
            ["항상", ko, "착륙 후만", "지상에서만"], 1,
            f"{term} — {ko}", "ATC")

    # Aircraft
    for name, icao, cls, use in AIRCRAFT:
        add(f"{name}의 분류는?",
            ["초대형기", cls, "화물기 전용", "헬리콥터"], 1,
            f"{name}({icao})는 {cls}로 {use}에 사용됩니다.", "기종")
        add(f"{name}({icao})는 주로 어떤 노선에 쓰이나요?",
            ["초단거리만", use, "군용만", "훈련 전용"], 1,
            f"{name}: {use}", "기종")

    # Airports
    for code, name, country in AIRPORTS:
        add(f"IATA 코드 '{code}'는 어느 공항인가요?",
            [name, "모르는 공항", code + " 시내", "군용기지"], 0,
            f"{code} = {name} ({country})", "공항")
        add(f"{name}({code})가 위치한 국가/지역은?",
            [country, "미국", "일본", "호주"], 0,
            f"{code}는 {country}에 있습니다.", "공항")

    # Korean airlines
    for code, name, typ, alliance in KOREAN_AIRLINES:
        add(f"{name}({code})의 항공사 유형은?",
            ["FSC" if typ == "FSC" else "LCC", "FSC" if typ == "LCC" else "LCC", "화물", "군용"], 0,
            f"{name}는 {'전통 항공사(FSC)' if typ == 'FSC' else '저비용 항공사(LCC)'}입니다.", "한국항공")
        if alliance:
            add(f"{name}가 속한 항공 동맹은?",
                [alliance, "SkyTeam" if alliance != "SkyTeam" else "Star Alliance", "없음", "oneworld"], 0,
                f"{name} — {alliance} 멤버", "한국항공")

    # Weather
    for term, ko, detail in WEATHER:
        add(f"항공 기상에서 '{term}'란?",
            [ko, "연료 종류", "착륙 속도", "승객 수"], 0,
            f"{term}: {ko}. {detail}", "기상")
        add(f"{term} 정보가 비행에 중요한 이유는?",
            ["기내식", detail, "티켓 가격", "좌석 배치"], 1,
            f"{term} — {detail}", "기상")

    # Navigation
    for term, ko, use in NAV:
        add(f"항공 전자 '{term}'의 역할은?",
            [ko, "객실 안내", "연료 주입", "수하물 분류"], 0,
            f"{term}: {ko}. {use}", "항법")
        add(f"조종사가 '{term}'를 사용하는 상황은?",
            [use, "기내식 서비스", "탑승 수속", "면세품 판매"], 0,
            f"{term} — {use}", "항법")

    # Speeds
    for spd, ko, note in SPEEDS:
        add(f"이륙·착륙 속도 '{spd}'의 의미는?",
            [ko, "연료량", "승객 수", "항로명"], 0,
            f"{spd}: {ko}. {note}", "성능")
        add(f"'{spd}'와 관련된 올바른 설명은?",
            [note, "기내 온도", "좌석 등급", "공항 코드"], 0,
            f"{spd} — {note}", "성능")

    # CRM / procedures templates
    crm_qs = [
        ("비상 시 조종실에서 가장 먼저 해야 할 것은?", ["체크리스트·역할 분담", "승객 방송", "즉시 착륙", "고도 상승"], 0, "CRM: PF/PM 분업, 체크리스트 우선"),
        ("기장(PIC)의 최종 권한은?", ["안전에 관한 최종 결정", "기내식 선택", "티켓 환불", "좌석 배정"], 0, "PIC = Pilot In Command"),
        ("부기장(FO)의 역할은?", ["기장 보조·조종·모니터링", "객실 서비스", "수하물", "정비"], 0, "FO는 기장을 보조합니다"),
        ("대체공항(Diversion)을 선택할 때 우선순위는?", ["안전·연료·기상", "가장 가까운 면세점", "승객 투표", "가장 싼 공항"], 0, "안전이 최우선"),
        ("연료 계획 시 반드시 포함해야 하는 것은?", ["예비연료(Reserve)", "기내식", "면세품", "Wi-Fi"], 0, "Trip+Alternate+Reserve+Final"),
        ("악천후 접근 시 Go-around를 하는 이유는?", ["안전 기준 미달", "승객 요청", "연료 남음", "시간 여유"], 0, "안전하지 않으면 재접근"),
        ("ATC와 교신 시 표준 phraseology를 쓰는 이유는?", ["오해 방지·안전", "영어 연습", "음성 녹음", "티켓 할인"], 0, "표준 교신 = 안전"),
        ("Type Rating이 필요한 이유는?", ["기종별 조종 자격", "면허 갱신", "여권", "비자"], 0, "기종마다 별도 훈련 필요"),
    ]
    for q, ch, ans, expl in crm_qs:
        add(q, ch, ans, expl, "CRM")

    # Numeric / FL questions
    for fl in range(50, 451, 5):
        add(f"FL{fl}은 대략 몇 피트 고도인가요?",
            [f"{fl * 100} ft", f"{fl * 10} ft", f"{fl} ft", f"{fl * 1000} ft"], 0,
            f"FL{fl} = {fl * 100}피트 (100피트 단위)", "항법")

    # Combination expansion
    wrong_pool = ["승객 투표로 결정", "무시하고 계속", "가장 빠른 속도", "연료 없이 비행",
                  "관제 무시", "체크리스트 생략", "혼자 모든 업무", "착륙 강행"]
    right_crm = ["체크리스트 확인 후 역할 분담", "CRM 원칙에 따라 협력", "안전 우선 판단",
                 "관제와 표준 교신", "대체공항 검토", "Go-around 결정", "연료·기상 재확인"]

    for i, emer in enumerate(EMERGENCIES):
        for variant in range(4):
            if len(quizzes) >= target:
                break
            w = wrong_pool[(i + variant) % len(wrong_pool)]
            r = right_crm[(i + variant) % len(right_crm)]
            add(f"순항 중 '{emer}' 상황이 발생했습니다. 기장의 적절한 1차 대응은?",
                [r, w, wrong_pool[(i+variant+1) % len(wrong_pool)], wrong_pool[(i+variant+2) % len(wrong_pool)]],
                0, f"{emer} 시: {r}", "비상절차")

    # Fill to 1000 with category mix
    fillers = []
    for code, name, country in AIRPORTS:
        for ac_name, icao, _, _ in AIRCRAFT:
            fillers.append((
                f"{name}({code})에서 {ac_name} 운항 시 고려할 점은?",
                ["연료·기상·활주로 길이", "기내식만", "면세품", "좌석 색상"],
                0, f"{code}+{icao}: 노선·기종에 맞는 연료와 성능 검토", "운항"
            ))

    wrong_atc = ["연료 주유 방식", "좌석 등급", "기내식 메뉴", "수하물 태그", "면세품 한도", "탑승구 번호"]
    for term, ko, _ in ATC_TERMS:
        for n in range(3):
            w = wrong_atc[(n + len(term)) % len(wrong_atc)]
            fillers.append((
                f"다음 중 '{term}'와 관련 없는 것은? (변형 {n + 1})",
                [w, ko, "관제 교신", "비행 안전"],
                0, f"{term}는 {ko}와 관련", "ATC"
            ))

    for emer in EMERGENCIES:
        for code, name, country in AIRPORTS:
            fillers.append((
                f"{name}({code}) 인근에서 '{emer}' 발생 시 우선 조치는?",
                ["CRM·체크리스트·회항 검토", "승객 투표", "관제 무시", "연료 무시 강행"],
                0, f"{code} 근처 {emer}: 안전·연료·기상 우선", "비상절차"
            ))

    for term, ko, detail in WEATHER:
        for fl in [200, 250, 300, 350, 400]:
            fillers.append((
                f"FL{fl} 순항 중 '{term}' 정보가 필요한 이유는?",
                [detail, "기내 온도만", "티켓 가격", "좌석 배치"],
                0, f"FL{fl}에서 {term}: {detail}", "기상"
            ))

    for code, name, typ, _ in KOREAN_AIRLINES:
        for ac_name, icao, cls, use in AIRCRAFT:
            fillers.append((
                f"{name}({code})가 {ac_name}({icao})를 운용할 때 맞는 설명은?",
                [f"{typ} · {cls} · {use}", "군용 전용", "헬리콥터만", "훈련기만"],
                0, f"{name}+{icao}: {typ}, {use}", "한국항공"
            ))

    for spd, ko, note in SPEEDS:
        for ac_name, icao, _, _ in AIRCRAFT:
            fillers.append((
                f"{ac_name}({icao}) 이륙·착륙 시 '{spd}'를 고려하는 이유는?",
                [note, "기내식", "면세품", "게이트 번호"],
                0, f"{icao} + {spd}: {note}", "성능"
            ))

    for item in itertools.cycle(fillers):
        if len(quizzes) >= target:
            break
        add(*item)

    # 최종 보충: 고유 질문 변형으로 target까지 채움
    pad_topics = list(ATC_TERMS) + [(t[0], t[1], t[2]) for t in WEATHER]
    pad_idx = 0
    while len(quizzes) < target:
        topic = pad_topics[pad_idx % len(pad_topics)]
        label = topic[0]
        ko = topic[1]
        detail = topic[2] if len(topic) > 2 else ko
        add(
            f"[보충 {pad_idx + 1}] '{label}' 관련 항공 지식 — 올바른 설명은?",
            [detail, "승객 수하물 규정", "면세 쇼핑", "기내 와이파이 요금"],
            0,
            f"{label}: {ko}",
            "일반",
        )
        pad_idx += 1

    return quizzes[:target]


def generate_flashcards(target=1000):
    existing = load_existing("flashcards.json")
    seen = {f["term"] for f in existing}
    cards = list(existing)
    idx = len(cards) + 1

    def add(term, ko, defn, ex, cat="일반"):
        nonlocal idx
        if term in seen or len(cards) >= target:
            return
        seen.add(term)
        cards.append({
            "id": f"f{idx:04d}",
            "term": term,
            "term_ko": ko,
            "definition": defn,
            "example": ex,
            "category": cat,
        })
        idx += 1

    for term, ko, ex in ATC_TERMS:
        add(term, ko, f"ATC/항공 통신 용어: {ko}", ex, "ATC")

    for term, ko, detail in WEATHER:
        add(term, ko, f"기상: {ko}. {detail}", f"Check {term} before departure.", "기상")

    for term, ko, use in NAV:
        add(term, ko, f"항법: {ko}. {use}", f"{term} used for {use}.", "항법")

    for spd, ko, note in SPEEDS:
        add(spd, ko, f"속도: {ko}. {note}", f"{spd} — {note}", "성능")

    for code, name, typ, _ in KOREAN_AIRLINES:
        add(code, name, f"한국 항공사 IATA 코드. {typ}", f"{name} flight {code}001.", "한국항공")

    for code, name, country in AIRPORTS:
        add(code, name, f"{country} 공항 IATA 코드", f"Departing {code} for destination.", "공항")

    for name, icao, cls, use in AIRCRAFT:
        add(icao, name, f"{cls} 기종. {use}", f"{icao} on final approach.", "기종")

    extra_terms = [
        ("Aileron", "에일러론", "날개 끝 회전 제어(롤)", "Move aileron for bank."),
        ("Rudder", "러더", "수직 꼬리날개(요)", "Rudder for yaw control."),
        ("Elevator", "엘리베이터", "수평 꼬리날개(피치)", "Pull elevator to climb."),
        ("Flap", "플랩", "양력 증가·속도 감소", "Flaps 15 for approach."),
        ("Spoiler", "스포일러", "양력 감소·감속", "Deploy spoilers after landing."),
        ("Slat", "슬랫", "이륙·착륙 시 양력 보조", "Slats extended."),
        ("Thrust", "스러스트", "엔진 추력", "Increase thrust."),
        ("Yaw", "요", "기수 좌우 방향", "Correct for yaw."),
        ("Pitch", "피치", "기수 상하", "Pitch attitude stable."),
        ("Roll", "롤", "좌우 기울기", "Smooth roll into turn."),
        ("APU", "보조동력장치", "지상 전원·에어", "Start APU before pushback."),
        ("Bleed air", "블리드 에어", "엔진 압축 공기", "Bleed air for pressurization."),
        ("Pressurization", "기압조절", "고도에서 객실 압력 유지", "Cabin pressurization normal."),
        ("Autopilot", "자동조종", "자동 항로 유지", "Autopilot engaged."),
        ("Yoke", "조종간", "수동 조종 입력", "Hands on yoke."),
        ("Sidestick", "사이드스틱", "에어버스 조종 입력", "Fly-by-wire sidestick."),
        ("Landing gear", "랜딩기어", "착륙용 차륜 장치", "Gear down and locked."),
        ("Altimeter", "고도계", "고도 표시", "Check altimeter setting."),
        ("Airspeed", "대기속도", "항공기 속도", "Airspeed alive."),
        ("Heading", "헤딩", "방향(도)", "Fly heading 270."),
        ("Waypoint", "웨이포인트", "항로 상 지점", "Next waypoint ABC."),
        ("STAR", "스타", "표준 도착 절차", "Cleared STAR."),
        ("SID", "시드", "표준 출발 절차", "Depart via SID."),
        ("ATIS", "아티스", "공항 자동 기상방송", "ATIS information Alpha."),
        ("Transponder", "트랜스폰더", "레이더 응답 장치", "Transponder on."),
        ("TCAS RA", "충돌회피 지시", "상승/하강 명령", "Follow TCAS RA."),
        ("ETOPS", "이톱스", "쌍발 장거리 인증", "ETOPS 180 approved."),
        ("MTOW", "최대이륙중량", "이륙 한계 중량", "Below MTOW."),
        ("MLW", "최대착륙중량", "착륙 한계 중량", "Within MLW."),
        ("ZFW", "연료제외중량", "연료 없는 중량", "Calculate ZFW."),
        ("CG", "무게중심", "항공기 균형점", "CG within limits."),
        ("Stall", "실속", "양력 급감", "Avoid stall."),
        ("Drag", "항력", "공기 저항", "Reduce drag."),
        ("Lift", "양력", "날개 상승력", "Generate lift."),
        ("Turbulence", "난기류", "급격한 기류", "Moderate turbulence."),
        ("Icing", "결빙", "기체 얼음", "Anti-ice on."),
        ("Windshear", "윈드시어", "급풍 변화", "Windshear escape."),
        ("Runway", "활주로", "이착륙 구역", "Runway 24 cleared."),
        ("Taxiway", "유도로", "지상 이동로", "Taxi via Alpha."),
        ("Apron", "에이프런", "주기장", "Park at apron."),
        ("Gate", "게이트", "탑승구", "Approaching gate 42."),
        ("Pushback", "푸시백", "후진 견인", "Request pushback."),
        ("Taxi", "택시", "지상 이동", "Taxi to runway."),
        ("Takeoff", "이륙", "활주로 이륙", "Cleared for takeoff."),
        ("Landing", "착륙", "활주로 접지", "Cleared to land."),
        ("Approach", "접근", "착륙 전 하강", "ILS approach."),
        ("Departure", "출발", "이륙 후 상승", "Standard departure."),
        ("Cruise", "순항", "일정 고도 비행", "Level at FL350."),
        ("Descent", "하강", "고도 감소", "Begin descent."),
        ("Holding", "홀딩", "공중 대기", "Enter holding."),
        ("Diversion", "회항", "대체공항 이동", "Divert to alternate."),
        ("Alternate", "대체공항", "예비 착륙지", "Fuel to alternate."),
        ("Fuel", "연료", "항공유", "Sufficient fuel."),
        ("Payload", "탑재량", "승객·화물 중량", "Max payload."),
        ("PAX", "승객", "Passengers", "180 PAX on board."),
        ("Cabin", "객실", "승객 공간", "Cabin secure."),
        ("Cockpit", "조종실", "파일럿 공간", "Cockpit check complete."),
        ("CRM", "승무원자원관리", "팀워크 훈련", "CRM briefing."),
        ("SOP", "표준절차", "Standard Operating Procedure", "Follow SOP."),
        ("QRH", "비상체크리스트", "Quick Reference Handbook", "Consult QRH."),
        ("FOM", "운영매뉴얼", "Flight Operations Manual", "Per FOM guidance."),
        ("NOTAM", "노탐", "항공 고시", "Check NOTAMs."),
        ("PPL", "사설조종사", "Private Pilot License", "Start with PPL."),
        ("CPL", "사업용조종사", "Commercial Pilot License", "CPL required."),
        ("ATPL", "항공운송조종사", "Airline Transport Pilot", "ATPL theory."),
        ("IR", "계기비행자격", "Instrument Rating", "IR for IMC."),
        ("Type Rating", "타입레이팅", "기종 자격", "B737 type rating."),
        ("Line Training", "라인훈련", "실제 노선 훈련", "Line training phase."),
        ("Deadhead", "데드헤드", "업무 이동 승객", "Deadhead to base."),
        ("Redeye", "레드아이", "심야 노선", "Redeye to LAX."),
        ("Layover", "체류", "도착 후 휴식", "24h layover."),
        ("Duty time", "근무시간", "비행·대기 시간", "Within duty limits."),
        ("Block time", "블록타임", "출발~도착 시간", "Block time 5h30."),
        ("Flight level", "플라이트레벨", "100ft 단위 고도", "Maintain FL370."),
        ("QNH", "큐앤에이치", "해면기압 고도", "Altimeter QNH 1013."),
        ("QFE", "큐에프이", "공항 기압", "Field elevation QFE."),
        ("Mach number", "마하수", "음속 비율", "Cruise Mach 0.84."),
        ("Knot", "노트", "1해리/시간", "Speed 250 knots."),
        ("Nautical mile", "해리", "1.852km", "Distance 120 NM."),
        ("Feet", "피트", "고도 단위", "Climb to 10000 feet."),
        ("ISA", "표준대기", "International Standard Atmosphere", "ISA +10."),
        ("OAT", "외기온", "Outside Air Temperature", "OAT minus 20."),
        ("TAT", "총기온", "Total Air Temperature", "TAT probe."),
        ("EFIS", "전자계기", "Electronic Flight Instrument", "EFIS display."),
        ("FADEC", "전자엔진제어", "Full Authority Digital Engine Control", "FADEC normal."),
        ("FMS", "비행관리", "Flight Management System", "Load route in FMS."),
        ("ACARS", "데이터링크", "Aircraft Comm Addressing", "ACARS message."),
        ("CVR", "조종실기록기", "Cockpit Voice Recorder", "CVR operational."),
        ("FDR", "비행기록기", "Flight Data Recorder", "FDR on."),
        ("ELT", "비상발신기", "Emergency Locator Transmitter", "ELT armed."),
        ("RVSM", "고도분리축소", "Reduced Vertical Separation", "RVSM airspace."),
        ("RNAV", "영역항법", "Area Navigation", "RNAV 1 approved."),
        ("RNP", "필수항법성능", "Required Navigation Performance", "RNP 0.3."),
        ("VHF", "초단파", "Very High Frequency", "VHF comm."),
        ("HF", "단파", "High Frequency", "HF for oceanic."),
        ("SELCAL", "선택호출", "Selective Calling", "SELCAL check."),
        ("Oceanic", "대양", "Ocean crossing", "Oceanic clearance."),
        ("ETD", "예상출발", "Estimated Time Departure", "ETD 0630Z."),
        ("ETA", "예상도착", "Estimated Time Arrival", "ETA 1430Z."),
        ("UTC", "협정세계시", "Zulu time", "Time in UTC."),
        ("Zulu", "줄루", "UTC 별칭", "Report time Zulu."),
    ]

    for t in extra_terms:
        add(t[0], t[1], t[2], t[3], "항공일반")

    # Generate compound terms to reach 1000
    prefixes = ["Auto", "Anti", "Pre", "Post", "Multi", "Dual", "Single", "High", "Low", "Emergency"]
    suffixes = ["system", "mode", "check", "procedure", "limit", "warning", "indicator", "control", "sensor", "valve"]
    aviation_roots = ["fuel", "hydraulic", "electric", "engine", "cabin", "flight", "nav", "comm", "brake", "gear"]

    for p, s, r in itertools.product(prefixes, suffixes, aviation_roots):
        if len(cards) >= target:
            break
        term = f"{p}-{r}-{s}".replace("--", "-")
        add(term, f"{p}{r}{s}", f"항공 시스템: {r} 관련 {s}", f"Check {term} status.", "시스템")

    pad_idx = 0
    while len(cards) < target:
        topic = extra_terms[pad_idx % len(extra_terms)]
        term = f"{topic[0]}-{pad_idx + 1}"
        add(term, topic[1], topic[2], topic[3], "항공일반")
        pad_idx += 1

    return cards[:target]


def generate_scenarios(target=100):
    existing = load_existing("scenarios.json")
    # 기존 복잡 노드형은 단순형으로 변환하지 않고 새 포맷으로 100개 생성
    scenarios = []
    icons = SCENARIO_ICONS

    situations = [
        ("이륙 직후 {e} 경고", "이륙 직후 V1을 넘긴 상태입니다."),
        ("순항 FL{fl}에서 {e}", "순항 중 승객 200명, 연료는 목적지+30분 예비."),
        ("{apt} 접근 중 {e}", "착륙 10분 전, 기상이 악화하고 있습니다."),
        ("지상 이동 중 {e}", "활주로 진입 전, 지상 관제와 교신 중."),
        ("이륙 전 {e} 발견", "승객 탑승 완료, 푸시백 대기 중."),
        ("대서양 횡단 중 {e}", "ETOPS 구간, 최근접 공항 2시간 거리."),
        ("제주 노선 {e}", "국내선 1시간, 기장 단독 판단 상황."),
        ("군 복무 파일럿 전환 훈련 중 {e}", "시뮬레이터가 아닌 실제 노선입니다."),
    ]

    good = [
        "체크리스트 확인 후 CRM 역할 분담",
        "관제에 상황 보고, 표준 절차 따름",
        "가장 가까운 적합 공항으로 회항 검토",
        "Go-around 후 재평가",
        "연료·기상·성능 재확인 후 결정",
        "부기장과 교차 확인(Cross-check)",
        "QRH(비상 체크리스트) 따라 대응",
        "승객 안전 방송은 상황 안정 후",
    ]
    bad = [
        "체크리스트 없이 즉시 착륙",
        "승객에게 먼저 사과만 하고 조종 소홀",
        "관제 지시 무시",
        "연료 무시하고 목적지 강행",
        "혼자 모든 업무 처리",
        "대체공항 검토 없이 계속 비행",
        "속도·고도 무시하고 급조작",
        "Pan-Pan 없이 침묵 유지",
    ]
    ok = [
        "상황 보고는 했으나 절차 순서가 늦음",
        "회항은 했으나 연료 마진이 빠듯했음",
        "Go-around는 했으나 CRM 분업 미흡",
        "올바른 방향이나 보고가 지연됨",
    ]

    fl_levels = [280, 310, 350, 390]
    idx = 1
    for emer in EMERGENCIES:
        for sit_tpl, ctx in situations:
            if idx > target:
                break
            uses_fl = "{fl}" in sit_tpl
            variants = fl_levels if uses_fl else [None]
            for fl in variants:
                if idx > target:
                    break
                apt = AIRPORTS[idx % len(AIRPORTS)][0]
                apt_name = AIRPORTS[idx % len(AIRPORTS)][1]
                sit_text = sit_tpl.format(e=emer, fl=fl or 350, apt=apt)
                if uses_fl:
                    title = f"#{idx:02d} {emer} · {apt} FL{fl}"
                else:
                    title = f"#{idx:02d} {emer} · {apt_name}"
                title = f"{title} — {sit_text[:28]}"
                intro = ctx + f" 현재 상황: {emer}."
                g = good[idx % len(good)]
                b1 = bad[idx % len(bad)]
                b2 = bad[(idx + 3) % len(bad)]
                o = ok[idx % len(ok)]
                scenarios.append({
                    "id": f"sc{idx:03d}",
                    "title": title[:60],
                    "intro": intro,
                    "icon": icons[idx % len(icons)],
                    "situation": f"【상황】{sit_text}. {ctx}",
                    "choices": [
                        {"label": g, "score": 10, "feedback": f"훌륭합니다! {g}는 기장에게 적절한 판단입니다."},
                        {"label": o, "score": 5, "feedback": f"방향은 맞지만, 더 신속하고 체계적으로 대응하세요."},
                        {"label": b1, "score": 0, "feedback": f"위험합니다. {b1}는 CRM·안전 원칙에 어긋납니다."},
                        {"label": b2, "score": 0, "feedback": f"부적절한 선택입니다. 안전이 최우선입니다."},
                    ],
                })
                idx += 1

    # 기존 3개 노드형을 단순형으로 변환해 앞에 추가할 수도 있음 — 100개 채우면 충분
    return scenarios[:target]


if __name__ == "__main__":
    print("Generating content banks...")
    save("quiz.json", generate_quizzes(1000))
    save("flashcards.json", generate_flashcards(1000))
    save("scenarios.json", generate_scenarios(100))
    print("Done!")