# Pilot Dream App

미래의 기장을 꿈꾸는 사람들을 위한 몰입형 항공 교육 + 동기부여 플랫폼.

## 프로젝트 구조 (Flask + Docker)

```
pilot-dream-app/
├── app/
│   ├── __init__.py          # Flask factory
│   └── routes/
│       ├── main.py
│       ├── radar.py
│       ├── aircraft.py
│       ├── planner.py
│       ├── logbook.py
│       ├── atc.py
│       └── career.py
├── templates/               # Jinja2 템플릿
├── static/
├── data/                    # JSON 데이터
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── app.py                   # Entry point
└── README.md
```

## 실행 방법

```bash
docker-compose up --build
```

브라우저에서 `http://localhost:5000` 접속

## 주요 기능 (계획)

- 관제 레이더 (170대 실시간 시뮬)
- 기종 설계도
- 항공 영어 연습
- 비행 계획 시뮬레이터
- 가상 로그북
- 뱃지 시스템
- 한국 기장 진로 정보

## 아키텍처 원칙

- Blueprint를 사용한 기능별 분리
- 데이터는 JSON으로 관리 (추후 DB로 전환 가능)
- Template + Static 분리
- Docker로 일관된 개발/배포 환경

이 구조로 가면 나중에 기능이 많이 늘어나도 유지보수가 가능합니다.
