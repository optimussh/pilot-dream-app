import json

# Load existing data
with open("data/atc_phrases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 30 realistic and commonly used Passenger Announcements
pa_announcements = [
    {
        "en": "Ladies and gentlemen, welcome aboard Korean Air flight KE001 to Los Angeles.",
        "pron": "레이디스 앤 젠틀맨, 웰컴 어보드 코리안 에어 플라이트 KE001 투 로스앤젤레스.",
        "ko": "신사 숙녀 여러분, 대한항공 KE001편 로스앤젤레스행에 탑승하신 것을 환영합니다."
    },
    {
        "en": "For your safety, please place all electronic devices in airplane mode.",
        "pron": "포 유어 세이프티, 플리즈 플레이스 올 일렉트로닉 디바이시스 인 에어플레인 모드.",
        "ko": "안전을 위해 모든 전자기기를 비행기 모드로 전환해 주시기 바랍니다."
    },
    {
        "en": "Please fasten your seatbelts and return your seat backs and tray tables to their upright positions.",
        "pron": "플리즈 패슨 유어 시트벨츠 앤 리턴 유어 시트 백스 앤 트레이 테이블스 투 데어 업라이트 포지션스.",
        "ko": "좌석 벨트를 매주시고 좌석 등받이와 트레이 테이블을 원래 위치로 되돌려 주십시오."
    },
    {
        "en": "In the event of a loss of cabin pressure, oxygen masks will drop from the overhead compartments.",
        "pron": "인 디 이벤트 오브 어 로스 오브 캐빈 프레셔, 옥시전 마스크스 윌 드롭 프롬 디 오버헤드 컴파트먼츠.",
        "ko": "만약 기내 압력이 떨어지면 위 선반에서 산소마스크가 내려옵니다."
    },
    {
        "en": "Please secure your own mask before assisting others.",
        "pron": "플리즈 시큐어 유어 오운 마스크 비포 어시스팅 아더스.",
        "ko": "다른 사람을 돕기 전에 먼저 본인의 마스크를 착용해 주십시오."
    },
    {
        "en": "Your life vest is located under your seat. Please do not inflate it inside the aircraft.",
        "pron": "유어 라이프 베스트 이즈 로케이티드 언더 유어 시트. 플리즈 두 낫 인플레이트 잇 인사이드 디 에어크래프트.",
        "ko": "구명조끼는 좌석 아래에 있습니다. 기내에서는 절대 부풀리지 마십시오."
    },
    {
        "en": "There are emergency exits located at the front, over the wings, and at the rear of the aircraft.",
        "pron": "데어 아 에머전시 이그짓츠 로케이티드 앳 더 프론트, 오버 더 윙스, 앤 앳 더 리어 오브 디 에어크래프트.",
        "ko": "비상구는 전방, 날개 위, 그리고 후방에 있습니다."
    },
    {
        "en": "We are currently taxiing to the runway. Please remain seated with your seatbelt fastened.",
        "pron": "위 아 커렌틀리 택시잉 투 더 런웨이. 플리즈 리메인 시티드 위드 유어 시트벨트 패슨드.",
        "ko": "현재 활주로로 이동 중입니다. 안전벨트를 매고 좌석에 앉아 계셔 주십시오."
    },
    {
        "en": "Cabin crew, please prepare for takeoff.",
        "pron": "캐빈 크루, 플리즈 프리페어 포 테이크오프.",
        "ko": "객실 승무원 여러분, 이륙 준비를 해주십시오."
    },
    {
        "en": "We have reached our cruising altitude. You may now use electronic devices in airplane mode.",
        "pron": "위 해브 리치드 아워 크루징 알티튜드. 유 메이 나우 유스 일렉트로닉 디바이시스 인 에어플레인 모드.",
        "ko": "순항 고도에 도달했습니다. 이제 전자기기를 비행기 모드로 사용하실 수 있습니다."
    },
    {
        "en": "Due to turbulence, the seatbelt sign has been turned on. Please return to your seats.",
        "pron": "듀 투 터뷸런스, 더 시트벨트 사인 해즈 빈 턴드 온. 플리즈 리턴 투 유어 시츠.",
        "ko": "난기류로 인해 안전벨트 사인이 켜졌습니다. 좌석으로 돌아가 주십시오."
    },
    {
        "en": "Ladies and gentlemen, the meal service will begin shortly from the rear of the aircraft.",
        "pron": "레이디스 앤 젠틀맨, 더 밀 서비스 윌 비긴 쇼틀리 프롬 더 리어 오브 디 에어크래프트.",
        "ko": "식사 서비스를 기체 후방부터 시작하겠습니다."
    },
    {
        "en": "Please return your tray tables to the upright position as we prepare for landing.",
        "pron": "플리즈 리턴 유어 트레이 테이블스 투 디 업라이트 포지션 애즈 위 프리페어 포 랜딩.",
        "ko": "착륙 준비를 위해 트레이 테이블을 원래 위치로 되돌려 주십시오."
    },
    {
        "en": "We are now beginning our descent into Incheon International Airport.",
        "pron": "위 아 나우 비기닝 아워 디센트 인투 인천 인터내셔널 에어포트.",
        "ko": "인천국제공항으로 하강을 시작합니다."
    },
    {
        "en": "Cabin crew, please take your seats for landing.",
        "pron": "캐빈 크루, 플리즈 테이크 유어 시츠 포 랜딩.",
        "ko": "객실 승무원 여러분, 착륙을 위해 좌석에 앉아 주십시오."
    },
    {
        "en": "Please remain in your seats with your seatbelts fastened until the aircraft has come to a complete stop.",
        "pron": "플리즈 리메인 인 유어 시츠 위드 유어 시트벨츠 패슨드 언틸 디 에어크래프트 해즈 컴 투 어 컴플리트 스탑.",
        "ko": "항공기가 완전히 정지할 때까지 안전벨트를 매고 좌석에 앉아 계셔 주십시오."
    },
    {
        "en": "Thank you for flying with Korean Air. We hope you had a pleasant flight.",
        "pron": "땡큐 포 플라잉 위드 코리안 에어. 위 호프 유 해드 어 플레전트 플라이트.",
        "ko": "대한항공을 이용해 주셔서 감사합니다. 즐거운 비행이 되셨기를 바랍니다."
    },
    {
        "en": "For passengers with connecting flights, please check the departure information on the screens.",
        "pron": "포 패신저스 위드 커넥팅 플라이트스, 플리즈 체크 더 디파처 인포메이션 온 더 스크린스.",
        "ko": "연결편을 이용하시는 승객께서는 스크린의 출발 정보를 확인해 주시기 바랍니다."
    },
    {
        "en": "Your checked baggage will be available at baggage claim carousel number 7.",
        "pron": "유어 체크드 뱃기지 윌 비 어베일러블 앳 뱃기지 클레임 캐러셀 넘버 7.",
        "ko": "위탁 수하물은 7번 캐러셀에서 찾으실 수 있습니다."
    },
    {
        "en": "Please be careful when opening the overhead bins, as baggage may have shifted during the flight.",
        "pron": "플리즈 비 케어풀 웬 오프닝 디 오버헤드 빈스, 애즈 뱃기지 메이 해브 시프티드 듀링 더 플라이트.",
        "ko": "비행 중 물건이 이동했을 수 있으니, 위 선반을 열 때 주의해 주십시오."
    },
    {
        "en": "We will be landing in approximately 15 minutes. Please prepare for arrival.",
        "pron": "위 윌 비 랜딩 인 어프록시메이트리 15 미닛츠. 플리즈 프리페어 포 어리벌.",
        "ko": "약 15분 후 착륙합니다. 도착 준비를 해주시기 바랍니다."
    },
    {
        "en": "Welcome to Incheon International Airport. The local time is now 4:20 PM.",
        "pron": "웰컴 투 인천 인터내셔널 에어포트. 더 로컬 타임 이즈 나우 4:20 PM.",
        "ko": "인천국제공항에 오신 것을 환영합니다. 현재 현지 시간은 오후 4시 20분입니다."
    },
    {
        "en": "If you require special assistance, our staff will be happy to help you.",
        "pron": "이프 유 리콰이어 스페셜 어시스턴스, 아워 스태프 윌 비 해피 투 헬프 유.",
        "ko": "특별한 도움이 필요하시면 직원이 도와드리겠습니다."
    },
    {
        "en": "The use of mobile phones is now permitted.",
        "pron": "더 유스 오브 모바일 폰스 이즈 나우 퍼미티드.",
        "ko": "이제 휴대전화 사용이 가능합니다."
    },
    {
        "en": "We are currently experiencing light turbulence. Please remain seated with your seatbelt fastened.",
        "pron": "위 아 커렌틀리 익스피리언싱 라이트 터뷸런스. 플리즈 리메인 시티드 위드 유어 시트벨트 패슨드.",
        "ko": "현재 약한 난기류가 있습니다. 안전벨트를 매고 좌석에 앉아 계셔 주십시오."
    },
    {
        "en": "Thank you for your attention during the safety demonstration.",
        "pron": "땡큐 포 유어 어텐션 듀링 더 세이프티 데몬스트레이션.",
        "ko": "안전 시범 방송에 주의해 주셔서 감사합니다."
    },
    {
        "en": "For passengers seated in the emergency exit rows, please review the safety card in the seat pocket.",
        "pron": "포 패신저스 시티드 인 디 에머전시 이그짓 로우스, 플리즈 리뷰 더 세이프티 카드 인 더 시트 포켓.",
        "ko": "비상구 좌석에 앉으신 승객께서는 좌석 주머니의 안전 카드를 확인해 주십시오."
    },
    {
        "en": "We would like to thank you for choosing Korean Air for your travel today.",
        "pron": "위 우드 라이크 투 땡크 유 포 추징 코리안 에어 포 유어 트래블 투데이.",
        "ko": "오늘 대한항공을 이용해 주셔서 진심으로 감사드립니다."
    },
    {
        "en": "Have a wonderful stay in Korea or continue safely to your final destination.",
        "pron": "해브 어 원더풀 스테이 인 코리아 오어 컨티뉴 세이프리 투 유어 파이널 데스티네이션.",
        "ko": "한국에서의 즐거운 체류가 되시거나, 최종 목적지까지 안전한 여행 되시기 바랍니다."
    },
    {
        "en": "It has been our pleasure serving you on this flight. Goodbye.",
        "pron": "잇 해즈 빈 아워 플레저 서빙 유 온 디스 플라이트. 굿바이.",
        "ko": "이번 비행 동안 모시게 되어 영광이었습니다. 안녕히 가십시오."
    }
]

# Add the new category
data["기내 방송 (Passenger Announcements)"] = pa_announcements

# Save back
with open("data/atc_phrases.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("성공적으로 기내 방송 카테고리 30개를 추가했습니다.")
print("현재 총 문장 수:", sum(len(v) for v in data.values()))
