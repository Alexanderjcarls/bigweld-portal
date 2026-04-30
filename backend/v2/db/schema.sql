CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS bigweld_v2;

CREATE TABLE IF NOT EXISTS bigweld_v2.conversations (
  id UUID PRIMARY KEY,
  title TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE bigweld_v2.conversations
  ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS bigweld_v2.messages (
  id BIGSERIAL PRIMARY KEY,
  conv_id UUID NOT NULL REFERENCES bigweld_v2.conversations(id) ON DELETE CASCADE,
  turn_idx INT NOT NULL,
  role TEXT NOT NULL,
  content TEXT,
  raw_message JSONB NOT NULL,
  token_count INT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (conv_id, turn_idx)
);

CREATE INDEX IF NOT EXISTS idx_messages_conv_turn
  ON bigweld_v2.messages(conv_id, turn_idx);

CREATE TABLE IF NOT EXISTS bigweld_v2.compacted_summaries (
  id BIGSERIAL PRIMARY KEY,
  conv_id UUID NOT NULL REFERENCES bigweld_v2.conversations(id) ON DELETE CASCADE,
  range_start_idx INT NOT NULL,
  range_end_idx INT NOT NULL,
  summary TEXT NOT NULL,
  embedding VECTOR(2560),
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_summaries_conv
  ON bigweld_v2.compacted_summaries(conv_id);

CREATE TABLE IF NOT EXISTS bigweld_v2.artifacts (
  id UUID PRIMARY KEY,
  conv_id UUID NOT NULL REFERENCES bigweld_v2.conversations(id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  current_version INT NOT NULL DEFAULT 1,
  archived_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (type IN ('markdown', 'spreadsheet', 'image', 'mermaid', 'd2', 'pdf', 'powerpoint')),
  CHECK (source IN ('bigweld', 'user_dropped', 'user_pasted', 'cross_conv_pulled'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_conv
  ON bigweld_v2.artifacts(conv_id);

CREATE TABLE IF NOT EXISTS bigweld_v2.artifact_versions (
  artifact_id UUID NOT NULL REFERENCES bigweld_v2.artifacts(id) ON DELETE CASCADE,
  version INT NOT NULL,
  body TEXT,
  body_blob BYTEA,
  diff_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (artifact_id, version)
);

CREATE INDEX IF NOT EXISTS idx_artifact_versions_id
  ON bigweld_v2.artifact_versions(artifact_id);

GRANT USAGE ON SCHEMA bigweld_v2 TO matrix_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bigweld_v2 TO matrix_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA bigweld_v2 TO matrix_admin;
