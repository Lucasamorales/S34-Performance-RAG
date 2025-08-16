-- ===========================================
-- Extension: pgcrypto
-- Required for hashing functions (digest, encode).
-- ===========================================
create extension if not exists pgcrypto;

-- ===========================================
-- Column: row_hash
-- Adds a hash column to document_rows for deduplication and integrity.
-- ===========================================
alter table document_rows add column if not exists row_hash text;

-- ===========================================
-- Data Migration: Initialize row_hash for existing rows
-- Uses SHA-256 hash of row_data::text (jsonb::text is stable for jsonb).
-- Only updates rows where row_hash is currently null.
-- ===========================================
update document_rows
set row_hash = encode(digest(row_data::text, 'sha256'), 'hex')
where row_hash is null;

-- ===========================================
-- Index: document_rows_unique_dataset_hash
-- Ensures no duplicate logical row (by hash) within the same dataset.
-- ===========================================
create unique index if not exists document_rows_unique_dataset_hash 
on document_rows (dataset_id, row_hash);