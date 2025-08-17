from fastapi import FastAPI
from app.db import connect, close
from app.Routers import ingest

app = FastAPI(title="Performance RAG API")

@app.on_event("startup")
async def _startup():
    """
    Event handler for FastAPI startup event.
    Initializes the database connection pool.
    """
    try:
        await connect()
    except Exception as e:
        # Log or handle startup connection errors as needed
        raise RuntimeError(f"Failed during startup: {e}")

@app.on_event("shutdown")
async def _shutdown():
    """
    Event handler for FastAPI shutdown event.
    Closes the database connection pool.
    """
    try:
        await close()
    except Exception as e:
        # Log or handle shutdown errors as needed
        raise RuntimeError(f"Failed during shutdown: {e}")

app.include_router(ingest.router, prefix="/api")  

@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns a simple status message indicating the service is running.
    """
    return {"status": "ok"}
