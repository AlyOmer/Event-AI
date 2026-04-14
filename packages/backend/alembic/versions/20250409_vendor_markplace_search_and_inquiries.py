"""
Vendor Marketplace: Search Indexes and Customer Inquiries

Revision ID: 20250409_vendor_marketplace
Revises: 8fb1c54dfed0
Create Date: 2026-04-09 16:00:00.000000+00:00

This migration adds:
- pg_trgm extension for trigram similarity search
- Full-text and trigram indexes on vendors table
- Customer inquiries table for vendor marketplace
- Unique constraint on vendor business name + location
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250409_vendor_marketplace'
down_revision: Union[str, None] = '8fb1c54dfed0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for trigram similarity search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("DROP TYPE IF EXISTS inquiry_status_enum CASCADE")
    
    # Create inquiry_status enum manually - removed because op.create_table creates it automatically!
    # inquiry_status_enum = postgresql.ENUM( ... )
    # inquiry_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create customer_inquiries table
    op.create_table(
        'customer_inquiries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_name', sa.String(255), nullable=False, index=True),
        sa.Column('customer_email', sa.String(255), nullable=False, index=True),
        sa.Column('customer_phone', sa.String(50), nullable=True),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('preferred_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=True),
        sa.Column('expected_guests', sa.Integer, nullable=True),
        sa.Column('budget_range', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('NEW', 'CONTACTED', 'QUOTED', 'CONVERTED', 'DECLINED', name='inquiry_status_enum'), nullable=False, server_default='NEW'),
        sa.Column('vendor_response', sa.Text, nullable=True),
        sa.Column('vendor_responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Add indexes on customer_inquiries
    op.create_index('ix_customer_inquiries_vendor_id_status', 'customer_inquiries', ['vendor_id', 'status'])
    op.create_index('ix_customer_inquiries_created_at', 'customer_inquiries', ['created_at'])
    
    # Add search indexes on vendors table
    # GIN index for trigram similarity on business_name
    op.execute("CREATE INDEX idx_vendors_name_trgm ON vendors USING gin (business_name gin_trgm_ops)")
    
    # GIN index for trigram similarity on description
    op.execute("CREATE INDEX idx_vendors_description_trgm ON vendors USING gin (description gin_trgm_ops)")
    
    # Functional index for full-text search on business_name
    op.execute("CREATE INDEX idx_vendors_name_fts ON vendors USING gin (to_tsvector('english', business_name))")
    
    # Functional index for full-text search on description
    op.execute("CREATE INDEX idx_vendors_description_fts ON vendors USING gin (to_tsvector('english', coalesce(description, '')))")
    
    # Composite unique index for vendor deduplication (business name + location, excluding rejected)
    op.create_index(
        'ix_vendors_business_name_location',
        'vendors',
        [sa.func.lower('business_name'), sa.func.lower('city'), sa.func.lower('region')],
        unique=True,
        postgresql_where=sa.text("status != 'REJECTED'")
    )
    
    # Add indexes on approval_requests for better query performance
    op.create_index('ix_approval_requests_status_submitted', 'approval_requests', ['status', 'submitted_date'])
    # op.create_index('ix_approval_requests_vendor_id', 'approval_requests', ['vendor_id'])
    
    # Add index on vendor_categories for faster lookups
    op.create_index('ix_vendor_categories_category_id', 'vendor_categories', ['category_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_vendor_categories_category_id', table_name='vendor_categories')
    # op.drop_index('ix_approval_requests_vendor_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_status_submitted', table_name='approval_requests')
    op.drop_index('ix_vendors_business_name_location', table_name='vendors')
    op.execute("DROP INDEX IF EXISTS idx_vendors_description_fts")
    op.execute("DROP INDEX IF EXISTS idx_vendors_name_fts")
    op.execute("DROP INDEX IF EXISTS idx_vendors_description_trgm")
    op.execute("DROP INDEX IF EXISTS idx_vendors_name_trgm")
    
    # Drop customer_inquiries table
    op.drop_index('ix_customer_inquiries_created_at', table_name='customer_inquiries')
    op.drop_index('ix_customer_inquiries_vendor_id_status', table_name='customer_inquiries')
    op.drop_table('customer_inquiries')
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS inquiry_status_enum")
    
    # Note: We don't drop pg_trgm extension as it might be used by other features
