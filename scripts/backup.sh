#!/bin/bash
# EasyPay Payment Gateway - Database Backup Script
# This script creates automated backups of the production database

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="easypay_backup_${DATE}.sql"
BACKUP_FILE_COMPRESSED="easypay_backup_${DATE}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Database configuration
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

echo "Starting database backup process..."
echo "Backup file: ${BACKUP_FILE}"
echo "Backup directory: ${BACKUP_DIR}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Set PGPASSWORD for non-interactive backup
export PGPASSWORD="${DB_PASSWORD}"

# Create database backup
echo "Creating database backup..."
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
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Database backup completed successfully"
    
    # Compress the backup
    echo "Compressing backup file..."
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    
    if [ $? -eq 0 ]; then
        echo "Backup compressed successfully: ${BACKUP_FILE_COMPRESSED}"
        
        # Upload to S3 if configured
        if [ -n "${S3_BUCKET}" ] && [ -n "${S3_ACCESS_KEY}" ] && [ -n "${S3_SECRET_KEY}" ]; then
            echo "Uploading backup to S3..."
            
            # Install AWS CLI if not available
            if ! command -v aws &> /dev/null; then
                echo "Installing AWS CLI..."
                apk add --no-cache aws-cli
            fi
            
            # Configure AWS CLI
            aws configure set aws_access_key_id "${S3_ACCESS_KEY}"
            aws configure set aws_secret_access_key "${S3_SECRET_KEY}"
            aws configure set default.region "${S3_REGION}"
            
            # Upload to S3
            aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE_COMPRESSED}" "s3://${S3_BUCKET}/database-backups/"
            
            if [ $? -eq 0 ]; then
                echo "Backup uploaded to S3 successfully"
                
                # Remove local backup after successful S3 upload
                rm "${BACKUP_DIR}/${BACKUP_FILE_COMPRESSED}"
                echo "Local backup file removed after successful S3 upload"
            else
                echo "Failed to upload backup to S3"
            fi
        fi
        
        # Clean up old backups
        echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
        find "${BACKUP_DIR}" -name "easypay_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
        
        # Log backup completion
        echo "Backup process completed successfully at $(date)"
        
        # Create backup metadata file
        cat > "${BACKUP_DIR}/backup_metadata_${DATE}.json" << EOF
{
    "backup_file": "${BACKUP_FILE_COMPRESSED}",
    "backup_date": "$(date -Iseconds)",
    "database_name": "${DB_NAME}",
    "database_host": "${DB_HOST}",
    "backup_size": "$(stat -c%s "${BACKUP_DIR}/${BACKUP_FILE_COMPRESSED}" 2>/dev/null || echo "unknown")",
    "retention_days": "${RETENTION_DAYS}",
    "s3_uploaded": "$([ -n "${S3_BUCKET}" ] && echo "true" || echo "false")"
}
EOF
        
    else
        echo "Failed to compress backup file"
        exit 1
    fi
else
    echo "Database backup failed"
    exit 1
fi

# Unset PGPASSWORD
unset PGPASSWORD

echo "Backup process completed successfully!"
