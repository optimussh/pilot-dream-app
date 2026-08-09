# Pilot Dream App

미래의 기장을 꿈꾸는 사람들을 위한 몰입형 항공 교육 + 동기부여 플랫폼.

## 접속 주소 (로컬 Docker)

| 서비스 | URL |
|--------|-----|
| 메인 앱 | **http://127.0.0.1:5000** |
| 기장석 시뮬 | **http://127.0.0.1:5001** |

> 포트 없이 `http://127.0.0.1` 만 열면 연결되지 않습니다. **반드시 `:5000`** 을 붙이세요.

## 항상 켜 두기 (재부팅 대응)

코드는 **이미지에 포함**되고 DB만 Docker 볼륨에 둡니다.  
Google Drive 경로가 바뀌거나 드라이브가 늦게 마운트돼도, 이미 빌드된 컨테이너는 재부팅 후 다시 뜹니다.

### 1) 지금 배포 (빌드 + 기동)

```powershell
cd "G:\내 드라이브\10. 개발\Projects\pilot-dream-app"
.\deploy.ps1
```

### 2) 로그인 시 자동 기동 (한 번만)

```powershell
.\install-autostart.ps1
```

- Windows 작업 스케줄러: `PilotDreamApp-EnsureRunning` (로그인 1분 후)
- Docker Desktop: **Settings → General → Start Docker Desktop when you sign in** 켜기
- 로그: `%LOCALAPPDATA%\pilot-dream-app\ensure-running.log`

### 3) 재부팅 후 수동 확인

```powershell
.\ensure-running.ps1
docker compose -p pilot-dream-app ps
```

## 개발 모드 (소스 바인드 + reload)

Google Drive 바인드 마운트는 불안정할 수 있습니다. 가능하면 로컬 디스크 복제본을 권장합니다.

```powershell
docker compose -p pilot-dream-app -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Docker 없이 로컬

```powershell
.\run-local.ps1
```

## 프로젝트 구조

```
pilot-dream-app/
├── app/                 # Flask 패키지 (routes, services, models)
├── wsgi.py              # gunicorn 진입점 (app:app 이름 충돌 방지)
├── app.py               # flask run / 로컬 진입
├── sim/                 # 기장석 시뮬 (:5001)
├── templates/ static/ data/
├── docker-compose.yml   # always-on (이미지 내장, restart: unless-stopped)
├── docker-compose.dev.yml
├── deploy.ps1
├── ensure-running.ps1
└── install-autostart.ps1
```

## 트러블슈팅

| 증상 | 원인 / 조치 |
|------|-------------|
| `이 페이지에 연결할 수 없습니다` (127.0.0.1) | 포트 누락 → `http://127.0.0.1:5000` |
| 컨테이너 `Restarting` | 예전 경로 바인드 → `.\deploy.ps1` 로 재배포 |
| 재부팅 후 안 뜸 | Docker Desktop 자동 시작 + `install-autostart.ps1` 확인 |
| 소스 수정이 안 보임 | always-on 은 이미지 고정 → `.\deploy.ps1` 재빌드 또는 dev compose |

```powershell
docker compose -p pilot-dream-app logs --tail 80 web
docker compose -p pilot-dream-app logs --tail 80 sim
```
