"""Ingest API router for handling text and row-based document ingestion.

This module provides endpoints for ingesting text documents and tabular data (rows)
into the system, updating metadata, and managing document vectors and schemas.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Set, Tuple, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import exec as db_exec, fetch as db_fetch

# Prefer the canonical, lowercase path; keep a fallback for existing deployments.
try:
    from app.services.chunking import chunk_text  # returns List[Tuple[int, str]]
except ImportError:  # pragma: no cover
    from app.Services.chunking import chunk_text  # type: ignore

from app.rag.vectorstore import insert_chunk

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ---------------- Models ----------------

class IngestTextBody(BaseModel):
    """
    Request body for ingesting a text document.
    """
    file_id: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    url: str = Field(..., min_length=1, max_length=2048)
    content: str = Field(..., min_length=1)


class IngestRowsBody(BaseModel):
    """
    Request body for ingesting tabular data (rows).
    """
    file_id: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    url: str = Field(..., min_length=1, max_length=2048)
    rows: List[Dict[str, Any]] = Field(..., min_items=1)
    full_refresh: bool = False  # optional override to force replace


class TextIngestResponse(BaseModel):
    """
    Response model for text ingestion.
    """
    status: Literal["ok"]
    mode: Literal["full_replace"]
    chunks_inserted: int


class RowsIngestResponse(BaseModel):
    """
    Response model for row ingestion.
    """
    status: Literal["ok"]
    mode: Literal["full_refresh", "incremental"]
    rows_inserted: int
    rows_deleted: Optional[int] = None
    schema_keys: List[str]


# ---------------- Helpers ----------------

async def upsert_document_metadata(file_id: str, title: str, url: str) -> None:
    """
    Insert or update document metadata in the database.
    """
    await db_exec(
        """
        INSERT INTO document_metadata (id, title, url)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE
          SET title = EXCLUDED.title,
              url   = EXCLUDED.url
        """,
        file_id, title, url,
    )


async def update_document_schema(file_id: str, schema_keys: List[str]) -> None:
    """
    Update the schema (list of keys) for a document in the metadata table.
    """
    await db_exec(
        "UPDATE document_metadata SET schema = $2 WHERE id = $1",
        file_id, json.dumps(schema_keys),
    )


async def delete_vectors_for_file(file_id: str) -> None:
    """
    Delete all vector entries for a given file from the documents table.
    """
    await db_exec("DELETE FROM documents WHERE metadata->>'file_id' = $1", file_id)


def _hash_row(row: Dict[str, Any]) -> str:
    """
    Compute a stable hash for a row dictionary using canonical JSON.
    Detects any change in fields or values.
    """
    normalized = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------- Endpoints ----------------

@router.post("/text", response_model=TextIngestResponse)
async def ingest_text(body: IngestTextBody) -> TextIngestResponse:
    """
    Ingest a text document:
    - Upsert document metadata.
    - Delete existing vectors for this file.
    - Chunk the content and insert each chunk as a vector.
    """
    # Upsert metadata + full-replace vectors for this file
    await upsert_document_metadata(body.file_id, body.title, body.url)
    await delete_vectors_for_file(body.file_id)

    chunks = chunk_text(body.content, chunk_size=1000, overlap=150)
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks produced from content.")

    # Concurrency-limited parallel inserts (IO-bound): big speedup on large docs
    semaphore = asyncio.Semaphore(16)
    inserted = 0

    async def _insert(idx: int, chunk: str) -> None:
        """
        Insert a single chunk into the vector store with associated metadata.
        """
        nonlocal inserted
        meta = {
            "file_id": body.file_id,
            "file_title": body.title,
            "file_url": body.url,
            "file_type": "text",
            "chunk_index": idx,
        }
        async with semaphore:
            await insert_chunk(chunk, meta)
            inserted += 1

    await asyncio.gather(*(_insert(i, c) for i, c in chunks))

    return TextIngestResponse(status="ok", mode="full_replace", chunks_inserted=inserted)


@router.post("/rows", response_model=RowsIngestResponse)
async def ingest_rows(body: IngestRowsBody) -> RowsIngestResponse:
    """
    Ingest tabular data (rows):
    - Upsert document metadata.
    - Update schema (list of keys).
    - If full_refresh: replace all rows.
    - Otherwise: perform incremental sync (insert new/changed, delete removed).
    """
    # Upsert metadata
    await upsert_document_metadata(body.file_id, body.title, body.url)

    # Derive schema as ordered union of keys (preserves first-seen order)
    schema_keys = list(
        dict.fromkeys(
            k for row in body.rows
            if isinstance(row, dict)
            for k in row.keys()
        )
    )
    if not schema_keys:
        raise HTTPException(status_code=400, detail="Rows must be JSON objects with at least one key.")

    await update_document_schema(body.file_id, schema_keys)

    if body.full_refresh:
        """
        Strict replace for rows if requested:
        - Delete all existing rows for this file.
        - Insert all provided rows.
        """
        await db_exec("DELETE FROM document_rows WHERE dataset_id = $1", body.file_id)
        inserted = 0
        for row in body.rows:
            if not isinstance(row, dict):
                raise HTTPException(status_code=400, detail="Each row must be a JSON object.")
            row_hash = _hash_row(row)
            await db_exec(
                "INSERT INTO document_rows (dataset_id, row_data, row_hash) VALUES ($1, $2::jsonb, $3)",
                body.file_id, json.dumps(row), row_hash,
            )
            inserted += 1

        return RowsIngestResponse(
            status="ok", mode="full_refresh", rows_inserted=inserted, rows_deleted=0, schema_keys=schema_keys
        )

    # Incremental sync (default): insert new/changed, delete removed (strict sync)
    incoming: List[Tuple[str, Dict[str, Any]]] = []
    incoming_hashes: Set[str] = set()
    for row in body.rows:
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail="Each row must be a JSON object.")
        h = _hash_row(row)
        incoming.append((h, row))
        incoming_hashes.add(h)

    existing_rows = await db_fetch(
        "SELECT row_hash FROM document_rows WHERE dataset_id = $1",
        body.file_id,
    )
    existing_hashes: Set[str] = {r.get("row_hash") for r in existing_rows if r.get("row_hash")}

    to_insert = [item for item in incoming if item[0] not in existing_hashes]
    to_delete = list(existing_hashes - incoming_hashes)

    deleted = 0
    inserted = 0

    if to_delete:
        """
        Delete rows that are no longer present in the incoming data.
        """
        await db_exec(
            "DELETE FROM document_rows WHERE dataset_id = $1 AND row_hash = ANY($2::text[])",
            body.file_id, to_delete,
        )
        # `DELETE ... RETURNING` would give exact count; we use len(to_delete) here.
        deleted = len(to_delete)

    for h, row in to_insert:
        """
        Insert new or changed rows.
        """
        await db_exec(
            "INSERT INTO document_rows (dataset_id, row_data, row_hash) VALUES ($1, $2::jsonb, $3)",
            body.file_id, json.dumps(row), h,
        )
        inserted += 1

    return RowsIngestResponse(
        status="ok", mode="incremental", rows_inserted=inserted, rows_deleted=deleted, schema_keys=schema_keys
    )
