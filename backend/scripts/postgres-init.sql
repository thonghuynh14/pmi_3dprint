-- Postgres extensions cần cho dự án (chạy 1 lần khi container khởi tạo)
-- Tham khảo: docs/architecture/db-schema/SKILL.md

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- gen_random_uuid alternative
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- fuzzy text search
CREATE EXTENSION IF NOT EXISTS "ltree";           -- category tree
CREATE EXTENSION IF NOT EXISTS "btree_gin";       -- composite GIN
CREATE EXTENSION IF NOT EXISTS "unaccent";        -- VN accent-insensitive search

-- Helper function cho VN search (unaccent wrapped IMMUTABLE để dùng trong index)
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text AS $$
  SELECT unaccent('unaccent', $1);
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'Extensions installed: %', (
    SELECT string_agg(extname, ', ')
    FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'pgcrypto', 'pg_trgm', 'ltree', 'btree_gin', 'unaccent')
  );
END $$;
