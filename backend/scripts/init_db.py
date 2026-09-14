"""Create the database schema for whichever DATABASE_URL is configured.

The Alembic migration chain targets PostgreSQL (it relies on gen_random_uuid()
and postgresql.TIMESTAMP), so it cannot run against SQLite. The ORM models
themselves are dialect-agnostic, so for SQLite we create the schema directly
from the model metadata - the same approach the test suite uses.

Usage (from the backend/ directory):
    python -m scripts.init_db
"""

import asyncio
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()


async def _create_all() -> None:
    from app.core.database import Base, engine

    # Importing the models registers them on Base.metadata.
    from app.models import comment, prediction, user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def main() -> int:
    from app.core.config import get_settings

    db_url = get_settings().DATABASE_URL.strip()

    if db_url.startswith("sqlite"):
        print(f"==> SQLite detected ({db_url}). Creating schema from models...")
        asyncio.run(_create_all())
        print("==> Schema created.")
        return 0

    print(f"==> Server database detected. Running Alembic migrations for {db_url.split('@')[-1]}...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
