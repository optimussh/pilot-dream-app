from app.services.economy import award_money, spend_money, get_owned_aircraft

GREEN_LEVELS = [
    {'level': 1, 'name': '🌱 새싹', 'min_points': 0},
    {'level': 2, 'name': '🌿 풀잎', 'min_points': 21},
    {'level': 3, 'name': '🌳 나무', 'min_points': 51},
    {'level': 4, 'name': '🌍 지구 지킴이', 'min_points': 101},
]

GREEN_TIPS = [
    "비행기에 탈 때 텀블러를 챙기면 쓰레기를 줄일 수 있어요! 🥤",
    "가벼운 짐을 싸면 비행기가 연료를 덜 써서 지구가 좋아해요! 🧳",
    "기내식을 남기지 않고 다 먹으면 음식물 쓰레기가 줄어들어요! 🍱",
    "짧은 거리는 기차나 버스를 타는 것도 좋은 방법이랍니다! 🚂",
    "태양광이나 풍력 같은 착한 에너지를 응원해 주세요! ☀️",
]

def get_green_level(points):
    current = GREEN_LEVELS[0]
    for lvl in GREEN_LEVELS:
        if points >= lvl['min_points']:
            current = lvl
    return current

def get_green_tips():
    return GREEN_TIPS

def calculate_green_score(prog):
    meta = prog._json('pilot_meta', {})
    green = meta.get('green', {'points': 0, 'level': 1, 'eco_meals': False, 'recycling': False, 'saf': False, 'claimed_levels': []})
    
    # Base points
    points = 10
    
    if green.get('eco_meals'): points += 15
    if green.get('recycling'): points += 20
    if green.get('saf'): points += 30
    
    # Fleet efficiency bonus — owned_aircraft column (there is no wallet JSON field)
    fleet = get_owned_aircraft(prog)
    points += 5 * len(fleet)
        
    green['points'] = points
    
    new_level_info = get_green_level(points)
    new_level = new_level_info['level']
    green['level'] = new_level
    
    claimed = green.get('claimed_levels', [])
    new_rewards = 0
    if new_level > 1:
        for lvl in range(2, new_level + 1):
            if lvl not in claimed:
                claimed.append(lvl)
                new_rewards += 1000000
                award_money(prog, 1000000, f'친환경 레벨 {lvl} 달성')
                
    green['claimed_levels'] = claimed
    meta['green'] = green
    prog.set_json('pilot_meta', meta)
    
    return green

def get_green_status(prog):
    green = calculate_green_score(prog)
    level_info = get_green_level(green['points'])
    
    next_level = None
    for lvl in GREEN_LEVELS:
        if lvl['level'] == level_info['level'] + 1:
            next_level = lvl
            break
            
    return {
        'points': green['points'],
        'level': green['level'],
        'level_name': level_info['name'],
        'next_level_points': next_level['min_points'] if next_level else None,
        'eco_meals': green.get('eco_meals', False),
        'recycling': green.get('recycling', False),
        'saf': green.get('saf', False),
        'tips': GREEN_TIPS,
        'progress_percent': min(100, int((green['points'] / (next_level['min_points'] if next_level else 150)) * 100))
    }

def toggle_eco_option(prog, option):
    if option not in ('eco_meals', 'recycling', 'saf'):
        return False, '알 수 없는 설정이에요.'

    meta = prog._json('pilot_meta', {})
    green = meta.get('green') or {
        'points': 0, 'level': 1, 'eco_meals': False, 'recycling': False,
        'saf': False, 'claimed_levels': [],
    }

    if option == 'saf' and not green.get('saf'):
        ok, msg = spend_money(prog, 500000, '친환경 연료(SAF) 구매')
        if not ok:
            return False, '돈이 부족해요! (500,000원이 필요해요)'

    green[option] = not green.get(option, False)
    meta['green'] = green
    prog.set_json('pilot_meta', meta)
    calculate_green_score(prog)
    return True, f'{option} 설정이 변경되었어요!'
