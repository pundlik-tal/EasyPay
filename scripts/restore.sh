#!/bin/bash
# EasyPay Payment Gateway - Database Restore Script
# This script restores the production database from a backup

set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${POSTGRES_DB:-easypay}
DB_USER=${POSTGRES_USER:-easypay}
DB_PASSWORD=${POSTGRES_PASSWORD}

# S3 configuration (optional)
S3_BUCKET=${BACKUP_S3_BUCKET}
S3_ACCESS_KEY=${BACKUP_S3_ACCESS_KEY}
S3_SECRET_KEY=${BACKUP_S3_SECRET_KEY}
S3_REGION=${BACKUP_S3_REGION:-us-east-1}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -f, --force         Force restore without confirmation"
    echo "  -d, --dry-run       Show what would be restored without actually doing it"
    echo "  -s, --s3            Download backup from S3"
    echo "  -c, --create-db     Create database if it doesn't exist"
    echo ""
    echo "Examples:"
    echo "  $0 easypay_backup_20240101_120000.sql.gz"
    echo "  $0 --s3 easypay_backup_20240101_120000.sql.gz"
    echo "  $0 --dry-run easypay_backup_20240101_120000.sql.gz"
    exit 1
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
FROM_S3=false
CREATE_DB=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--s3)
            FROM_S3=true
            shift
            ;;
        -c|--create-db)
            CREATE_DB=true
            shift
            ;;
        -*)
            echo "Unknown option $1"
            usage
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    echo "Error: Backup file is required"
    usage
fi

echo "Starting database restore process..."
echo "Backup file: ${BACKUP_FILE}"
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"

# Set PGPASSWORD for non-interactive restore
export PGPASSWORD="${DB_PASSWORD}"

# Check if backup file exists locally or download from S3
if [ "$FROM_S3" = true ]; then
    echo "Downloading backup from S3..."
    
    # Install AWS CLI if not available
    if ! command -v aws &> /dev/null; then
        echo "Installing AWS CLI..."
        apk add --no-cache aws-cli
    fi
    
    # Configure AWS CLI
    aws configure set aws_access_key_id "${S3_ACCESS_KEY}"
    aws configure set aws_secret_access_key "${S3_SECRET_KEY}"
    aws configure set default.region "${S3_REGION}"
    
    # Download from S3
    aws s3 cp "s3://${S3_BUCKET}/database-backups/${BACKUP_FILE}" "${BACKUP_DIR}/"
    
    if [ $? -ne 0 ]; then
        echo "Failed to download backup from S3"
        exit 1
    fi
    
    echo "Backup downloaded successfully from S3"
fi

# Check if backup file exists
if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "Error: Backup file ${BACKUP_DIR}/${BACKUP_FILE} not found"
    exit 1
fi

# Check if it's a compressed file
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "Backup file is compressed, will decompress during restore"
    COMPRESSED=true
else
    COMPRESSED=false
fi

# Check database connection
echo "Testing database connection..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" -c "SELECT 1;" > /dev/null

if [ $? -ne 0 ]; then
    echo "Error: Cannot connect to database"
    exit 1
fi

echo "Database connection successful"

# Check if database exists
DB_EXISTS=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';")

if [ "$DB_EXISTS" != "1" ]; then
    if [ "$CREATE_DB" = true ]; then
        echo "Creating database ${DB_NAME}..."
        if [ "$DRY_RUN" = false ]; then
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" -c "CREATE DATABASE ${DB_NAME};"
        else
            echo "DRY RUN: Would create database ${DB_NAME}"
        fi
    else
        echo "Error: Database ${DB_NAME} does not exist. Use --create-db to create it."
        exit 1
    fi
fi

# Confirmation prompt (unless forced or dry run)
if [ "$FORCE" = false ] && [ "$DRY_RUN" = false ]; then
    echo ""
    echo "WARNING: This will completely replace the current database!"
    echo "Database: ${DB_NAME}"
    echo "Backup file: ${BACKUP_FILE}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
fi

# Create backup of current database before restore
if [ "$DRY_RUN" = false ]; then
    echo "Creating backup of current database..."
    CURRENT_BACKUP="easypay_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
    pg_dump \
        --host="${DB_HOST}" \
        --port="${DB_PORT}" \
        --username="${DB_USER}" \
        --dbname="${DB_NAME}" \
        --verbose \
        --no-password \
        --format=plain \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        --create \
        --file="${BACKUP_DIR}/${CURRENT_BACKUP}"
    
    if [ $? -eq 0 ]; then
        echo "Pre-restore backup created: ${CURRENT_BACKUP}"
    else
        echo "Warning: Failed to create pre-restore backup"
    fi
fi

# Perform restore
echo "Starting database restore..."

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: Would restore database from ${BACKUP_FILE}"
    echo "DRY RUN: Command would be:"
    if [ "$COMPRESSED" = true ]; then
        echo "gunzip -c ${BACKUP_DIR}/${BACKUP_FILE} | psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
    else
        echo "psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < ${BACKUP_DIR}/${BACKUP_FILE}"
    fi
else
    if [ "$COMPRESSED" = true ]; then
        echo "Restoring compressed backup..."
        gunzip -c "${BACKUP_DIR}/${BACKUP_FILE}" | psql \
            --host="${DB_HOST}" \
            --port="${DB_PORT}" \
            --username="${DB_USER}" \
            --dbname="${DB_NAME}" \
            --verbose \
            --no-password
    else
        echo "Restoring uncompressed backup..."
        psql \
            --host="${DB_HOST}" \
            --port="${DB_PORT}" \
            --username="${DB_USER}" \
            --dbname="${DB_NAME}" \
            --verbose \
            --no-password \
            --file="${BACKUP_DIR}/${BACKUP_FILE}"
    fi
    
    if [ $? -eq 0 ]; then
        echo "Database restore completed successfully!"
        
        # Verify restore
        echo "Verifying restore..."
        TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        echo "Tables restored: ${TABLE_COUNT}"
        
        # Update statistics
        echo "Updating database statistics..."
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "ANALYZE;"
        
        # Log restore completion
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "INSERT INTO audit_logs (action, details, created_at) VALUES ('database_restore', 'Database restored from ${BACKUP_FILE}', CURRENT_TIMESTAMP);" 2>/dev/null || echo "Could not log restore event (audit_logs table may not exist)"
        
    else
        echo "Database restore failed!"
        echo "You can restore from the pre-restore backup: ${CURRENT_BACKUP}"
        exit 1
    fi
fi

# Unset PGPASSWORD
unset PGPASSWORD

echo "Database restore process completed!"
