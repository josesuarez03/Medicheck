-- Catalogo de condiciones (fisicas y psicologicas) para alimentar a ai-service
-- como contexto recuperable por similitud semantica (RAG) al generar respuestas.
-- Dimension 1024 alineada con Titan Text Embeddings v2, igual que el resto de
-- tablas RAG. Si se cambia el modelo de embeddings, migrar junto con ai-service.

CREATE TABLE IF NOT EXISTS rag.conditions_catalog (
    id serial PRIMARY KEY,
    condition_id varchar(100) NOT NULL UNIQUE,
    name varchar(200) NOT NULL,
    category varchar(20) NOT NULL DEFAULT 'physical',          -- physical | psychological
    synonyms jsonb NOT NULL DEFAULT '[]'::jsonb,
    signals jsonb NOT NULL DEFAULT '[]'::jsonb,
    urgency_level varchar(20) NOT NULL DEFAULT 'moderate',      -- low | moderate | high | emergency
    next_step varchar(50) NOT NULL DEFAULT 'doctor',           -- self_care | doctor | psychologist | emergency
    country_context varchar(10) NOT NULL DEFAULT 'ALL',         -- ALL | VE
    description text NULL,
    source varchar(200) NULL,
    embedding vector(1024) NULL,
    embedding_model text NULL,
    embedding_text text NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    CONSTRAINT conditions_catalog_urgency_chk
        CHECK (urgency_level IN ('low', 'moderate', 'high', 'emergency')),
    CONSTRAINT conditions_catalog_next_step_chk
        CHECK (next_step IN ('self_care', 'doctor', 'psychologist', 'emergency'))
);

CREATE INDEX IF NOT EXISTS idx_conditions_catalog_category
    ON rag.conditions_catalog (category);

CREATE INDEX IF NOT EXISTS idx_conditions_catalog_country
    ON rag.conditions_catalog (country_context);

-- Indice ANN para busqueda por similitud coseno.
CREATE INDEX IF NOT EXISTS idx_conditions_catalog_embedding
    ON rag.conditions_catalog USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
