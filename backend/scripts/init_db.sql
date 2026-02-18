-- =============================================================================
-- BET_HOPE DATABASE INITIALIZATION
-- =============================================================================
-- This script runs on first database creation
-- Enables required PostgreSQL extensions

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable other useful extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
CREATE EXTENSION IF NOT EXISTS btree_gin; -- For faster index scans

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE bet_hope TO bet_hope;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Database initialization complete. pgvector extension enabled.';
END
$$;
