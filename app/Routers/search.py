"""Search API router for semantic search over the vector store.

This module provides an endpoint for performing semantic search queries
with optional metadata filtering.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.rag.vectorstore import rag_search

router = APIRouter(prefix="/search", tags=["search"])


# ----- Response model (keeps OpenAPI tight) -----
class SearchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    query: str = Field(..., min_length=1, max_length=512)
    k: int = Field(..., ge=1, le=50)
    filter: Dict[str, Any]
    results: List[Dict[str, Any]]


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=512),
    k: int = Query(5, ge=1, le=50),
    filter_: Optional[str] = Query(None, alias="filter", description="JSON object as string"),
):
    """
    Semantic search over the vector store.

    - `q`: query text
    - `k`: top-K results (1..50)
    - `filter`: JSON string, e.g. {"file_id":"abc","file_type":"text"}
    """
    q_stripped = q.strip()
    if not q_stripped:
        raise HTTPException(status_code=422, detail="Query cannot be blank.")

    # Parse filter JSON once; return 400 on invalid payload
    try:
        filt: Dict[str, Any] = json.loads(filter_) if filter_ else {}
        if not isinstance(filt, dict):  # guard against arrays/strings
            raise ValueError("Filter must be a JSON object.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON for 'filter'.")

    try:
        results = await rag_search(q_stripped, k, filt)
    except Exception as e:
        # Surface a clean 500 but avoid leaking internals
        raise HTTPException(status_code=500, detail="Search backend error.") from e

    return SearchResponse(query=q_stripped, k=k, filter=filt, results=results)
