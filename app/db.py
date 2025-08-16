import asyncpg
from typing import Optional
from app.config import settings

_pool: Optional[asyncpg.Pool] = None

async def connect() -> None:
    """
    Initialize the asyncpg connection pool if it hasn't been created yet.
    Uses the database URL from settings.
    """
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=5
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create database pool: {e}")

async def close() -> None:
    """
    Close the asyncpg connection pool if it exists.
    """
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception as e:
            raise RuntimeError(f"Failed to close database pool: {e}")
        finally:
            _pool = None

async def fetch(query: str, *args):
    """
    Execute a SELECT query and return all results.

    Args:
        query (str): The SQL query to execute.
        *args: Parameters to pass to the query.

    Returns:
        List of records from the database.
    """
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call connect() first.")
    try:
        return await _pool.fetch(query, *args)
    except Exception as e:
        raise RuntimeError(f"Database fetch failed: {e}")

async def exec(query: str, *args):
    """
    Execute a query (INSERT, UPDATE, DELETE, etc.) and return the status.

    Args:
        query (str): The SQL query to execute.
        *args: Parameters to pass to the query.

    Returns:
        The status returned by asyncpg's execute method.
    """
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call connect() first.")
    try:
        return await _pool.execute(query, *args)
    except Exception as e:
        raise RuntimeError(f"Database execute failed: {e}")


