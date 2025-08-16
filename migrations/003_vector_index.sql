-- ===========================================
-- Index: documents_embedding_ivfflat
-- Creates an IVF Flat index on the embedding column for efficient vector similarity search.
-- Requires pgvector >= 0.5. Adjust the 'lists' parameter based on dataset size for optimal performance.
-- ===========================================
create index if not exists documents_embedding_ivfflat
    on documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ===========================================
-- Analyze: documents
-- Updates planner statistics for the documents table to optimize query performance.
-- ===========================================
analyze documents;