# Progress

프로젝트 진행 현황 로그. 커밋 직전 갱신 (`claude_Template-main/rules/common/git.md`).

---

## 2026-08-09 — 비행계획 단계별 시간 모델 (이·착륙 반영)

### What / Why
- 기존: `거리 / (spd×0.85)` 단순 나눗셈 → 단거리(국내선)가 비현실적으로 짧음
- 버그: `aircraft.spd` 없음(실제 필드는 `cruise_kmh`) → 항상 850 폴백
- 기본 모델: 택시 아웃·상승·순항·하강·접근·택시 인. 단거리는 순항 미도달(삼각 프로파일)
- 연료: 상승·하강 구간 소모율 가중. 순항 고도는 구간 거리에 따라 FL 추정
- UI: 단계별 카드 + 옛 단순 계산 대비 분 단위 비교

### Files
- `static/js/flight_time.js` (신규)
- `templates/flight_planner.html`

### Sanity (B737, 맑음)
- 40km 단거리 ~42분 (옛 ~3분)
- ICN-CJU 450km ~1h12 (옛 ~39분)
- ICN-NRT 1250km ~2h10 / ICN-JFK ~14h11

---

## 2026-08-09 — Always-on Docker (Google Drive 이전 후 복구)

### What / Why
- 소스를 Google Drive로 옮긴 뒤 컨테이너가 예전 경로 `C:\Users\user\pilot-dream-app` 를 바인드해 **Restarting 루프** → 127.0.0.1 접속 불가
- 런타임 바인드 제거: 코드는 이미지에 bake, DB만 `pilot_db` 볼륨 → 재부팅·드라이브 지연에도 기동 가능
- gunicorn 진입점 `wsgi:app` (`app` 패키지 vs `app.py` 충돌 해결)
- `deploy.ps1` / `ensure-running.ps1` / `install-autostart.ps1` (로그인 1분 후 자동 기동)
- 검증: web :5000 HTTP 200, sim :5001/health 200, restart=unless-stopped

### Files
- `docker-compose.yml`, `docker-compose.dev.yml`, `Dockerfile`, `wsgi.py`
- `deploy.ps1`, `ensure-running.ps1`, `install-autostart.ps1`, `.dockerignore`
- `sim/app.py` (debug/reloader 안정화), `README.md`

---

## 2026-07-19 — 시뮬레이션 A·B·C + 메인 메뉴 통합

### What / Why
- A: CJU 착륙·악천후 시나리오 추가 (Lv 해금)
- B: 도감 등급(마스터) + 주간 복습 미션
- C: 항공사 Lv/평판 해금 + 우리 항공 스토리 노선명
- 메인 앱 내비 **🎮 시뮬레이션** (`/simulation`) · 시뮬 **메인 앱** → :5000 홈 (404 수정)

---

## 2026-07-19 — 기장석 v4: 도감+복습 + ICN 출발 시나리오

### What / Why
- 스위치 도감(발견/설명/복습) · 복습 덱 · 메인 메타 저장 · 도감 배지
- ICN 출발 전 10분 시나리오(7막) · 부기장 FO 대사 · 단계별 체크

### Files
- `sim/content/core/scenarios.json`, `sim/backend/scenario_engine.py`, `codex.py`
- `sim/app.py` v4, `edu_pack.js`, cockpit UI tabs
- `app/services/sim_bridge.py`, `sim_hub.html`, badges, guide

---

## 2026-07-19 — 기장석 v3 (교관·스토리·챌린지·노선·가이드)

### What / Why
1–10 확장: 카메라 lerp, L1 일러스트 핫스팟, 교관 TTS, 스토리 컷,
실패 리플레이, 용어→학습, 일일/주간 챌린지, 노선 선택, 배지 강조, 가이드

### Files
- `sim/frontend/*`, `sim/content/core/*`, `sim/backend/*`
- `app/services/sim_bridge.py`, `templates/sim_hub.html`, `badges.html`
- `data/guide_sections.json`, `docs/simulator.md`

---

## 2026-07-19 — 기장석 v2 (교육·유리창 L1·Three.js L2·연동)

### What / Why
- 체크리스트 7종, 순서 경고, TTS, 미니 퀴즈, 배지, 단계 자동 진행
- 앞유리 배경 + 계기, 핫스팟 기장석(L1), Three.js 1인칭(L2)
- 노선 탑승 미션, 레벨·평판 패널 해금, 스토리 로그북

### Files
- `sim/content/core/*`, `sim/backend/*`, `sim/frontend/*`
- `app/services/sim_bridge.py`, `templates/sim_hub.html`, `data/badges.json`
- `docs/simulator.md`

---

## 2026-07-19 — 기장석 시스템 트레이너 (`sim/` :5001)

### What / Why
- 옵션 C: 메인 웹 가볍게 + 시뮬 별 포트. X-Plane는 이후.
- 코어 1 + 프로필 A(표준)/B(우리 항공) 스킨
- 스위치 40+ · 설명 · 체크리스트 · web session/complete 보상
- 웹 이사(R2)는 보류, `sim/` 형제 폴더만 추가

### Files
- `sim/` (app, content, backend, frontend)
- `docs/simulator.md`
- `app/services/sim_bridge.py`, `app/routes/sim_hub.py`, `templates/sim_hub.html`
- `templates/base.html` 내비, `docker-compose.yml` profile sim

---

## 2026-07-17 — 항공사 3층: 투자 교실 (주식회사·친구 시장·이사회)

### What / Why
- 조각 발행, NPC 지분, 하늘 친구 시장, 주간 배당, 이사회 카드
- 중독 방지: 일 2회 시장, 당주 매도 금지, 7일 인내 보너스, 주 단위 시세
- 탭 `📈 투자`, API `/api/airline/invest/*`, 가이드·가이드.md 연동

### Files
- `app/services/airline_invest.py`
- `data/airline_market_firms.json`, `airline_npc_investors.json`, `airline_board_cards.json`
- `app/routes/airline.py`, `app/services/airline_ops.py`, `templates/airline.html`
- `data/guide_sections.json`, `가이드.md`

---

## 2026-07-17 — UX 편의: 완료 접기 / 할 일 펼치기

### What / Why
- 뱃지 패턴을 앱 전반에 확대: **끝낸 것은 접고, 남은 일을 먼저**
- 공통 `uxCollapseHtml` / `bindUxCollapses` (`gamification.js`)
- 적용: 뱃지, 기장생활(동료·도감·정시·탭 ✓), 상점 보너스, 대시보드 미션, 항공사 채용, 학습 허브 완료 표시
- 가이드 `ux_collapse` 섹션 추가

### Files
- `static/js/gamification.js`
- `templates/badges.html`, `captain_life.html`, `shop.html`, `dashboard.html`, `airline.html`, `learn.html`
- `data/guide_sections.json`

---

## 2026-07-17 — 성능 최적화 2단계 (지연 로딩 + tick 분리)

### What / Why
- 채용 풀·노선 템플릿을 **탭 열 때만** 로드 (`/api/airline/crew`, `/api/airline/route-templates`)
- 일일 수익 tick을 대시보드에서 분리 (`POST /api/airline/tick`, 백그라운드)
- 대시보드는 해금·채용 동료만 (only_active)
- 1단계: JSON/프로필 캐시 + light 대시보드 유지

### Files
- `app/services/airline_ops.py`, `app/routes/airline.py`, `templates/airline.html`
- `verify_airline.py`, `PROGRESS.md`

### Deferred
- 3층 주식/투자 — 의도적 보류

---

## 2026-07-17 — 성능 최적화 1단계 (클릭 렉)

### What / Why
- `load_json` mtime 캐시, 승무원 프로필 캐시, 미해금 슬림 프로필
- 대시보드 light + POST light 응답

---

## 2026-07-10 — 항공사 2층(회사 경영) 완성

### What / Why
- **손익 보드**: 매출·비용·이익을 아이 문장으로 개요 탭에 표시
- **주간 이익 배치(CEO 회의)**: 금고 / 재투자(+6% 매출) / 직원 보너스(평판)
- **회사 금고**: 적립·인출 API
- **가이드 연동**: `guide_sections.json` + 루트 `가이드.md` 초등 설명
- 이후 작업 시 히스토리(이 파일)·가이드·가이드 탭을 항상 같이 갱신하는 워크플로 확립

### Files
- `app/services/airline_company.py` (new)
- `app/services/airline_ops.py`, `app/routes/airline.py`
- `templates/airline.html`
- `data/guide_sections.json`, `가이드.md`, `PROGRESS.md`

### Verify
- `python verify_airline.py`
- company board present on dashboard when airline founded

### Next (not done — Layer 3)
- 주식회사 조각 발행, 하늘 친구 시장(투자) — 보류
