-- Enable the pgvector extension for vector similarity search.
create extension if not exists vector;

-- ===========================================
-- Table: documents
-- Stores text documents with vector embeddings for similarity search.
-- ===========================================
create table if not exists documents (
    id bigserial primary key, -- Unique identifier for each document
    content text not null,    -- The main text content of the document
    metadata jsonb default '{}'::jsonb, -- Optional metadata as JSONB
    embedding vector(1536) not null     -- Vector embedding for similarity search
);

-- ===========================================
-- Function: match_documents
-- Returns the most similar documents to a given embedding.
-- Parameters:
--   query_embedding: The embedding to compare against.
--   match_count: Maximum number of matches to return (optional).
--   filter: JSONB filter to match against document metadata (optional).
-- Returns:
--   id, content, metadata, similarity score (higher is more similar).
-- ===========================================
create or replace function match_documents(
    query_embedding vector(1536),
    match_count int default null,
    filter jsonb default '{}'::jsonb
) returns table (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
) language plpgsql as $$
begin
    -- Safety: Ensure match_count is positive if provided
    if match_count is not null and match_count <= 0 then
        raise exception 'match_count must be positive';
    end if;

    -- Return the most similar documents, filtered by metadata if provided
    return query
    select
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) as similarity
    from documents d
    where (filter = '{}'::jsonb or d.metadata @> filter)
      and d.embedding is not null
    order by d.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- ===========================================
-- Table: document_metadata
-- Stores metadata for datasets/documents.
-- ===========================================
create table if not exists document_metadata (
    id text primary key,           -- Unique identifier for the dataset/document
    title text,                    -- Title of the document
    url text,                      -- Source URL
    created_at timestamp default now(), -- Creation timestamp
    schema text                    -- Optional schema information
);

-- ===========================================
-- Table: document_rows
-- Stores tabular data rows associated with a document/dataset.
-- ===========================================
create table if not exists document_rows (
    id serial primary key,                         -- Unique row identifier
    dataset_id text references document_metadata(id) on delete cascade, -- Foreign key to document_metadata
    row_data jsonb not null                        -- Row data as JSONB
);

