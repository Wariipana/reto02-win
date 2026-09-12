-- Capa 2: Normalización. Esquema único para todas las fuentes con texto,
-- más una tabla separada para series de conteo puras (Google Trends).
-- Ver CLAUDE.md, arquitectura propuesta, Capa 2 y Capa 4.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS items (
    id              TEXT PRIMARY KEY,          -- sha256 corto de fuente|url|fecha (ver ingest/schema.py)
    fuente          TEXT NOT NULL,             -- google_news, google_play, tiktok, prensa_rpp, etc.
    marca           TEXT NOT NULL DEFAULT 'WIN',
    texto           TEXT NOT NULL DEFAULT '',
    fecha           TIMESTAMPTZ NOT NULL,
    url             TEXT NOT NULL,
    autor_hash      TEXT,
    geo             TEXT,
    rating          REAL,
    engagement      JSONB,
    texto_hash      TEXT,                      -- hash normalizado del texto, para exact-dedup
    embedding       vector(384),               -- paraphrase-multilingual-MiniLM-L12-v2 (Capa 3)
    tema            TEXT,                      -- clasificador propio (Capa 3)
    sentimiento     TEXT,                      -- pysentimiento (Capa 3)
    severidad       SMALLINT,                  -- señales de escalamiento (Capa 3)
    es_ruido        BOOLEAN NOT NULL DEFAULT FALSE, -- feedback "esto es ruido" del tablero
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_fecha ON items (fecha);
CREATE INDEX IF NOT EXISTS idx_items_fuente ON items (fuente);
CREATE INDEX IF NOT EXISTS idx_items_marca ON items (marca);
CREATE INDEX IF NOT EXISTS idx_items_texto_hash ON items (texto_hash);
CREATE INDEX IF NOT EXISTS idx_items_tema ON items (tema);

-- Near-duplicate search (MinHash real se calcula en Python; esto sirve para
-- similitud semántica vía embeddings una vez poblada la Capa 3)
CREATE INDEX IF NOT EXISTS idx_items_embedding ON items
    USING hnsw (embedding vector_cosine_ops);

-- Serie temporal cruda de Google Trends: no es texto, alimenta directo la Capa 4
CREATE TABLE IF NOT EXISTS trends_series (
    id          BIGSERIAL PRIMARY KEY,
    marca       TEXT NOT NULL,
    fecha       TIMESTAMPTZ NOT NULL,
    valor       INTEGER NOT NULL,
    granularidad TEXT NOT NULL DEFAULT 'hora', -- 'hora' o 'dia'
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (marca, fecha, granularidad)
);

CREATE INDEX IF NOT EXISTS idx_trends_marca_fecha ON trends_series (marca, fecha);
