"""승무원·직원 스펙 — crew_id 기준 결정적(항상 동일) 랜덤 프로필"""
import hashlib
import random
import re

GRADE_THRESHOLDS = (
    (90, 'S'), (75, 'A'), (60, 'B'), (45, 'C'), (0, 'D'),
)
GRADE_EMOJI = {'S': '🌟', 'A': '💎', 'B': '✈️', 'C': '📘', 'D': '🌱'}

ROLE_SKILLS = {
    '승무원': [('서비스', '😊'), ('응급처치', '🩹'), ('언어', '🗣️')],
    '부기장': [('조종숙련', '🕹️'), ('협업', '🤝'), ('절차준수', '📋')],
    '기장': [('안전', '🛡️'), ('리더십', '👑'), ('기상판단', '🌤️')],
    '국제선 기장': [('국제노선', '🌏'), ('안전', '🛡️'), ('리더십', '👑')],
    '화물기장': [('화물운송', '📦'), ('안전', '🛡️'), ('야간비행', '🌙')],
    '최고 기장': [('전략', '🎯'), ('안전', '🛡️'), ('멘토링', '🎓')],
    '정비사': [('정비', '🔧'), ('진단', '🔍'), ('신속', '⚡')],
    '운항관리': [('스케줄', '📅'), ('정시', '⏰'), ('협조', '🤝')],
    '관제사': [('관제', '📡'), ('안전', '🛡️'), ('집중력', '🎯')],
    '정시 전문': [('정시', '⏰'), ('스케줄', '📅'), ('위기대응', '🚨')],
    '연료사': [('연료계산', '⛽'), ('정확', '🎯'), ('절약', '💰')],
    '비행 학생': [('열정', '🔥'), ('학습', '📚'), ('체력', '💪')],
    '조종 학생': [('학습', '📚'), ('시뮬', '🖥️'), ('협업', '🤝')],
}

SPECIALTIES = {
    '승무원': ['다국어 서비스', '키즈 케어', '비즈니스석', '응급 대응', '미소 장인', '기내 안내'],
    '부기장': ['절차 준수', '단거리 전문', '야간 비행', '복항로 숙련', 'CRM 달인'],
    '기장': ['정시 운항', '악천후 대응', '국내선', '신규 노선', '안전 제일'],
    '국제선 기장': ['대서양 횡단', '장거리 CRM', '제트래그 극복', '다국적 승무'],
    '화물기장': ['화물 적재', '야간 화물', '위험물 취급', '긴급 운송'],
    '최고 기장': ['전설의 정시', '위기 관리', '후배 양성', '세계 일주'],
    '정비사': ['엔진 정비', '항공전자', '신속 AOG', '예방 정비'],
    '운항관리': ['허브 운영', '지연 복구', '슬롯 협상', '연결편 관리'],
    '관제사': ['혼잡 공역', '악천후 관제', '24시 관제', '비상 교신'],
    '정시 전문': ['5분 정시', '지연 예방', '턴어라운드', '연결 최적화'],
    '연료사': ['연료 절감', '장거리 연료', '대체공항', '정밀 계산'],
    '비행 학생': ['열심히 공부', '시뮬 연습', '첫 솔로 준비'],
    '조종 학생': ['시뮬 고수', '이론 만점', 'CRM 연습'],
}

PERSONALITIES = [
    '침착한 타입', '밝은 에너지', '꼼꼼한 성격', '든든한 형', '상냥한 언니',
    '유머 감각', '조용한 실력파', '열정 만수르', '차분한 베테랑', '호기심 많은',
]

HIRE_TIPS = {
    'S': '최고의 선택! 수익이 크게 올라가요',
    'A': '우수 인재! 국제선·장거리에 추천',
    'B': '믿을 만해요. 국내선 운영에 좋아요',
    'C': '성장형! 단거리·보조 업무에 적합',
    'D': '신입 느낌. 연습·보조로 키워보세요',
}

ROLE_PAY_BASE = {
    'captain': 1_200_000, 'fo': 750_000, 'fa': 420_000,
    'mechanic': 580_000, 'dispatcher': 520_000, 'ground': 380_000,
}


def _seed(crew_id):
    return int(hashlib.md5(crew_id.encode('utf-8')).hexdigest()[:8], 16)


def _crew_index(crew_id):
    m = re.search(r'_(\d+)$', crew_id)
    return int(m.group(1)) if m else 25


def _grade(overall):
    for threshold, g in GRADE_THRESHOLDS:
        if overall >= threshold:
            return g
    return 'D'


def _rng_for(crew_id):
    return random.Random(_seed(crew_id))


_profile_cache = {}  # crew_id -> profile dict


def generate_crew_profile(card):
    """카드 dict → 스펙 프로필 (항상 동일 crew_id면 동일 결과, 캐시)"""
    cid = card['id']
    cached = _profile_cache.get(cid)
    if cached is not None:
        return cached
    rng = _rng_for(cid)
    idx = _crew_index(cid)
    role = card.get('role', '승무원')
    airline_role = card.get('airline_role', 'fa')

    overall = int(35 + idx * 1.15 + rng.randint(-6, 10))
    overall = max(38, min(95, overall))

    if role == '최고 기장':
        overall = min(99, overall + 12)
    elif role in ('국제선 기장', '화물기장'):
        overall = min(92, overall + 6)
    elif role in ('비행 학생', '조종 학생'):
        overall = min(62, max(40, overall - 18))
    elif role == '정시 전문':
        overall = min(90, overall + 4)

    grade = _grade(overall)
    exp_years = max(1, int(overall / 8 + rng.randint(0, 4)))
    if role in ('비행 학생', '조종 학생'):
        exp_years = max(0, rng.randint(0, 2))
    elif role == '최고 기장':
        exp_years = max(18, exp_years + 8)

    flight_hours = exp_years * rng.randint(450, 850) + rng.randint(100, 800)
    flights_count = max(exp_years * 50, flight_hours // rng.randint(4, 8))

    skill_defs = ROLE_SKILLS.get(role, ROLE_SKILLS['승무원'])
    skills = []
    for name, emoji in skill_defs:
        val = max(30, min(99, overall + rng.randint(-12, 12)))
        skills.append({'name': name, 'emoji': emoji, 'value': val})

    specs = SPECIALTIES.get(role, SPECIALTIES['승무원'])
    specialty = rng.choice(specs)
    personality = rng.choice(PERSONALITIES)

    pay_base = ROLE_PAY_BASE.get(airline_role, 400_000)
    weekly_pay = int(pay_base * (0.75 + overall / 200))

    kid = f'{exp_years}년 경력 · {grade}등급 · {specialty}'
    if role in ('비행 학생', '조종 학생'):
        kid = f'신입 {role} · {specialty}'

    result = {
        'grade': grade,
        'grade_emoji': GRADE_EMOJI.get(grade, '✈️'),
        'overall': overall,
        'experience_years': exp_years,
        'flight_hours': flight_hours,
        'flights_count': flights_count,
        'specialty': specialty,
        'personality': personality,
        'weekly_pay': weekly_pay,
        'skills': skills,
        'kid_summary': kid,
        'hire_tip': HIRE_TIPS.get(grade, ''),
        'route_bonus_pct': max(0, overall - 50),
    }
    _profile_cache[cid] = result
    return result


def get_crew_profile(crew_id, card=None):
    if card and card.get('id') == crew_id:
        return generate_crew_profile(card)
    cached = _profile_cache.get(crew_id)
    if cached is not None:
        return cached
    from app.services.gamification import load_json_by_id
    cards = load_json_by_id('crew_cards.json')
    c = cards.get(crew_id)
    if not c:
        return {'grade': 'C', 'overall': 50, 'skills': [], 'kid_summary': '동료'}
    return generate_crew_profile(c)


def crew_power(crew_id):
    return get_crew_profile(crew_id)['overall'] / 100.0


ROUTE_SPECIALTY_KEYWORDS = {
    'international': ['국제', '다국어', '대서양', '세계', '제트래그', '다국적', '장거리'],
    'longhaul': ['국제', '대서양', '장거리', '제트래그', 'CRM', '다국적'],
    'domestic': ['국내', '단거리', '정시', '신규', '국내선'],
    'regional': ['단거리', '국내', '리저널', '짧은'],
    'cargo': ['화물', '야간 화물', '긴급', '적재', '운송'],
}

GRADE_RANK = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}


def collect_route_crew_ids(staff, ops=None):
    """노선 staff dict → crew id 목록 (레거시 bool 지원)"""
    ids = []
    if not staff:
        return ids
    pool = (ops or {}).get('staff_pool', {})
    pool_keys = {'captain': 'captain', 'fo': 'fo', 'mechanic': 'mechanic', 'dispatcher': 'dispatcher'}
    for key, pool_key in pool_keys.items():
        val = staff.get(key)
        if isinstance(val, str):
            ids.append(val)
        elif val is True and pool.get(pool_key):
            role_pool = pool.get(pool_key, [])
            if role_pool:
                ids.append(role_pool[0])
    for fa in staff.get('fa', []) or []:
        if isinstance(fa, str):
            ids.append(fa)
    return list(dict.fromkeys(ids))


def specialty_match_mult(route_type, crew_ids, cards_by_id):
    keywords = ROUTE_SPECIALTY_KEYWORDS.get(route_type, ROUTE_SPECIALTY_KEYWORDS['domestic'])
    matches = []
    for cid in crew_ids:
        card = cards_by_id.get(cid, {})
        prof = get_crew_profile(cid, card if card else None)
        spec = prof.get('specialty', '')
        role = card.get('role', '')
        text = f'{spec} {role}'
        for kw in keywords:
            if kw in text:
                matches.append({'id': cid, 'name': card.get('name', cid), 'specialty': spec, 'keyword': kw})
                break
    mult = 1.0 + min(0.28, 0.09 * len(matches))
    labels = [f'{m["name"]}({m["keyword"]})' for m in matches]
    return mult, labels


def synergy_mult(crew_ids, cards_by_id):
    if len(crew_ids) < 2:
        return 1.0, []
    profiles = []
    for cid in crew_ids:
        card = cards_by_id.get(cid, {})
        p = get_crew_profile(cid, card if card else None)
        profiles.append({**p, 'id': cid, 'name': card.get('name', ''), 'role': card.get('role', '')})

    mult = 1.0
    labels = []
    specs = [p.get('specialty', '') for p in profiles]
    roles = [p.get('role', '') for p in profiles]
    grades = [p.get('grade', 'C') for p in profiles]
    personalities = [p.get('personality', '') for p in profiles]

    ontime_n = sum(1 for s in specs if '정시' in s)
    if ontime_n >= 2:
        mult *= 1.07
        labels.append('⏰ 정시 듀오')

    if any('다국어' in s for s in specs) and any('국제' in r or '국제' in s for r, s in zip(roles, specs)):
        mult *= 1.08
        labels.append('🌏 국제 서비스팀')

    crm_spec = any('CRM' in s for s in specs)
    crm_skill = any(
        any(sk.get('name') in ('협업', '리더십') and sk.get('value', 0) >= 68 for sk in p.get('skills', []))
        for p in profiles
    )
    if crm_spec and crm_skill:
        mult *= 1.07
        labels.append('🤝 CRM 드림팀')

    cap_grades = [GRADE_RANK.get(g, 1) for p in profiles if '기장' in p.get('role', '') for g in [p.get('grade')]]
    fo_grades = [GRADE_RANK.get(g, 1) for p in profiles if '부기장' in p.get('role', '') or p.get('role') == '조종 학생' for g in [p.get('grade')]]
    if cap_grades and fo_grades and max(cap_grades) >= 4 and max(fo_grades) >= 3:
        mult *= 1.06
        labels.append('👨‍✈️ 에이스 조종편')

    if any('침착' in p for p in personalities) and any('꼼꼼' in p for p in personalities):
        mult *= 1.04
        labels.append('🛡️ 안전 콤비')

    cargo_specs = sum(1 for s in specs if '화물' in s)
    if cargo_specs >= 2:
        mult *= 1.06
        labels.append('📦 화물 전문팀')

    return min(1.35, mult), labels


def analyze_route_bonuses(route, ops, cards_by_id):
    staff = route.get('staff', {})
    crew_ids = collect_route_crew_ids(staff, ops)
    route_type = route.get('type', 'domestic')
    spec_m, spec_labels = specialty_match_mult(route_type, crew_ids, cards_by_id)
    syn_m, syn_labels = synergy_mult(crew_ids, cards_by_id)
    return {
        'crew_count': len(crew_ids),
        'specialty_mult': round(spec_m, 3),
        'synergy_mult': round(syn_m, 3),
        'combined_bonus_pct': int((spec_m * syn_m - 1) * 100),
        'specialty_labels': spec_labels,
        'synergy_labels': syn_labels,
    }


BENCH_PAY_RATIO = 0.25


def assigned_crew_ids(ops):
    """노선에 실제 배치된 승무원 ID"""
    ids = set()
    for route in ops.get('routes', []):
        if not route.get('active', True):
            continue
        staff = route.get('staff', {})
        for key in ('captain', 'fo', 'mechanic', 'dispatcher'):
            cid = staff.get(key)
            if isinstance(cid, str) and cid:
                ids.add(cid)
        for fid in staff.get('fa', []) or []:
            if isinstance(fid, str) and fid:
                ids.add(fid)
    return ids


def calc_weekly_payroll(ops):
    from app.services.gamification import load_json
    pool = ops.get('staff_pool', {})
    cards = {c['id']: c for c in load_json('crew_cards.json')}
    on_route = assigned_crew_ids(ops)
    has_routes = any(r.get('active', True) for r in ops.get('routes', []))
    total = 0
    breakdown = []
    for role, ids in pool.items():
        if not isinstance(ids, list):
            continue
        for cid in ids:
            card = cards.get(cid)
            if not card:
                continue
            prof = generate_crew_profile(card)
            full_pay = prof['weekly_pay']
            if cid in on_route:
                pay = full_pay
                status = '배치'
            elif has_routes:
                pay = int(full_pay * BENCH_PAY_RATIO)
                status = '대기'
            else:
                pay = full_pay
                status = '대기'
            total += pay
            breakdown.append({
                'id': cid,
                'name': card['name'],
                'role': card.get('role', role),
                'grade': prof['grade'],
                'pay': pay,
                'full_pay': full_pay,
                'status': status,
            })
    breakdown.sort(key=lambda x: -x['pay'])
    return total, breakdown


def staff_label(crew_id, hireable_by_id):
    c = hireable_by_id.get(crew_id)
    if not c:
        return crew_id
    p = c.get('profile', {})
    return f"{c.get('emoji', '')} {c['name']} ({p.get('grade', '?')})"