# 세계 · 경제 · 꿈 유지 기능 (구현 완료)

## 접속
- 허브 페이지: `/world`
- 네비: **🌍 세계**
- 대시보드 상단: 스카이 타임즈 카드
- 레이더 항공기 클릭: 「왜 이 비행이 떴을까?」+ 손님/화물 이야기
- 항공사 개요: 유가·세계 수요 배수 반영
- 로그북: 노선 선택 시 이야기 카드

## 기능 맵

| # | 기능 | 위치 |
|---|------|------|
| 1 | 스카이 타임즈 | 대시보드 + `/world` |
| 2 | 비행 손님/화물 이야기 | 레이더 팝업, 로그북, API |
| 3 | 미래 편지 마일스톤 | `/world` → 💌 |
| 4 | 공항 경제 도감 | `/world` → 🗺️ |
| 5 | 밤하늘 항로 스토리 | `/world` → 🌙 |
| 6 | 요금 실험실 | `/world` → 💰 |
| 7 | 허브 미션 | `/world` → 🕸️ |
| 8 | 운영 트레이드오프 | `/world` → ⚖️ |
| 9 | 동맹(코드셰어) 지도 | `/world` → 🤝 |
| 10 | 세계 이벤트 보드 | `/world` → 📡 |
| 11 | 무역 체인 미션 | `/world` → 📦 |
| 12 | 관광 시즌 캘린더 | `/world` → 📅 |
| 13 | 유가 게이지 | 신문 + 항공사 수익 연동 |
| 14 | 레이더 왜 떴을까 | `radar.html` |
| 15 | 경제 퀴즈 | `/world` + 퀴즈 은행에 병합 |
| 16 | 주간 CEO 리포트 | `/world` → 📊 |
| 17 | 부모 모드 | `/world` 상단 토글 + 탭 |

## 데이터 파일 (`data/`)
- `world_events.json`, `flight_stories.json`, `trade_missions.json`
- `tourism_calendar.json`, `airport_economy.json`, `night_sky_stories.json`
- `economy_quiz.json`, `hub_missions.json`, `ops_tradeoffs.json`
- `pricing_lab.json`, `future_letter_milestones.json`

## 코드
- 서비스: `app/services/world_economy.py`
- 라우트: `app/routes/world.py`
- 수익 연동: `airline_ops._calc_single_route_revenue` / `estimate_weekly_revenue`

## 검증
```bash
python verify_world.py
```
