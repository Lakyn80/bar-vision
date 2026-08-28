#!/bin/sh
set -eu

echo "Waiting for PostgreSQL..."

python - <<'PY'
import asyncio
import os

import asyncpg


async def wait_for_db() -> None:
    database_url = os.environ["DATABASE_URL"]
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    last_error: Exception | None = None

    for _ in range(60):
        try:
            connection = await asyncpg.connect(dsn=dsn)
            await connection.close()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            await asyncio.sleep(1)

    raise RuntimeError(f"PostgreSQL is not ready: {last_error}")


asyncio.run(wait_for_db())
PY

echo "PostgreSQL is ready."
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

exec "$@"
