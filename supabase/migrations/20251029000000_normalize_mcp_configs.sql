-- ====================================================================
-- Normalize MCP Configuration Storage
-- ====================================================================
--
-- Purpose: Replace single-table JSONB storage with normalized schema
--
-- Changes:
-- 1. Create mcp_config_files table (file-level metadata)
-- 2. Create mcp_servers table (individual server configurations)
-- 3. Migrate existing mcp_configs.config_data to new structure
-- 4. Drop old mcp_configs table
--
-- Benefits:
-- - Queryable server configurations (filter by type, command, url)
-- - Indexed columns for efficient searches
-- - Referential integrity with foreign keys
-- - Check constraints for data validation
-- ====================================================================

-- ====================================================================
-- PART 1: Create New Tables
-- ====================================================================

-- Table 1: MCP Config Files (file-level metadata)
CREATE TABLE IF NOT EXISTS mcp_config_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id TEXT NOT NULL,

    -- File identification
    config_name TEXT NOT NULL,  -- e.g., 'claude_mcp_config' or 'mcp_config'
    file_path TEXT NOT NULL,    -- Relative path like '.claude-mcp-config.json'
    file_type TEXT CHECK (file_type IN ('claude-mcp-config', 'mcp')),  -- Which config file format

    -- Metadata from _metadata section (if present in JSON)
    metadata_machine_id TEXT,   -- Can differ from machine_id (from _metadata.machine_id)
    metadata_created_at TIMESTAMPTZ,  -- From _metadata.created_at
    metadata_auto_generated BOOLEAN DEFAULT false,  -- From _metadata.auto_generated
    metadata_repo_root TEXT,    -- From _metadata.repo_root

    -- Scope
    scope TEXT DEFAULT 'global' CHECK (scope IN ('global', 'project')),
    is_global BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one config per machine+name
    UNIQUE(machine_id, config_name)
);

-- Table 2: MCP Servers (individual server configurations)
CREATE TABLE IF NOT EXISTS mcp_servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_file_id UUID REFERENCES mcp_config_files(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,  -- Denormalized for faster queries

    -- Server identification
    server_name TEXT NOT NULL,  -- Key from mcpServers object (e.g., "claude-tasks-dev")

    -- Transport configuration
    transport_type TEXT NOT NULL CHECK (transport_type IN ('stdio', 'http', 'sse')),

    -- Common fields (all transport types)
    disabled BOOLEAN DEFAULT false,      -- Temporarily disable server
    always_allow BOOLEAN DEFAULT false,  -- Skip permission prompts (alwaysAllow in JSON)

    -- Stdio-specific fields
    command TEXT,                -- Executable path (for stdio)
    args JSONB,                  -- Array of command arguments (for stdio)
    env JSONB,                   -- Object of environment variables (for stdio)

    -- HTTP/SSE-specific fields
    url TEXT,                    -- Remote server endpoint (for http/sse)
    headers JSONB,               -- Object of HTTP headers (for http/sse)

    -- Display order (preserve order from JSON file)
    sort_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one server name per config file
    UNIQUE(config_file_id, server_name),

    -- Check constraints for transport-specific fields
    CONSTRAINT check_stdio_fields CHECK (
        CASE
            WHEN transport_type = 'stdio' THEN command IS NOT NULL
            ELSE true
        END
    ),
    CONSTRAINT check_http_sse_fields CHECK (
        CASE
            WHEN transport_type IN ('http', 'sse') THEN url IS NOT NULL
            ELSE true
        END
    )
);

-- ====================================================================
-- PART 2: Indexes
-- ====================================================================

-- Config files indexes
CREATE INDEX IF NOT EXISTS idx_mcp_config_files_machine ON mcp_config_files(machine_id);
CREATE INDEX IF NOT EXISTS idx_mcp_config_files_scope ON mcp_config_files(scope);

-- Servers indexes
CREATE INDEX IF NOT EXISTS idx_mcp_servers_config_file ON mcp_servers(config_file_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_machine ON mcp_servers(machine_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_name ON mcp_servers(server_name);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_transport ON mcp_servers(transport_type);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_disabled ON mcp_servers(disabled);

-- ====================================================================
-- PART 3: Triggers
-- ====================================================================

CREATE TRIGGER update_mcp_config_files_updated_at BEFORE UPDATE ON mcp_config_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_servers_updated_at BEFORE UPDATE ON mcp_servers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================
-- PART 4: Migrate Existing Data
-- ====================================================================

DO $$
DECLARE
    config_record RECORD;
    config_file_id UUID;
    server_name TEXT;
    server_config JSONB;
    transport_type TEXT;
    idx INTEGER;
BEGIN
    -- Check if mcp_configs table exists and has data
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mcp_configs') THEN

        -- Iterate through existing configs
        FOR config_record IN
            SELECT * FROM mcp_configs
        LOOP
            -- Insert config file record
            INSERT INTO mcp_config_files (
                machine_id,
                config_name,
                file_path,
                file_type,
                metadata_machine_id,
                metadata_created_at,
                metadata_auto_generated,
                metadata_repo_root,
                scope,
                is_global,
                created_at,
                updated_at
            ) VALUES (
                config_record.machine_id,
                config_record.config_name,
                config_record.file_path,
                'claude-mcp-config',  -- Default type
                config_record.config_data->'_metadata'->>'machine_id',
                (config_record.config_data->'_metadata'->>'created_at')::TIMESTAMPTZ,
                (config_record.config_data->'_metadata'->>'auto_generated')::BOOLEAN,
                config_record.config_data->'_metadata'->>'repo_root',
                config_record.scope,
                config_record.is_global,
                config_record.created_at,
                config_record.updated_at
            )
            RETURNING id INTO config_file_id;

            -- Insert server records from mcpServers object
            idx := 0;
            FOR server_name, server_config IN
                SELECT * FROM jsonb_each(config_record.config_data->'mcpServers')
            LOOP
                -- Detect transport type (handle both 'type' and 'transport' keys)
                transport_type := COALESCE(
                    server_config->>'type',
                    server_config->>'transport',
                    'stdio'  -- Default to stdio if not specified
                );

                -- Insert server
                INSERT INTO mcp_servers (
                    config_file_id,
                    machine_id,
                    server_name,
                    transport_type,
                    disabled,
                    always_allow,
                    command,
                    args,
                    env,
                    url,
                    headers,
                    sort_order
                ) VALUES (
                    config_file_id,
                    config_record.machine_id,
                    server_name,
                    transport_type,
                    COALESCE((server_config->>'disabled')::BOOLEAN, false),
                    COALESCE((server_config->>'alwaysAllow')::BOOLEAN, false),
                    server_config->>'command',
                    server_config->'args',
                    server_config->'env',
                    server_config->>'url',
                    server_config->'headers',
                    idx
                );

                idx := idx + 1;
            END LOOP;
        END LOOP;

        RAISE NOTICE 'Migrated % config file(s) from mcp_configs to mcp_config_files',
            (SELECT COUNT(*) FROM mcp_config_files);
        RAISE NOTICE 'Created % server record(s) in mcp_servers',
            (SELECT COUNT(*) FROM mcp_servers);
    ELSE
        RAISE NOTICE 'mcp_configs table does not exist, skipping migration';
    END IF;
END $$;

-- ====================================================================
-- PART 5: Drop Old Table (after verification)
-- ====================================================================

-- Uncomment after verifying migration succeeded:
-- DROP TABLE IF EXISTS mcp_configs CASCADE;

-- ====================================================================
-- PART 6: Row Level Security
-- ====================================================================

ALTER TABLE mcp_config_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_servers ENABLE ROW LEVEL SECURITY;

-- Allow all operations policies (can be tightened later with auth)
CREATE POLICY "Allow all operations on mcp_config_files" ON mcp_config_files FOR ALL USING (true);
CREATE POLICY "Allow all operations on mcp_servers" ON mcp_servers FOR ALL USING (true);

-- ====================================================================
-- PART 7: Comments for Documentation
-- ====================================================================

COMMENT ON TABLE mcp_config_files IS 'Normalized MCP configuration file metadata (replaces mcp_configs.config_data)';
COMMENT ON TABLE mcp_servers IS 'Individual MCP server configurations with normalized columns for queryability';

COMMENT ON COLUMN mcp_servers.transport_type IS 'Transport protocol: stdio (command-based), http (REST), or sse (Server-Sent Events)';
COMMENT ON COLUMN mcp_servers.args IS 'JSONB array of command-line arguments (stdio only)';
COMMENT ON COLUMN mcp_servers.env IS 'JSONB object of environment variables (stdio only)';
COMMENT ON COLUMN mcp_servers.headers IS 'JSONB object of HTTP headers (http/sse only)';
COMMENT ON COLUMN mcp_servers.always_allow IS 'Skip permission prompts for this server (from alwaysAllow in JSON)';

-- ====================================================================
-- Migration Complete
-- ====================================================================

-- To verify migration:
--   SELECT cf.*, COUNT(ms.id) as server_count
--   FROM mcp_config_files cf
--   LEFT JOIN mcp_servers ms ON cf.id = ms.config_file_id
--   GROUP BY cf.id;
