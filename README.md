# Bar Vision

Docker-first PWA for bar shift handovers: measure remaining alcohol in bottles via camera + deterministic calibration (not LLM volume guesses).

## Requirements

- Docker Desktop
- Docker Compose
- Copy `.env.example` to `.env` and adjust if needed

## Quick start

```powershell
cd C:\Users\lukas\Desktop\PYTHON_PROJECTS_DESKTOP\PYTHON_PROJECTS\bar-vision
Copy-Item .env.example .env
docker compose up --build -d
```

Application (Nginx entrypoint):

```text
http://localhost:18100
```

Health:

```text
http://localhost:18100/api/v1/health
```

## Services

| Service  | Role                         | Host exposure      |
|----------|------------------------------|--------------------|
| nginx    | reverse proxy                | `127.0.0.1:18100`  |
| frontend | React + Vite (dev)           | internal only      |
| backend  | FastAPI + Alembic            | internal only      |
| postgres | PostgreSQL 18                | internal only      |
| minio    | S3-compatible object storage | internal only      |

Backend runs migrations automatically on container start.

## Tests (inside Docker)

```powershell
docker compose exec -T backend pytest -q
```

## Docs

- `docs/project/BAR_VISION_EXECUTION_MAP_EN.md` — architecture and phase order
- `docs/project/UNIVERSAL_EXECUTION_PROTOCOL.md` — engineering / verification protocol
