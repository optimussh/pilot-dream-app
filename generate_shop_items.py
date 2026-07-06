"""상점 아이템 카탈로그 생성 (~160개)"""
import json
import os

OUT = os.path.join(os.path.dirname(__file__), 'data', 'shop_items.json')

RARITY_PRICE = {
    'common': (300_000, 800_000),
    'uncommon': (800_000, 1_500_000),
    'rare': (1_500_000, 3_000_000),
    'epic': (3_000_000, 6_000_000),
    'legendary': (6_000_000, 15_000_000),
}

ALL_AC = ['*']
NARROW = ['b737', 'b737max', 'a320', 'a320neo', 'a321', 'a321neo', 'b757', 'a220', 'e190', 'e195']
WIDE = ['a330', 'a330neo', 'a350', 'a3501000', 'b787', 'b78710', 'b777', 'b777x', 'b767', 'a380', 'b747']
CARGO = ['b777f', 'b747f', 'a330f', 'b767f', 'md11f', 'an124', 'an225']
CLASSIC = ['b707', 'dc10', 'md80', 'tu154', 'concorde', 'b747sp', 'md11']

items = []

def add(item):
    items.append(item)

def price_for(rarity, offset=0):
    lo, hi = RARITY_PRICE[rarity]
    step = (hi - lo) // 5
    return lo + step * (offset % 5)

# ── 아바타: 머리 (20) ──
HEADS = [
    ('av_cap_ke', '대한항공 캡', '🧢', 'common', 'KE 시그니처 블루 캡'),
    ('av_cap_oz', '아시아나 캡', '🎩', 'common', 'OZ 퍼플 캡'),
    ('av_cap_7c', '제주항공 캡', '🧢', 'common', '7C 오렌지 캡'),
    ('av_cap_jin', '진에어 캡', '🧢', 'common', 'LJ 민트 캡'),
    ('av_cap_tway', '티웨이 캡', '🧢', 'common', 'TW 레드 캡'),
    ('av_cap_ana', 'ANA 캡', '🧢', 'uncommon', '일본 ANA 블루'),
    ('av_cap_jal', 'JAL 캡', '🧢', 'uncommon', '일본 JAL 크림슨'),
    ('av_cap_singapore', '싱가포르 캡', '🎩', 'uncommon', 'SQ 슬림 캡'),
    ('av_cap_emirates', '에미레이트 캡', '🎩', 'rare', 'EK 골드 캡'),
    ('av_cap_lufthansa', '루프트한자 캡', '🎩', 'uncommon', 'LH 옐로우 캡'),
    ('av_cap_delta', '델타 캡', '🧢', 'uncommon', 'DL 네이비 캡'),
    ('av_cap_qantas', '콴타스 캡', '🧢', 'uncommon', 'QF 루프 캡'),
    ('av_headset_pro', '프로 헤드셋', '🎧', 'common', 'Bose ANR 헤드셋'),
    ('av_headset_gold', '골드 마이크 헤드셋', '🎧', 'rare', '골드 마이크 암'),
    ('av_helmet', '비행 헬멧', '⛑️', 'uncommon', '헬리콥터/군용 스타일'),
    ('av_cap_cargo', '카고 파일럿 캡', '🧢', 'common', '화물기 전용 캡'),
    ('av_cap_vintage', '빈티지 파일럿 캡', '🎩', 'rare', '1950년대 가죽 캡'),
    ('av_cap_neon', '네온 파일럿 캡', '🧢', 'epic', '야광 네온 캡'),
    ('av_cap_captain_gold', '골드 기장 캡', '👑', 'legendary', '황금 기장 전용'),
    ('av_headset_cat', '고양이 귀 헤드셋', '🐱', 'epic', '귀여운 파일럿 에디션'),
]
for i, (id_, name, emoji, rarity, desc) in enumerate(HEADS):
    add({'id': id_, 'name': name, 'category': 'avatar', 'slot': 'head', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity, 'desc': desc, 'sellable': True})

# ── 아바타: 유니폼 (20) ──
UNIFORMS = [
    ('av_uni_student', '비행학원 조끼', '🦺', 'common', '학생 파일럿 에폴렌'),
    ('av_uni_lcc', 'LCC 조끼', '🦺', 'common', '저비용 항공사 조끼'),
    ('av_uni_fo', '부기장 재킷', '👔', 'uncommon', '3스트라이프 부기장'),
    ('av_uni_captain', '기장 재킷', '🥼', 'rare', '4스트라이프 기장'),
    ('av_uni_senior', '최고기장 재킷', '🥼', 'epic', '5스트라이프 시니어'),
    ('av_uni_ke', '대한항공 유니폼', '👔', 'uncommon', 'KE 네이비 정장'),
    ('av_uni_oz', '아시아나 유니폼', '👔', 'uncommon', 'OZ 퍼플 정장'),
    ('av_uni_cargo', '카고 조종사 조끼', '🦺', 'common', '화물기 주황 조끼'),
    ('av_uni_winter', '겨울 파일럿 코트', '🧥', 'uncommon', '눈 오는 날 방한 코트'),
    ('av_uni_summer', '여름 반팔 유니폼', '👕', 'common', '열대 노선 반팔'),
    ('av_uni_military', '군용 비행복', '🪖', 'rare', '공군 파일럿 스타일'),
    ('av_uni_business', '비즈니스 제트 유니폼', '🤵', 'rare', '프라이빗 제트 승무원'),
    ('av_uni_retro', '레트로 유니폼', '👔', 'epic', '1970 Pan Am 스타일'),
    ('av_uni_neon', '네온 유니폼', '🦺', 'epic', '사이버 파일럿'),
    ('av_uni_space', '우주 파일럿 슈트', '🧑‍🚀', 'legendary', '미래형 파일럿'),
    ('av_uni_legend', '전설의 기장 코트', '🥼', 'legendary', '황금 단추 기장 코트'),
    ('av_uni_trainee', '견습 조종사 조끼', '🦺', 'common', '첫 솔로 비행 기념'),
    ('av_uni_instructor', '교관 유니폼', '👔', 'rare', '비행교관 블랙 재킷'),
    ('av_uni_cargo_ke', '대한항공 카고', '🦺', 'uncommon', 'KE 카고 전용'),
    ('av_uni_hawaiian', '하와이안 셔츠', '🌺', 'uncommon', '휴양지 노선 셔츠'),
]
for i, (id_, name, emoji, rarity, desc) in enumerate(UNIFORMS):
    add({'id': id_, 'name': name, 'category': 'avatar', 'slot': 'uniform', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity, 'desc': desc, 'sellable': True})

# ── 아바타: 악세서리 (24) ──
ACCESSORIES = [
    ('av_acc_aviator', '에비에이터 선글라스', '🕶️', 'common', '클래식 파일럿 선글라스'),
    ('av_acc_tie', '실크 넥타이', '👔', 'common', '기장 넥타이'),
    ('av_acc_bowtie', '나비넥타이', '🎀', 'uncommon', '정식 기내 복장'),
    ('av_acc_watch', '파일럿 시계', '⌚', 'uncommon', '크로노그래프 시계'),
    ('av_acc_briefcase', '비행 서류가방', '💼', 'common', 'Jeppesen 차트 가방'),
    ('av_acc_epaulette', '견장 세트', '⭐', 'uncommon', '어깨 견장'),
    ('av_acc_scarf', '실크 스카프', '🧣', 'common', '겨울 비행 스카프'),
    ('av_acc_gloves', '비행 장갑', '🧤', 'common', '가죽 조종 장갑'),
    ('av_acc_badge_id', '사원증', '🪪', 'common', '항공사 ID 카드'),
    ('av_acc_pen', '만년필', '🖊️', 'common', '로그북 서명용'),
    ('av_acc_chart', '접이식 차트', '🗺️', 'uncommon', '종이 항공차트'),
    ('av_acc_ipad', 'EFB 태블릿', '📱', 'rare', '전자비행화면'),
    ('av_acc_torch', '조종실 손전등', '🔦', 'common', '비상 손전등'),
    ('av_acc_medal', '훈장', '🏅', 'rare', '우수 파일럿 훈장'),
    ('av_acc_coffee', '조종사 커피', '☕', 'common', '새벽 비행 필수템'),
    ('av_acc_snack', '에너지 바', '🍫', 'common', '장거리 비행 간식'),
    ('av_acc_lucky', '행운의 부적', '🍀', 'uncommon', '비행 전 루틴'),
    ('av_acc_patch_nasa', 'NASA 패치', '🚀', 'rare', 'NASA 미션 패치'),
    ('av_acc_patch_world', '세계일주 패치', '🌍', 'epic', '라운드 더 월드'),
    ('av_acc_gold_pen', '골드 만년필', '🖊️', 'epic', '기장 전용 골드펜'),
    ('av_acc_diamond_watch', '다이아 시계', '⌚', 'legendary', '다이아 베젤 시계'),
    ('av_acc_comm_badge', '통신 뱃지', '📡', 'uncommon', 'ATC 통신 자격'),
    ('av_acc_sunglass_mirror', '미러 선글라스', '🕶️', 'uncommon', '미러 코팅'),
    ('av_acc_headband', '땀밴드', '🎗️', 'common', '더운 날 비행용'),
]
for i, (id_, name, emoji, rarity, desc) in enumerate(ACCESSORIES):
    add({'id': id_, 'name': name, 'category': 'avatar', 'slot': 'accessory', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity, 'desc': desc, 'sellable': True})

# ── 아바타: 윙 (16) ──
WINGS = [
    ('av_wing_student', '학생 윙', '🪽', 'common', '비행학원 졸업 윙'),
    ('av_wing_silver', '실버 윙', '🪽', 'uncommon', '은색 조종사 윙'),
    ('av_wing_gold', '골드 윙', '✨', 'rare', '황금 기장 윙'),
    ('av_wing_platinum', '플래티넘 윙', '💫', 'epic', '플래티넘 윙'),
    ('av_wing_diamond', '다이아 윙', '💎', 'legendary', '전설의 다이아 윙'),
    ('av_wing_cargo', '카고 윙', '📦', 'uncommon', '화물기 전용 윙'),
    ('av_wing_military', '군용 윙', '🎖️', 'rare', '공군 파일럿 윙'),
    ('av_wing_instructor', '교관 윙', '📚', 'rare', '비행교관 윙'),
    ('av_wing_night', '야간 비행 윙', '🌙', 'uncommon', '야간 자격 윙'),
    ('av_wing_instrument', '계기비행 윙', '🧭', 'uncommon', 'IFR 자격 윙'),
    ('av_wing_ocean', '대양횡단 윙', '🌊', 'epic', '대서양 횡단 기념'),
    ('av_wing_polar', '극지 비행 윙', '❄️', 'epic', '북극 항로 윙'),
    ('av_wing_1000h', '1000시간 윙', '🏆', 'rare', '1000시간 기념'),
    ('av_wing_captain_star', '기장 스타', '⭐', 'epic', '기장 승격 기념'),
    ('av_wing_rainbow', '레인보우 윙', '🌈', 'legendary', '프라이드 에디션'),
    ('av_wing_neon', '네온 윙', '💡', 'epic', '야광 윙'),
]
for i, (id_, name, emoji, rarity, desc) in enumerate(WINGS):
    add({'id': id_, 'name': name, 'category': 'avatar', 'slot': 'wings', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity, 'desc': desc, 'sellable': True})

# ── 리버리 (48) ──
LIVERIES = [
    ('lv_ke', '대한항공 스카이블루', '🔵', '#004B9C', 'uncommon', NARROW + WIDE, 'KE 클래식'),
    ('lv_oz', '아시아나 퍼플', '🟣', '#4B0082', 'uncommon', NARROW + WIDE, 'OZ 시그니처'),
    ('lv_7c', '제주항공 오렌지', '🟠', '#FF6600', 'common', NARROW, '7C LCC'),
    ('lv_jin', '진에어 민트', '🩵', '#00B4B4', 'common', NARROW, 'LJ 민트'),
    ('lv_tway', '티웨이 레드', '🔴', '#E60012', 'common', NARROW, 'TW 레드'),
    ('lv_airbus', '에어버스 화이트', '⬜', '#F0F0F0', 'common', NARROW + WIDE, '에어버스 기본'),
    ('lv_boeing', '보잉 블루', '🔷', '#0039A6', 'common', NARROW + WIDE, '보잉 기본'),
    ('lv_ana', 'ANA 블루', '🔵', '#003087', 'uncommon', NARROW + WIDE, '일본 ANA'),
    ('lv_jal', 'JAL 크림슨', '🔴', '#CC0000', 'uncommon', NARROW + WIDE, '일본 JAL'),
    ('lv_singapore', '싱가포르', '🔷', '#003366', 'rare', WIDE, 'SQ 블루/골드'),
    ('lv_emirates', '에미레이트', '🟡', '#D4AF37', 'rare', WIDE, 'EK 골드'),
    ('lv_qantas', '콴타스', '🔴', '#E0001B', 'uncommon', WIDE, 'QF 루프'),
    ('lv_lufthansa', '루프트한자', '🟡', '#F9BA00', 'uncommon', WIDE, 'LH 옐로우'),
    ('lv_ba', '영국항공', '🔵', '#075AAA', 'uncommon', WIDE, 'BA 스피드마크'),
    ('lv_af', '에어프랑스', '🔵', '#002157', 'uncommon', WIDE, 'AF 스트라이프'),
    ('lv_klm', 'KLM 블루', '🔵', '#00A1DE', 'uncommon', WIDE, 'KLM 크라운'),
    ('lv_delta', '델타', '🔵', '#003366', 'uncommon', WIDE, 'DL 위젯'),
    ('lv_united', '유나이티드', '🔵', '#0033A0', 'uncommon', WIDE, 'UA 글로브'),
    ('lv_aa', '아메리칸', '🔵', '#0078D2', 'uncommon', WIDE, 'AA 테일'),
    ('lv_cathay', '캐세이퍼시픽', '🟢', '#006564', 'rare', WIDE, 'CX 그린'),
    ('lv_qatar', '카타르', '🟣', '#5C0632', 'rare', WIDE, 'QR 버건디'),
    ('lv_etihad', '에티하드', '🟡', '#C4A000', 'rare', WIDE, 'EH 골드'),
    ('lv_turkish', '터키항공', '🔴', '#C8102E', 'uncommon', WIDE, 'TK 레드'),
    ('lv_airnz', '에어뉴질랜드', '⚫', '#000000', 'uncommon', WIDE, 'NZ 블랙'),
    ('lv_jetstar', '젯스타', '🟠', '#FF6600', 'common', NARROW, 'JQ 오렌지'),
    ('lv_ryanair', '라이언에어', '🔵', '#003399', 'common', NARROW, 'FR 블루/옐로'),
    ('lv_easyjet', '이지젯', '🟠', '#FF6600', 'common', NARROW, 'U2 오렌지'),
    ('lv_peach', '피치', '🩷', '#FF69B4', 'common', NARROW, '일본 피치'),
    ('lv_vietjet', '비엣젯', '🔴', '#E60012', 'common', NARROW, '베트남 LCC'),
    ('lv_airasia', '에어아시아', '🔴', '#E4002B', 'common', NARROW, 'AK 레드'),
    ('lv_cargo_red', '카고 레드', '📦', '#CC0000', 'uncommon', CARGO, '화물기 레드'),
    ('lv_cargo_ke', '대한항공 카고', '📦', '#004B9C', 'uncommon', CARGO, 'KE 카고'),
    ('lv_cargo_fedex', '페덱스 퍼플', '🟣', '#4D148C', 'rare', CARGO, 'FX 퍼플/오렌지'),
    ('lv_cargo_ups', 'UPS 브라운', '🟤', '#351C15', 'rare', CARGO, 'UPS 브라운'),
    ('lv_retro_panam', 'Pan Am 레트로', '📘', '#1E3A8A', 'epic', CLASSIC, '1970 클래식'),
    ('lv_retro_twa', 'TWA 레트로', '🔴', '#CC0000', 'epic', CLASSIC, 'TWA 레드'),
    ('lv_retro_braniff', 'Braniff 컬러', '🌈', '#FF6600', 'epic', CLASSIC, '컬러풀 레트로'),
    ('lv_military_grey', '군용 그레이', '🪖', '#4A4A4A', 'rare', ['c130', 'b29'], '밀리터리 그레이'),
    ('lv_concorde', '콩코르드 화이트', '⬜', '#FFFFFF', 'legendary', ['concorde'], '초음속 화이트'),
    ('lv_neon_blue', '네온 블루', '💙', '#00BFFF', 'epic', ALL_AC, '네온 블루'),
    ('lv_neon_pink', '네온 핑크', '💗', '#FF69B4', 'epic', ALL_AC, '네온 핑크'),
    ('lv_camo', '카모플라주', '🌿', '#3D5C3D', 'rare', ALL_AC, '밀리터리 카모'),
    ('lv_gold_luxury', '골드 럭셔리', '✨', '#FFD700', 'legendary', WIDE, '골드 프리미엄'),
    ('lv_rainbow', '레인보우', '🌈', '#ff6b6b', 'legendary', ALL_AC, '모든 기종 적용'),
    ('lv_midnight', '미드나잇 블랙', '🌑', '#1a1a2e', 'rare', ALL_AC, '야간 블랙'),
    ('lv_sunset', '선셋 오렌지', '🌅', '#ff6b35', 'uncommon', ALL_AC, '석양 그라데이션'),
    ('lv_aurora', '오로라', '🌌', '#00ff88', 'legendary', ALL_AC, '북극광 컬러'),
]
for i, (id_, name, emoji, color, rarity, applies, desc) in enumerate(LIVERIES):
    add({'id': id_, 'name': name, 'category': 'livery', 'slot': 'livery', 'emoji': emoji,
         'color': color, 'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': applies, 'desc': desc, 'sellable': True})

# ── 데코 (32) ──
TRAILS = [
    ('dc_trail_green', '그린 트레일', '🟢', '#33ff33', 'common'),
    ('dc_trail_blue', '블루 트레일', '🔵', '#0A84FF', 'common'),
    ('dc_trail_purple', '퍼플 트레일', '💜', '#a855f7', 'uncommon'),
    ('dc_trail_gold', '골드 트레일', '✨', '#FFD700', 'rare'),
    ('dc_trail_red', '레드 트레일', '🔴', '#FF3333', 'uncommon'),
    ('dc_trail_cyan', '시안 트레일', '🩵', '#00FFFF', 'uncommon'),
    ('dc_trail_rainbow', '레인보우 트레일', '🌈', '#ff6b6b', 'epic'),
    ('dc_trail_fire', '파이어 트레일', '🔥', '#FF4500', 'epic'),
    ('dc_trail_ice', '아이스 트레일', '❄️', '#B0E0FF', 'rare'),
    ('dc_trail_star', '스타더스트', '⭐', '#FFFACD', 'legendary'),
]
for i, (id_, name, emoji, color, rarity) in enumerate(TRAILS):
    add({'id': id_, 'name': name, 'category': 'deco', 'slot': 'trail', 'emoji': emoji,
         'color': color, 'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': ALL_AC, 'desc': f'레이더 {name}', 'sellable': True})

CALLSIGNS = [
    ('dc_cs_silver', '실버 콜사인', '🏷️', '#C0C0C0', 'common'),
    ('dc_cs_gold', '골드 콜사인', '🏷️', '#FFD700', 'uncommon'),
    ('dc_cs_neon', '네온 콜사인', '🏷️', '#00ff88', 'rare'),
    ('dc_cs_vintage', '빈티지 콜사인', '🏷️', '#8B7355', 'uncommon'),
]
for i, (id_, name, emoji, color, rarity) in enumerate(CALLSIGNS):
    add({'id': id_, 'name': name, 'category': 'deco', 'slot': 'callsign', 'emoji': emoji,
         'color': color, 'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': ALL_AC, 'desc': f'{name} 플레이트', 'sellable': True})

COCKPIT = [
    ('dc_ck_plant', '콕핏 화분', '🪴', 'common', '대시보드 화분'),
    ('dc_ck_photo', '가족 사진', '🖼️', 'common', '조종석 사진'),
    ('dc_ck_mascot', '행운 마스코트', '🧸', 'uncommon', '곰돌이 인형'),
    ('dc_ck_patch', '패치 보드', '📌', 'uncommon', '패치 모음'),
    ('dc_ck_coffee', '커피 홀더', '☕', 'common', '조종석 커피'),
    ('dc_ck_chart', '종이 차트', '🗺️', 'common', '종이 항로도'),
    ('dc_ck_lucky', '행운 부적', '🍀', 'uncommon', '비행 전 부적'),
    ('dc_ck_gold', '골드 컨트롤', '🎮', 'epic', '골드 조종간 커버'),
]
for i, (id_, name, emoji, rarity, desc) in enumerate(COCKPIT):
    add({'id': id_, 'name': name, 'category': 'deco', 'slot': 'cockpit', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': ALL_AC, 'desc': desc, 'sellable': True})

STICKERS = [
    ('dc_st_star', '별 스티커', '⭐', 'common'), ('dc_st_heart', '하트 스티커', '❤️', 'common'),
    ('dc_st_flag_kr', '태극기 스티커', '🇰🇷', 'common'), ('dc_st_flag_us', '미국 스티커', '🇺🇸', 'common'),
    ('dc_st_flag_jp', '일본 스티커', '🇯🇵', 'common'), ('dc_st_flag_uk', '영국 스티커', '🇬🇧', 'common'),
    ('dc_st_lightning', '번개 스티커', '⚡', 'uncommon'), ('dc_st_skull', '해적 스티커', '☠️', 'rare'),
    ('dc_st_diamond', '다이아 스티커', '💎', 'epic'), ('dc_st_crown', '왕관 스티커', '👑', 'legendary'),
]
for i, (id_, name, emoji, rarity) in enumerate(STICKERS):
    add({'id': id_, 'name': name, 'category': 'deco', 'slot': 'sticker', 'emoji': emoji,
         'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': ALL_AC, 'desc': f'기체 외부 {name}', 'sellable': True})

# ── 라운지 (20) ──
LOUNGES = [
    ('lg_radar_classic', '클래식 레이더', '🟢', '#33ff33', 'radar_skin', 'uncommon', '그린 관제'),
    ('lg_radar_sapphire', '사파이어 레이더', '🔵', '#0A84FF', 'radar_skin', 'rare', '블루 관제'),
    ('lg_radar_amber', '앰버 레이더', '🟡', '#ffaa00', 'radar_skin', 'uncommon', '앰버 관제'),
    ('lg_radar_red', '레드 얼럿 레이더', '🔴', '#FF3333', 'radar_skin', 'rare', '레드 관제'),
    ('lg_radar_matrix', '매트릭스 레이더', '💚', '#00ff41', 'radar_skin', 'epic', '해커 스타일'),
    ('lg_dash_night', '야간 계기판', '🌙', '#0a0a1a', 'dashboard_bg', 'uncommon', '야간 모드'),
    ('lg_dash_sunset', '석양 코크핏', '🌅', '#ff6b35', 'dashboard_bg', 'uncommon', '석양 뷰'),
    ('lg_dash_cloud', '구름 위 비행', '☁️', '#87CEEB', 'dashboard_bg', 'common', '푸른 하늘'),
    ('lg_dash_storm', '뇌우 비행', '⛈️', '#2c3e50', 'dashboard_bg', 'rare', '뇌우 배경'),
    ('lg_dash_aurora', '오로라 뷰', '🌌', '#00ff88', 'dashboard_bg', 'epic', '북극광'),
    ('lg_hangar_basic', '기본 행거', '🏗️', '#333333', 'hangar_bg', 'common', '기본 정비고'),
    ('lg_hangar_premium', '프리미엄 행거', '🏛️', '#gold', 'hangar_bg', 'epic', '럭셔리 행거'),
    ('lg_hangar_sunset', '석양 행거', '🌇', '#ff8844', 'hangar_bg', 'uncommon', '석양 정비고'),
    ('lg_hangar_night', '야간 행거', '🌃', '#1a1a2e', 'hangar_bg', 'uncommon', '야간 정비고'),
    ('lg_hangar_snow', '설원 행거', '❄️', '#E8F4FF', 'hangar_bg', 'rare', '눈 덮인 정비고'),
    ('lg_logbook_classic', '클래식 로그북', '📗', '#004B9C', 'logbook_skin', 'common', '클래식 스타일'),
    ('lg_logbook_gold', '골드 로그북', '📒', '#FFD700', 'logbook_skin', 'rare', '골드 테두리'),
    ('lg_logbook_neon', '네온 로그북', '📘', '#00ff88', 'logbook_skin', 'epic', '네온 스타일'),
    ('lg_radar_vintage', '빈티지 레이더', '📻', '#8B7355', 'radar_skin', 'epic', '1960년대 관제'),
    ('lg_dash_galaxy', '은하수 뷰', '🌠', '#191970', 'dashboard_bg', 'legendary', '우주 뷰'),
]
for i, (id_, name, emoji, color, slot, rarity, desc) in enumerate(LOUNGES):
    add({'id': id_, 'name': name, 'category': 'lounge', 'slot': slot, 'emoji': emoji,
         'color': color, 'price': price_for(rarity, i), 'rarity': rarity,
         'applies_to': ALL_AC, 'desc': desc, 'sellable': True})

# ── 가속권 (16) ──
BOOSTS = [
    ('boost_1h', '훈련 가속 +1h', 1, 250_000, 'common'),
    ('boost_3h', '훈련 가속 +3h', 3, 650_000, 'common'),
    ('boost_5h', '훈련 가속 +5h', 5, 1_000_000, 'uncommon'),
    ('boost_10h', '훈련 가속 +10h', 10, 1_800_000, 'uncommon'),
    ('boost_15h', '훈련 가속 +15h', 15, 2_500_000, 'rare'),
    ('boost_25h', '훈련 가속 +25h', 25, 4_000_000, 'rare'),
    ('boost_40h', '훈련 가속 +40h', 40, 6_000_000, 'epic'),
    ('boost_50h', '마스터 패키지 +50h', 50, 7_000_000, 'epic'),
    ('boost_75h', '엘리트 패키지 +75h', 75, 9_500_000, 'epic'),
    ('boost_100h', '레전드 패키지 +100h', 100, 12_000_000, 'legendary'),
    ('boost_2h', '익스프레스 +2h', 2, 450_000, 'common'),
    ('boost_8h', '스탠다드 +8h', 8, 1_500_000, 'uncommon'),
    ('boost_20h', '프로 +20h', 20, 3_200_000, 'rare'),
    ('boost_30h', '시니어 +30h', 30, 4_800_000, 'rare'),
    ('boost_60h', '베테랑 +60h', 60, 8_500_000, 'epic'),
    ('boost_150h', '초고속 +150h', 150, 18_000_000, 'legendary'),
]
for id_, name, hours, price, rarity in BOOSTS:
    add({'id': id_, 'name': name, 'category': 'boost', 'slot': 'boost',
         'emoji': '⚡', 'boost_hours': hours, 'price': price, 'rarity': rarity,
         'desc': f'기체 해금 +{hours}시간', 'sellable': False, 'stackable': True})

# dedupe by id
seen = set()
unique = []
for it in items:
    if it['id'] not in seen:
        seen.add(it['id'])
        unique.append(it)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(unique, f, ensure_ascii=False, indent=2)

print(f'Generated {len(unique)} shop items → {OUT}')
by_cat = {}
for it in unique:
    by_cat[it['category']] = by_cat.get(it['category'], 0) + 1
for c, n in sorted(by_cat.items()):
    print(f'  {c}: {n}')