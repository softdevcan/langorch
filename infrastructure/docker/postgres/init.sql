-- PostgreSQL initialization script
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Initial database setup
\c langorch;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS tenants;
CREATE SCHEMA IF NOT EXISTS workflows;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO langorch;
GRANT ALL PRIVILEGES ON SCHEMA tenants TO langorch;
GRANT ALL PRIVILEGES ON SCHEMA workflows TO langorch;
GRANT ALL PRIVILEGES ON SCHEMA monitoring TO langorch;
