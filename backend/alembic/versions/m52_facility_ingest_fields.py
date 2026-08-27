"""add facility ingest fields

Revision ID: 123abc456def
Revises: 075ce8068be5
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '123abc456def'
down_revision: Union[str, None] = '075ce8068be5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to healthcare_facilities
    op.add_column('healthcare_facilities', sa.Column('source_record_id', sa.String(), nullable=True))
    op.add_column('healthcare_facilities', sa.Column('source_type', sa.String(), nullable=True))
    op.add_column('healthcare_facilities', sa.Column('verification_status', sa.String(), server_default='UNVERIFIED', nullable=True))
    op.create_index(op.f('ix_healthcare_facilities_source_record_id'), 'healthcare_facilities', ['source_record_id'], unique=False)
    op.create_index(op.f('ix_healthcare_facilities_verification_status'), 'healthcare_facilities', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_healthcare_facilities_verification_status'), table_name='healthcare_facilities')
    op.drop_index(op.f('ix_healthcare_facilities_source_record_id'), table_name='healthcare_facilities')
    op.drop_column('healthcare_facilities', 'verification_status')
    op.drop_column('healthcare_facilities', 'source_type')
    op.drop_column('healthcare_facilities', 'source_record_id')

