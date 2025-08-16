import json
from typing import Dict, List, Any, Optional

from app.db import exec, fetch
from app.rag.embeddings import embed_text


def _vec_literal(v: List[float]) -> str:
    """
    Convert a list of floats into a Postgres vector literal string.

    Args:
        v (List[float]): The embedding vector.

    Returns:
        str: The vector as a string literal for SQL (e.g., '[0.1, 0.2, ...]').
    """
    if not isinstance(v, list) or not all(isinstance(x, (float, int)) for x in v):
        raise ValueError("Input must be a list of floats.")
    return "[" + ", ".join(f"{float(x):.8f}" for x in v) + "]"

async def insert_chunk(content: str, metadata: Dict[str, Any]) -> None:
    """
    Embed and insert a text chunk and its metadata into the documents table.

    Args:
        content (str): The text content to embed and store.
        metadata (Dict[str, Any]): Metadata dictionary to store as JSONB.

    Raises:
        ValueError: If content is empty or metadata is not a dict.
        Exception: If the database operation fails.
    """
    if not content or not isinstance(content, str):
        raise ValueError("Content must be a non-empty string.")
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary.")

    emb = embed_text(content)
    if not emb or not isinstance(emb, list):
        raise ValueError("Embedding failed or returned invalid result.")

    emb_lit = _vec_literal(emb)
    try:
        await exec(
            "insert into documents (content, metadata, embedding) values ($1, $2::jsonb, $3::vector)",
            content,
            json.dumps(metadata),
            emb_lit
        )
    except Exception as e:
        raise Exception(f"Failed to insert chunk: {e}")

async def rag_search(
    query: str,
    k: int = 5,
    filter_json: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Perform a similarity search for documents matching the query embedding.

    Args:
        query (str): The query text to embed and search for.
        k (int, optional): Number of top results to return. Defaults to 5.
        filter_json (Dict[str, Any] | None, optional): Metadata filter as a dict. Defaults to None.

    Returns:
        List[Dict[str, Any]]: List of matching documents with their fields.

    Raises:
        ValueError: If query is empty or k is not positive.
        Exception: If the database operation fails.
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string.")
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")
    if filter_json is not None and not isinstance(filter_json, dict):
        raise ValueError("filter_json must be a dictionary or None.")

    emb = embed_text(query)
    if not emb or not isinstance(emb, list):
        raise ValueError("Embedding failed or returned invalid result.")

    emb_lit = _vec_literal(emb)
    try:
        rows = await fetch(
            "select * from match_documents($1::vector, $2::int, $3::jsonb)",
            emb_lit,
            k,
            json.dumps(filter_json or {})
        )
        return [dict(r) for r in rows]
    except Exception as e:
        raise Exception(f"RAG search failed: {e}")
