"""Add authentication tables

Revision ID: 003_add_auth_tables
Revises: 002_add_audit_logs
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_auth_tables'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add authentication tables."""
    
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_id', sa.String(length=50), nullable=False),
        sa.Column('key_secret_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False),
        sa.Column('rate_limit_per_day', sa.Integer(), nullable=False),
        sa.Column('ip_whitelist', sa.JSON(), nullable=True),
        sa.Column('ip_blacklist', sa.JSON(), nullable=True),
        sa.Column('user_agent_patterns', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_id')
    )
    
    # Create indexes for api_keys table
    op.create_index('idx_api_keys_key_id', 'api_keys', ['key_id'])
    op.create_index('idx_api_keys_status', 'api_keys', ['status'])
    op.create_index('idx_api_keys_created_at', 'api_keys', ['created_at'])
    op.create_index('idx_api_keys_expires_at', 'api_keys', ['expires_at'])
    
    # Create auth_tokens table
    op.create_table('auth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_id', sa.String(length=50), nullable=False),
        sa.Column('token_type', sa.String(length=50), nullable=False),
        sa.Column('jti', sa.String(length=255), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('audience', sa.String(length=255), nullable=True),
        sa.Column('issuer', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
        sa.UniqueConstraint('token_id')
    )
    
    # Create indexes for auth_tokens table
    op.create_index('idx_auth_tokens_token_id', 'auth_tokens', ['token_id'])
    op.create_index('idx_auth_tokens_jti', 'auth_tokens', ['jti'])
    op.create_index('idx_auth_tokens_api_key_id', 'auth_tokens', ['api_key_id'])
    op.create_index('idx_auth_tokens_expires_at', 'auth_tokens', ['expires_at'])
    op.create_index('idx_auth_tokens_subject', 'auth_tokens', ['subject'])
    
    # Create users table (for future user management)
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create indexes for users table
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    
    # Add foreign key constraint to audit_logs table for api_key_id
    op.add_column('audit_logs', sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_audit_logs_api_key_id', 'audit_logs', 'api_keys', ['api_key_id'], ['id'])


def downgrade() -> None:
    """Remove authentication tables."""
    
    # Remove foreign key constraint from audit_logs table
    op.drop_constraint('fk_audit_logs_api_key_id', 'audit_logs', type_='foreignkey')
    op.drop_column('audit_logs', 'api_key_id')
    
    # Drop users table
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_username', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop auth_tokens table
    op.drop_index('idx_auth_tokens_subject', table_name='auth_tokens')
    op.drop_index('idx_auth_tokens_expires_at', table_name='auth_tokens')
    op.drop_index('idx_auth_tokens_api_key_id', table_name='auth_tokens')
    op.drop_index('idx_auth_tokens_jti', table_name='auth_tokens')
    op.drop_index('idx_auth_tokens_token_id', table_name='auth_tokens')
    op.drop_table('auth_tokens')
    
    # Drop api_keys table
    op.drop_index('idx_api_keys_expires_at', table_name='api_keys')
    op.drop_index('idx_api_keys_created_at', table_name='api_keys')
    op.drop_index('idx_api_keys_status', table_name='api_keys')
    op.drop_index('idx_api_keys_key_id', table_name='api_keys')
    op.drop_table('api_keys')
