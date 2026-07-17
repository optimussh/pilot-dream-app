# Progress

프로젝트 진행 현황 로그. 커밋 직전 갱신 (`claude_Template-main/rules/common/git.md`).

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
