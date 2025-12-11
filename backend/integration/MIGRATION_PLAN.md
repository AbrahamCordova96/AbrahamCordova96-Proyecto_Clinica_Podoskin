# Database Migration Plan for Integration Features

## Overview
This document outlines the database schema changes required to support voice-controlled frontend integration (Gemini Live + LangGraph).

## ⚠️ IMPORTANT: Pre-Migration Checklist

- [ ] **Backup**: Take full database backup of all 3 databases
- [ ] **Test Restore**: Verify backup can be restored successfully
- [ ] **Staging**: Apply migration to staging environment first
- [ ] **Validation**: Validate all features work in staging
- [ ] **Approval**: Get approval from @SalvadorCordova96 before production
- [ ] **Downtime**: Schedule maintenance window if needed
- [ ] **Rollback Plan**: Have rollback script ready

## 🗄️ Database: clinica_auth_db (schema: auth)

### 1. Enhance audit_log table

```sql
-- Add new columns for enhanced auditing
ALTER TABLE auth.audit_log 
    ADD COLUMN IF NOT EXISTS username VARCHAR(50),
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS method VARCHAR(10),
    ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255),
    ADD COLUMN IF NOT EXISTS request_body TEXT,
    ADD COLUMN IF NOT EXISTS response_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS source_refs JSONB,
    ADD COLUMN IF NOT EXISTS note TEXT;

-- Make registro_id nullable (not all audit entries have a specific record)
ALTER TABLE auth.audit_log 
    ALTER COLUMN registro_id DROP NOT NULL;

-- Remove duplicate primary key on timestamp_accion
-- (id_log is already the primary key)
ALTER TABLE auth.audit_log 
    DROP CONSTRAINT IF EXISTS audit_log_pkey;

ALTER TABLE auth.audit_log 
    ADD PRIMARY KEY (id_log);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_log_session 
    ON auth.audit_log(session_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_endpoint 
    ON auth.audit_log(endpoint);

CREATE INDEX IF NOT EXISTS idx_audit_log_username 
    ON auth.audit_log(username);
```

### 2. Create voice_transcripts table

```sql
-- Create table for voice conversation transcripts
CREATE TABLE IF NOT EXISTS auth.voice_transcripts (
    id_transcript BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id BIGINT NOT NULL REFERENCES auth.sys_usuarios(id_usuario) ON DELETE CASCADE,
    user_text TEXT NOT NULL,
    assistant_text TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    langgraph_job_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_voice_transcripts_session 
    ON auth.voice_transcripts(session_id);

CREATE INDEX IF NOT EXISTS idx_voice_transcripts_user 
    ON auth.voice_transcripts(user_id);

CREATE INDEX IF NOT EXISTS idx_voice_transcripts_timestamp 
    ON auth.voice_transcripts(timestamp);

-- Add comment
COMMENT ON TABLE auth.voice_transcripts IS 
    'Stores voice conversation transcripts for audit and history. Contains PII/PHI - implement retention policy.';
```

## 📋 Migration Scripts

### Forward Migration (Apply Changes)

Save as: `migrations/001_add_integration_features.sql`

```sql
-- ================================================
-- Migration 001: Add Integration Features
-- Description: Add support for voice frontend integration
-- Author: System
-- Date: 2025-12-11
-- Database: clinica_auth_db
-- ================================================

BEGIN;

-- 1. Enhance audit_log
ALTER TABLE auth.audit_log 
    ADD COLUMN IF NOT EXISTS username VARCHAR(50),
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS method VARCHAR(10),
    ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255),
    ADD COLUMN IF NOT EXISTS request_body TEXT,
    ADD COLUMN IF NOT EXISTS response_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS source_refs JSONB,
    ADD COLUMN IF NOT EXISTS note TEXT;

ALTER TABLE auth.audit_log 
    ALTER COLUMN registro_id DROP NOT NULL;

-- Fix primary key
ALTER TABLE auth.audit_log 
    DROP CONSTRAINT IF EXISTS audit_log_pkey;
ALTER TABLE auth.audit_log 
    ADD PRIMARY KEY (id_log);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_session 
    ON auth.audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_endpoint 
    ON auth.audit_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_audit_log_username 
    ON auth.audit_log(username);

-- 2. Create voice_transcripts
CREATE TABLE IF NOT EXISTS auth.voice_transcripts (
    id_transcript BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id BIGINT NOT NULL REFERENCES auth.sys_usuarios(id_usuario) ON DELETE CASCADE,
    user_text TEXT NOT NULL,
    assistant_text TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    langgraph_job_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_transcripts_session 
    ON auth.voice_transcripts(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_transcripts_user 
    ON auth.voice_transcripts(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_transcripts_timestamp 
    ON auth.voice_transcripts(timestamp);

COMMENT ON TABLE auth.voice_transcripts IS 
    'Stores voice conversation transcripts for audit and history. Contains PII/PHI - implement retention policy.';

COMMIT;

-- Verification queries
SELECT 'audit_log columns' as check_type, 
       column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'auth' 
  AND table_name = 'audit_log'
ORDER BY ordinal_position;

SELECT 'voice_transcripts table' as check_type,
       count(*) as row_count
FROM auth.voice_transcripts;
```

### Rollback Migration (Undo Changes)

Save as: `migrations/001_rollback_integration_features.sql`

```sql
-- ================================================
-- Rollback 001: Remove Integration Features
-- Description: Rollback voice frontend integration changes
-- Author: System
-- Date: 2025-12-11
-- Database: clinica_auth_db
-- ================================================

BEGIN;

-- 1. Drop voice_transcripts table
DROP TABLE IF EXISTS auth.voice_transcripts CASCADE;

-- 2. Remove new columns from audit_log
ALTER TABLE auth.audit_log 
    DROP COLUMN IF EXISTS username,
    DROP COLUMN IF EXISTS session_id,
    DROP COLUMN IF EXISTS method,
    DROP COLUMN IF EXISTS endpoint,
    DROP COLUMN IF EXISTS request_body,
    DROP COLUMN IF EXISTS response_hash,
    DROP COLUMN IF EXISTS source_refs,
    DROP COLUMN IF EXISTS note;

-- 3. Restore registro_id NOT NULL constraint (optional, may fail if NULL values exist)
-- ALTER TABLE auth.audit_log 
--     ALTER COLUMN registro_id SET NOT NULL;

-- 4. Drop new indexes
DROP INDEX IF EXISTS auth.idx_audit_log_session;
DROP INDEX IF EXISTS auth.idx_audit_log_endpoint;
DROP INDEX IF EXISTS auth.idx_audit_log_username;

COMMIT;
```

## 🧪 Validation Queries

### Check Migration Success

```sql
-- Verify audit_log enhancements
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'auth' 
    AND table_name = 'audit_log'
    AND column_name IN ('username', 'session_id', 'method', 'endpoint', 
                        'request_body', 'response_hash', 'source_refs', 'note')
ORDER BY column_name;

-- Verify voice_transcripts table exists
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'auth' 
    AND table_name = 'voice_transcripts';

-- Verify indexes
SELECT 
    indexname,
    tablename
FROM pg_indexes
WHERE schemaname = 'auth' 
    AND (tablename = 'audit_log' OR tablename = 'voice_transcripts')
ORDER BY tablename, indexname;
```

## 📊 Impact Assessment

### Storage Impact
- **audit_log**: ~100-200 bytes per row increase (8 new columns)
- **voice_transcripts**: New table, estimate ~500 bytes per transcript
  - Projected: 100 transcripts/day = 50KB/day = ~18MB/year
  - With retention policy (90 days): ~4.5MB stable storage

### Performance Impact
- **audit_log**: Minimal impact, new indexes improve query performance
- **voice_transcripts**: New table, no impact on existing queries
- **Middleware**: Slight overhead on write operations (~5-10ms per request)

### Backward Compatibility
- ✅ All changes are additive (no breaking changes)
- ✅ Existing queries continue to work
- ✅ NULL values allowed for new columns
- ✅ Indexes are optional (IF NOT EXISTS)

## 🔒 Security Considerations

### PII/PHI Protection
- `voice_transcripts` contains sensitive conversation data
- Implement retention policy (default: 90 days)
- Require user consent before storing transcripts
- Implement data export for GDPR compliance

### Audit Trail
- All changes logged in `audit_log`
- Response hashes enable non-repudiation
- Source references enable verification

## 📝 Post-Migration Tasks

1. **Update ORM Models**: Ensure SQLAlchemy models match schema
2. **Test Integration Endpoints**: Verify all new endpoints work
3. **Enable Audit Middleware**: Configure in app.py (optional)
4. **Implement Retention Policy**: Create scheduled job to purge old transcripts
5. **Monitor Logs**: Watch for any migration-related errors
6. **Update Documentation**: Update API docs with new endpoints

## 🚨 Troubleshooting

### Issue: Migration fails on registro_id NOT NULL
**Solution**: Some audit logs may have NULL registro_id. This is expected for system-level events.
```sql
-- Check for NULL values
SELECT COUNT(*) FROM auth.audit_log WHERE registro_id IS NULL;
-- If exists, DROP NOT NULL is correct
```

### Issue: Duplicate primary key constraint
**Solution**: Drop existing constraint first
```sql
ALTER TABLE auth.audit_log DROP CONSTRAINT IF EXISTS audit_log_pkey;
ALTER TABLE auth.audit_log DROP CONSTRAINT IF EXISTS audit_log_timestamp_accion_key;
```

### Issue: voice_transcripts foreign key fails
**Solution**: Ensure sys_usuarios table exists and has data
```sql
SELECT COUNT(*) FROM auth.sys_usuarios;
```

## 📞 Support

For migration issues or questions:
1. Check logs in `/var/log/postgresql/`
2. Verify backup is valid and restorable
3. Contact: @SalvadorCordova96

---

**Status**: Ready for Review
**Requires Approval**: Yes
**Breaking Changes**: None
**Estimated Downtime**: < 1 minute
