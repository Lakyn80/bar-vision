from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings


def test_alembic_heads_are_linear() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()

    assert len(heads) == 1
    assert heads[0] == "0004"


async def test_core_tables_exist_after_migration(
    db_engine: AsyncEngine,
) -> None:
    settings = get_settings()
    assert settings.database_url.startswith("postgresql+asyncpg://")

    async with db_engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'alembic_version',
                      'business_memberships',
                      'businesses',
                      'users',
                      'venues'
                  )
                ORDER BY table_name
                """
            )
        )
        tables = [row[0] for row in result]

    assert tables == [
        "alembic_version",
        "business_memberships",
        "businesses",
        "users",
        "venues",
    ]
