"""apicredentials add api_reg_token, api_reg_secret

Revision ID: f3c9b1a7d2e4
Revises: a8d3096ab772
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3c9b1a7d2e4'
down_revision = 'a8d3096ab772'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('apicredentials', sa.Column('api_reg_token', sa.String(length=1024), nullable=True))
    op.add_column('apicredentials', sa.Column('api_reg_secret', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('apicredentials', 'api_reg_secret')
    op.drop_column('apicredentials', 'api_reg_token')
