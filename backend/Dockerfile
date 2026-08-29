FROM python:3.13.15-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/bar-vision/.venv
ENV PATH="/opt/bar-vision/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock alembic.ini ./
RUN uv sync --frozen --extra dev --no-install-project

COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts

RUN uv sync --frozen --extra dev

# Use sh explicitly so Windows bind-mounts (CRLF / missing +x) cannot break startup.
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
