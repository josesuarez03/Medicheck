-- Dimension por defecto alineada con Titan Text Embeddings v2.
-- Si se cambia de modelo/vector size, esta tabla debe migrarse junto con ai-service.

CREATE TABLE IF NOT EXISTS rag.conversation_embeddings (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL,
    patient_id uuid NULL,
    conversation_id uuid NOT NULL,
    source_turn_id text NULL,
    embedding_model text NOT NULL,
    embedding vector(1024) NOT NULL,
    embedding_text text NOT NULL,
    facts_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    signal_score numeric(4,3) NOT NULL,
    triage_level varchar(20) NULL,
    clinical_topic varchar(100) NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    episode_timestamp timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_user_conversation_created
    ON rag.conversation_embeddings (user_id, conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_user_signal
    ON rag.conversation_embeddings (user_id, signal_score);

CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_triage
    ON rag.conversation_embeddings (triage_level);

CREATE TABLE IF NOT EXISTS rag.user_summary_embeddings (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL UNIQUE,
    patient_id uuid NOT NULL UNIQUE,
    clinical_summary_id uuid NOT NULL,
    embedding_model text NOT NULL,
    embedding vector(1024) NOT NULL,
    summary_text text NOT NULL,
    clinical_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    summary_version integer NOT NULL,
    source_updated_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_summary_embeddings_summary_version
    ON rag.user_summary_embeddings (summary_version);
