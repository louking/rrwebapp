"""add member column to runner table

Revision ID: 4b5ad1ebeb97
Revises: None
Create Date: 2013-05-18 12:55:01.001000

"""

# revision identifiers, used by Alembic.
revision = '4b5ad1ebeb97'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('runner', sa.Column('member', sa.Boolean(), nullable=True))
    ### end Alembic commands ###
    
    # on upgrade, all runners are members
    runner = table('runner',
                   column('member',sa.Boolean())
                   )
    op.execute(runner.update().values({'member':op.inline_literal(True)}))


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('runner', 'member')
    ### end Alembic commands ###
