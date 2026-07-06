"""비행 게임 허브: 세션, 보상, 런처 생성"""
from datetime import datetime
from app.models import db
from app.services.gamification import load_json, log_activity, today_str, award_virtual_hours
from app.services.economy import award_money, format_krw

# FlightGear 기본 설치 경로 (Windows)
FG_WINDOWS_PATHS = [
    r'C:\Program Files\FlightGear 2024.1\bin\fgfs.exe',
    r'C:\Program Files\FlightGear 2024.1.1\bin\fgfs.exe',
    r'C:\Program Files\FlightGear\bin\fgfs.exe',
    r'C:\Program Files (x86)\FlightGear\bin\fgfs.exe',
]

AIRCRAFT_FG_MAP = {
    'b737': 'b737',
    'a320': 'A320-211',
    'c172': 'c172p',
    'c172p': 'c172p',
}


def get_games():
    return load_json('flight_games.json')


def get_game(game_id):
    return next((g for g in get_games() if g['id'] == game_id), None)


def _sessions(prog):
    meta = prog._json('pilot_meta', {})
    return meta.setdefault('game_sessions', {})


def _save_sessions(prog, sessions):
    meta = prog._json('pilot_meta', {})
    meta['game_sessions'] = sessions
    prog.set_json('pilot_meta', meta)


def get_game_progress(prog, game_id):
    sess = _sessions(prog).get(game_id, {})
    return {
        'plays': sess.get('plays', 0),
        'completes': sess.get('completes', 0),
        'first_complete_done': sess.get('first_complete_done', False),
        'last_play': sess.get('last_play', ''),
        'last_complete': sess.get('last_complete', ''),
        'today_complete': sess.get('last_complete', '') == today_str(),
    }


def enrich_game(prog, game):
    if not game:
        return None
    g = dict(game)
    g['progress'] = get_game_progress(prog, game['id'])
    rewards = game.get('rewards', {})
    g['reward_preview'] = format_krw(rewards.get('first_complete', 0))
    return g


def get_catalog(prog):
    return [enrich_game(prog, g) for g in get_games()]


def start_session(prog, game_id):
    game = get_game(game_id)
    if not game:
        return False, '게임을 찾을 수 없어요.'
    sessions = _sessions(prog)
    s = sessions.setdefault(game_id, {})
    s['plays'] = s.get('plays', 0) + 1
    s['last_play'] = today_str()
    _save_sessions(prog, sessions)
    log_activity(prog, 'game', f'start:{game_id}')
    db.session.commit()
    return True, {'game_id': game_id, 'progress': get_game_progress(prog, game_id)}


def complete_session(prog, game_id):
    game = get_game(game_id)
    if not game:
        return False, '게임을 찾을 수 없어요.'
    sessions = _sessions(prog)
    s = sessions.setdefault(game_id, {})
    today = today_str()
    if s.get('last_complete') == today:
        return False, '오늘은 이미 보상을 받았어요! 내일 다시 도전해 보세요.'

    rewards = game.get('rewards', {})
    first_done = s.get('first_complete_done', False)
    money = rewards.get('repeat_complete', 100000) if first_done else rewards.get('first_complete', 200000)
    hours = rewards.get('virtual_hours', 0.2)

    award_money(prog, money, f'비행 게임: {game["name"]}')
    if hours > 0:
        award_virtual_hours(prog, hours, f'비행 게임: {game["name"]}')

    season_rewards = []
    xp = rewards.get('season_xp', 0)
    if xp > 0:
        try:
            from app.services.pilot_features import add_season_xp
            season_rewards = add_season_xp(prog, 'game_done', xp)
        except Exception:
            pass

    s['completes'] = s.get('completes', 0) + 1
    s['last_complete'] = today
    if not first_done:
        s['first_complete_done'] = True
    _save_sessions(prog, sessions)
    log_activity(prog, 'game', f'complete:{game_id}')
    db.session.commit()

    return True, {
        'message': f'🎉 {game["name"]} 비행 완료! {format_krw(money)} 받았어요!',
        'money': money,
        'virtual_hours': hours,
        'first_time': not first_done,
        'season_rewards': season_rewards,
        'progress': get_game_progress(prog, game_id),
    }


def build_launcher_bat(aircraft='c172p', airport='RKSI'):
    """Windows용 FlightGear 실행 배치 파일"""
    paths_check = '\n'.join(
        f'if exist "{p}" set FGFS="{p}"'
        for p in FG_WINDOWS_PATHS
    )
    return f'''@echo off
chcp 65001 >nul
title Pilot Dream - FlightGear 비행 시작
echo.
echo  ========================================
echo   Pilot Dream - 직접 비행해보기
echo   비행기: {aircraft}  /  공항: {airport}
echo  ========================================
echo.

set FGFS=
{paths_check}
where fgfs >nul 2>&1
if %ERRORLEVEL%==0 if not defined FGFS set FGFS=fgfs

if not defined FGFS (
    echo [안내] FlightGear를 찾을 수 없어요!
    echo.
    echo  1. 먼저 FlightGear를 설치했는지 확인하세요.
    echo     다운로드: https://www.flightgear.org/download/
    echo.
    echo  2. 설치했는데도 안 되면, 이 파일을 메모장으로 열어
    echo     맨 아래 FGFS= 줄에 설치 경로를 직접 적어주세요.
    echo.
    pause
    exit /b 1
)

echo FlightGear를 시작합니다... 잠시만 기다려 주세요.
echo (처음엔 5~10분 걸릴 수 있어요)
echo.

"%FGFS%" --aircraft={aircraft} --airport={airport} --timeofday=morning --wind=0@0 --disable-sound

if %ERRORLEVEL% neq 0 (
    echo.
    echo 비행이 끝났거나 오류가 있었어요.
    echo Pilot Dream으로 돌아가서 "비행 완료" 버튼을 눌러 보상을 받으세요!
    pause
)
'''


def build_launcher_mac(aircraft='c172p', airport='RKSI'):
    return f'''#!/bin/bash
echo "========================================"
echo " Pilot Dream - 직접 비행해보기"
echo " 비행기: {aircraft} / 공항: {airport}"
echo "========================================"
echo ""

FGFS=""
for path in "/Applications/FlightGear.app/Contents/MacOS/fgfs" \\
            "/Applications/FlightGear-2024.1.app/Contents/MacOS/fgfs"; do
    if [ -x "$path" ]; then
        FGFS="$path"
        break
    fi
done

if [ -z "$FGFS" ]; then
    if command -v fgfs &>/dev/null; then
        FGFS="fgfs"
    fi
fi

if [ -z "$FGFS" ]; then
    echo "FlightGear를 찾을 수 없어요!"
    echo "https://www.flightgear.org/download/ 에서 설치해 주세요."
    read -p "엔터를 눌러 닫기..."
    exit 1
fi

echo "FlightGear 시작 중..."
"$FGFS" --aircraft={aircraft} --airport={airport} --timeofday=morning --wind=0@0 --disable-sound
echo ""
echo "Pilot Dream으로 돌아가서 비행 완료 버튼을 눌러 보상을 받으세요!"
read -p "엔터를 눌러 닫기..."
'''