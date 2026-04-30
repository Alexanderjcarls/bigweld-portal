CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES bigweld_v2.conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  raw_message JSONB NOT NULL,
  turn_idx INT NOT NULL,
  token_count INT NOT NULL DEFAULT 0,
  finish_reason TEXT,
  usage JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (conversation_id, turn_idx)
);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'bigweld_v2'
      AND table_name = 'messages'
      AND column_name = 'conv_id'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'bigweld_v2'
      AND table_name = 'messages'
      AND column_name = 'conversation_id'
  ) THEN
    ALTER TABLE bigweld_v2.messages RENAME COLUMN conv_id TO conversation_id;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'bigweld_v2'
      AND table_name = 'messages'
      AND column_name = 'ts'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'bigweld_v2'
      AND table_name = 'messages'
      AND column_name = 'created_at'
  ) THEN
    ALTER TABLE bigweld_v2.messages RENAME COLUMN ts TO created_at;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'bigweld_v2'
      AND table_name = 'messages'
      AND column_name = 'id'
      AND data_type <> 'uuid'
  ) THEN
    ALTER TABLE bigweld_v2.messages ALTER COLUMN id DROP DEFAULT;
    ALTER TABLE bigweld_v2.messages ALTER COLUMN id TYPE UUID USING gen_random_uuid();
  END IF;
END $$;

ALTER TABLE bigweld_v2.messages
  ADD COLUMN IF NOT EXISTS finish_reason TEXT,
  ADD COLUMN IF NOT EXISTS usage JSONB,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE bigweld_v2.messages
  ALTER COLUMN id SET DEFAULT gen_random_uuid(),
  ALTER COLUMN token_count SET DEFAULT 0;

UPDATE bigweld_v2.messages SET token_count = 0 WHERE token_count IS NULL;

ALTER TABLE bigweld_v2.messages
  ALTER COLUMN token_count SET NOT NULL,
  DROP COLUMN IF EXISTS content,
  DROP COLUMN IF EXISTS conv_id,
  DROP COLUMN IF EXISTS ts;

DROP INDEX IF EXISTS bigweld_v2.idx_messages_conv_turn;

CREATE INDEX IF NOT EXISTS idx_messages_conversation_turn
  ON bigweld_v2.messages(conversation_id, turn_idx);

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
