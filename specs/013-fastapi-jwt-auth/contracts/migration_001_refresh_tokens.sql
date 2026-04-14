-- Migration: 001_add_refresh_and_reset_tables
-- Feature: 013-fastapi-jwt-auth
-- Created: 2026-04-09
-- Description: Add refresh_tokens and password_reset_tokens tables for JWT auth

-- ============================================
-- Refresh Tokens Table (Token Rotation)
-- ============================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for token lookup during refresh (critical path)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
    ON refresh_tokens(token_hash);

-- Composite index for user token queries and cleanup
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_exp_revoked
    ON refresh_tokens(user_id, expired, revoked_at);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_refresh_tokens_updated_at ON refresh_tokens;
CREATE TRIGGER trigger_refresh_tokens_updated_at
    BEFORE UPDATE ON refresh_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Password Reset Tokens Table
-- ============================================

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for token verification during reset
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash
    ON password_reset_tokens(token_hash);

-- Index for user-specific token queries and cleanup
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_used
    ON password_reset_tokens(user_id, used_at);

-- ============================================
-- Row Level Security (Optional, for multi-tenancy)
-- ============================================
-- Note: RLS not enabled by default. Uncomment if needed.
-- ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Cleanup Function (scheduled job candidate)
-- ============================================

-- Remove expired/revoked refresh tokens older than 30 days
CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM refresh_tokens
    WHERE (revoked_at IS NOT NULL AND expires_at < NOW() - INTERVAL '30 days')
       OR (expires_at < NOW());
END;
$$ LANGUAGE plpgsql;

-- Remove used/expired password reset tokens older than 7 days
CREATE OR REPLACE FUNCTION cleanup_used_reset_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM password_reset_tokens
    WHERE (used_at IS NOT NULL AND created_at < NOW() - INTERVAL '7 days')
       OR (expires_at < NOW());
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Rollback (DOWN migration)
-- ============================================
/*
-- To rollback this migration:
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS cleanup_expired_refresh_tokens();
DROP FUNCTION IF EXISTS cleanup_used_reset_tokens();
*/
