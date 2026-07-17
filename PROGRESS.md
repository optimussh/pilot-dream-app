# Progress

프로젝트 진행 현황 로그. 커밋 직전 갱신 (`claude_Template-main/rules/common/git.md`).

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
