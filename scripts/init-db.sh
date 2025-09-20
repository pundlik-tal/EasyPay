#!/bin/bash
# EasyPay Payment Gateway - Database Initialization Script
# This script initializes the production database with proper settings

set -e

echo "Starting database initialization..."

# Create database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    CREATE EXTENSION IF NOT EXISTS "btree_gin";
    
    -- Create custom functions
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';
    
    -- Create indexes for performance
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_status ON payments(status);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_created_at ON payments(created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_external_id ON payments(external_id);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_amount ON payments(amount);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_customer_id ON payments(customer_id);
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_event_type ON webhooks(event_type);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_status ON webhooks(status);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_created_at ON webhooks(created_at);
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
    
    -- Create partial indexes for better performance
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_failed ON payments(id) WHERE status = 'failed';
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_pending ON payments(id) WHERE status = 'pending';
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_failed ON webhooks(id) WHERE status = 'failed';
    
    -- Create composite indexes
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_status_created ON payments(status, created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_event_status ON webhooks(event_type, status);
    
    -- Set up connection limits and timeouts
    ALTER SYSTEM SET max_connections = 200;
    ALTER SYSTEM SET shared_buffers = '256MB';
    ALTER SYSTEM SET effective_cache_size = '1GB';
    ALTER SYSTEM SET maintenance_work_mem = '64MB';
    ALTER SYSTEM SET checkpoint_completion_target = 0.9;
    ALTER SYSTEM SET wal_buffers = '16MB';
    ALTER SYSTEM SET default_statistics_target = 100;
    ALTER SYSTEM SET random_page_cost = 1.1;
    ALTER SYSTEM SET effective_io_concurrency = 200;
    
    -- Enable query logging for performance monitoring
    ALTER SYSTEM SET log_statement = 'mod';
    ALTER SYSTEM SET log_min_duration_statement = 1000;
    ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
    
    -- Reload configuration
    SELECT pg_reload_conf();
    
    -- Create monitoring views
    CREATE OR REPLACE VIEW payment_stats AS
    SELECT 
        DATE(created_at) as date,
        status,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        AVG(amount) as avg_amount
    FROM payments
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(created_at), status
    ORDER BY date DESC, status;
    
    CREATE OR REPLACE VIEW webhook_stats AS
    SELECT 
        DATE(created_at) as date,
        event_type,
        status,
        COUNT(*) as count
    FROM webhooks
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(created_at), event_type, status
    ORDER BY date DESC, event_type, status;
    
    -- Grant permissions
    GRANT SELECT ON payment_stats TO easypay;
    GRANT SELECT ON webhook_stats TO easypay;
    
    -- Create backup user
    CREATE USER backup_user WITH PASSWORD 'backup_password';
    GRANT CONNECT ON DATABASE easypay TO backup_user;
    GRANT USAGE ON SCHEMA public TO backup_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
    GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO backup_user;
    
    -- Create read-only user for reporting
    CREATE USER readonly_user WITH PASSWORD 'readonly_password';
    GRANT CONNECT ON DATABASE easypay TO readonly_user;
    GRANT USAGE ON SCHEMA public TO readonly_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
    GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly_user;
    
    -- Set up row level security for sensitive data
    ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
    
    -- Create policies for row level security
    CREATE POLICY payment_access_policy ON payments
        FOR ALL TO easypay
        USING (true);
    
    CREATE POLICY webhook_access_policy ON webhooks
        FOR ALL TO easypay
        USING (true);
    
    CREATE POLICY audit_log_access_policy ON audit_logs
        FOR ALL TO easypay
        USING (true);
    
    -- Create policies for read-only user
    CREATE POLICY payment_read_policy ON payments
        FOR SELECT TO readonly_user
        USING (true);
    
    CREATE POLICY webhook_read_policy ON webhooks
        FOR SELECT TO readonly_user
        USING (true);
    
    CREATE POLICY audit_log_read_policy ON audit_logs
        FOR SELECT TO readonly_user
        USING (true);
    
    -- Create policies for backup user
    CREATE POLICY payment_backup_policy ON payments
        FOR SELECT TO backup_user
        USING (true);
    
    CREATE POLICY webhook_backup_policy ON webhooks
        FOR SELECT TO backup_user
        USING (true);
    
    CREATE POLICY audit_log_backup_policy ON audit_logs
        FOR SELECT TO backup_user
        USING (true);
    
    -- Create function for cleanup of old data
    CREATE OR REPLACE FUNCTION cleanup_old_data()
    RETURNS void AS \$\$
    BEGIN
        -- Delete old audit logs (older than 1 year)
        DELETE FROM audit_logs WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
        
        -- Delete old webhook attempts (older than 6 months)
        DELETE FROM webhooks WHERE created_at < CURRENT_DATE - INTERVAL '6 months' AND status = 'failed';
        
        -- Update statistics
        ANALYZE;
    END;
    \$\$ LANGUAGE plpgsql;
    
    -- Create scheduled job for cleanup (requires pg_cron extension)
    -- SELECT cron.schedule('cleanup-old-data', '0 3 * * 0', 'SELECT cleanup_old_data();');
    
    -- Create function for database health check
    CREATE OR REPLACE FUNCTION health_check()
    RETURNS TABLE(
        check_name text,
        status text,
        details text
    ) AS \$\$
    BEGIN
        RETURN QUERY
        SELECT 'database_connection'::text, 'ok'::text, 'Database is accessible'::text
        UNION ALL
        SELECT 'table_count'::text, 'ok'::text, (SELECT COUNT(*)::text FROM information_schema.tables WHERE table_schema = 'public')
        UNION ALL
        SELECT 'payment_count'::text, 'ok'::text, (SELECT COUNT(*)::text FROM payments)
        UNION ALL
        SELECT 'webhook_count'::text, 'ok'::text, (SELECT COUNT(*)::text FROM webhooks)
        UNION ALL
        SELECT 'audit_log_count'::text, 'ok'::text, (SELECT COUNT(*)::text FROM audit_logs);
    END;
    \$\$ LANGUAGE plpgsql;
    
    -- Grant execute permission on functions
    GRANT EXECUTE ON FUNCTION cleanup_old_data() TO easypay;
    GRANT EXECUTE ON FUNCTION health_check() TO easypay;
    GRANT EXECUTE ON FUNCTION health_check() TO readonly_user;
    
    -- Create database statistics view
    CREATE OR REPLACE VIEW db_stats AS
    SELECT 
        schemaname,
        tablename,
        attname,
        n_distinct,
        correlation,
        most_common_vals,
        most_common_freqs
    FROM pg_stats
    WHERE schemaname = 'public';
    
    GRANT SELECT ON db_stats TO easypay;
    GRANT SELECT ON db_stats TO readonly_user;
    
    -- Finalize setup
    ANALYZE;
    VACUUM ANALYZE;
    
    -- Log completion
    INSERT INTO audit_logs (action, details, created_at) 
    VALUES ('database_init', 'Production database initialization completed', CURRENT_TIMESTAMP);
    
EOSQL

echo "Database initialization completed successfully!"
echo "Database is ready for production use."
