import asyncio
import pathlib
import sys
from pathlib import Path
import asyncpg

# Ensure project root is on sys.path when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings

async def apply_migrations():
    """
    Applies all SQL migration files in the 'migrations' directory to the database.

    - Connects to the database using the DSN from settings.
    - Finds and applies all .sql files in sorted order.
    - Prints progress and success messages.
    - Ensures the connection is closed even if an error occurs.
    """
    conn = None
    try:
        dsn = settings.database_direct_url or settings.database_url
        conn = await asyncpg.connect(dsn=dsn)
        migrations_dir = pathlib.Path("migrations")
        if not migrations_dir.exists() or not migrations_dir.is_dir():
            raise FileNotFoundError("Migrations directory not found.")

        migration_files = sorted(migrations_dir.glob("*.sql"))
        if not migration_files:
            print("No migration files found.")
            return

        for path in migration_files:
            sql = path.read_text(encoding="utf-8")
            if sql.strip():
                print(f"Applying migration: {path.name}...")
                try:
                    await conn.execute(sql)
                except Exception as e:
                    print(f"Error applying {path.name}: {e}")
                    raise
        print("All migrations applied successfully.")
    except Exception as exc:
        print(f"Migration failed: {exc}")
        raise
    finally:
        if conn is not None:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(apply_migrations())