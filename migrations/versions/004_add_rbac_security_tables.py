"""Add RBAC and Security Tables

Revision ID: 004_add_rbac_security_tables
Revises: 003_add_authentication_tables
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_rbac_security_tables'
down_revision = '003_add_authentication_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add RBAC and security tables."""
    
    # Create roles table
    op.create_table('roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_system_role', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('resource_pattern', sa.String(length=255), nullable=True),
        sa.Column('is_system_permission', sa.Boolean(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create role_permissions association table
    op.create_table('role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    
    # Create user_roles association table
    op.create_table('user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Create resource_access table
    op.create_table('resource_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('allowed_actions', sa.JSON(), nullable=False),
        sa.Column('denied_actions', sa.JSON(), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource_type', 'resource_id', 'api_key_id', name='unique_resource_api_key_access')
    )
    
    # Create security_events table
    op.create_table('security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('action_attempted', sa.String(length=50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create api_key_scopes table
    op.create_table('api_key_scopes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope_type', sa.String(length=50), nullable=False),
        sa.Column('scope_value', sa.String(length=500), nullable=False),
        sa.Column('scope_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add role_id column to api_keys table
    op.add_column('api_keys', sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_api_keys_role_id', 'api_keys', 'roles', ['role_id'], ['id'])
    
    # Create indexes for performance
    op.create_index('idx_roles_name', 'roles', ['name'])
    op.create_index('idx_roles_status', 'roles', ['status'])
    op.create_index('idx_roles_priority', 'roles', ['priority'])
    op.create_index('idx_roles_created_at', 'roles', ['created_at'])
    
    op.create_index('idx_permissions_name', 'permissions', ['name'])
    op.create_index('idx_permissions_resource_type', 'permissions', ['resource_type'])
    op.create_index('idx_permissions_action_type', 'permissions', ['action_type'])
    op.create_index('idx_permissions_category', 'permissions', ['category'])
    op.create_index('idx_permissions_created_at', 'permissions', ['created_at'])
    
    op.create_index('idx_resource_access_resource', 'resource_access', ['resource_type', 'resource_id'])
    op.create_index('idx_resource_access_api_key', 'resource_access', ['api_key_id'])
    op.create_index('idx_resource_access_role', 'resource_access', ['role_id'])
    op.create_index('idx_resource_access_active', 'resource_access', ['is_active'])
    op.create_index('idx_resource_access_expires', 'resource_access', ['expires_at'])
    
    op.create_index('idx_security_events_type', 'security_events', ['event_type'])
    op.create_index('idx_security_events_category', 'security_events', ['event_category'])
    op.create_index('idx_security_events_severity', 'security_events', ['severity'])
    op.create_index('idx_security_events_api_key', 'security_events', ['api_key_id'])
    op.create_index('idx_security_events_user', 'security_events', ['user_id'])
    op.create_index('idx_security_events_ip', 'security_events', ['ip_address'])
    op.create_index('idx_security_events_resource', 'security_events', ['resource_type', 'resource_id'])
    op.create_index('idx_security_events_success', 'security_events', ['success'])
    op.create_index('idx_security_events_occurred', 'security_events', ['occurred_at'])
    
    op.create_index('idx_api_key_scopes_api_key', 'api_key_scopes', ['api_key_id'])
    op.create_index('idx_api_key_scopes_type', 'api_key_scopes', ['scope_type'])
    op.create_index('idx_api_key_scopes_active', 'api_key_scopes', ['is_active'])
    op.create_index('idx_api_key_scopes_created', 'api_key_scopes', ['created_at'])
    
    op.create_index('idx_api_keys_role_id', 'api_keys', ['role_id'])


def downgrade():
    """Remove RBAC and security tables."""
    
    # Drop indexes
    op.drop_index('idx_api_keys_role_id', 'api_keys')
    op.drop_index('idx_api_key_scopes_created', 'api_key_scopes')
    op.drop_index('idx_api_key_scopes_active', 'api_key_scopes')
    op.drop_index('idx_api_key_scopes_type', 'api_key_scopes')
    op.drop_index('idx_api_key_scopes_api_key', 'api_key_scopes')
    
    op.drop_index('idx_security_events_occurred', 'security_events')
    op.drop_index('idx_security_events_success', 'security_events')
    op.drop_index('idx_security_events_resource', 'security_events')
    op.drop_index('idx_security_events_ip', 'security_events')
    op.drop_index('idx_security_events_user', 'security_events')
    op.drop_index('idx_security_events_api_key', 'security_events')
    op.drop_index('idx_security_events_severity', 'security_events')
    op.drop_index('idx_security_events_category', 'security_events')
    op.drop_index('idx_security_events_type', 'security_events')
    
    op.drop_index('idx_resource_access_expires', 'resource_access')
    op.drop_index('idx_resource_access_active', 'resource_access')
    op.drop_index('idx_resource_access_role', 'resource_access')
    op.drop_index('idx_resource_access_api_key', 'resource_access')
    op.drop_index('idx_resource_access_resource', 'resource_access')
    
    op.drop_index('idx_permissions_created_at', 'permissions')
    op.drop_index('idx_permissions_category', 'permissions')
    op.drop_index('idx_permissions_action_type', 'permissions')
    op.drop_index('idx_permissions_resource_type', 'permissions')
    op.drop_index('idx_permissions_name', 'permissions')
    
    op.drop_index('idx_roles_created_at', 'roles')
    op.drop_index('idx_roles_priority', 'roles')
    op.drop_index('idx_roles_status', 'roles')
    op.drop_index('idx_roles_name', 'roles')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_api_keys_role_id', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'role_id')
    
    # Drop tables
    op.drop_table('api_key_scopes')
    op.drop_table('security_events')
    op.drop_table('resource_access')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
