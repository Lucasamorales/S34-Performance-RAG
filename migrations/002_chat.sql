-- ===========================================
-- Table: chat_messages
-- Stores messages exchanged in chat sessions, including user, assistant, and system messages.
-- ===========================================
create table if not exists chat_messages (
    id bigserial primary key, -- Unique identifier for each message
    session_id text not null, -- Identifier for the chat session
    role text not null check (role in ('user', 'assistant', 'system')), -- Role of the message sender
    content text not null, -- The message content
    created_at timestamp default now() -- Timestamp when the message was created
);

-- ===========================================
-- Index: chat_messages_session_idx
-- Speeds up queries filtering by session and ordering by creation time.
-- ===========================================
create index if not exists chat_messages_session_idx on chat_messages (session_id, created_at);