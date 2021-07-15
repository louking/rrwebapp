"""support proportional scoring; better nonmember administration

Revision ID: ee692403f211
Revises: ee330649908f
Create Date: 2021-06-21 16:28:19.178815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee692403f211'
down_revision = 'ee330649908f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('runner', sa.Column('estdateofbirth', sa.Boolean(), nullable=True))
    op.add_column('series', sa.Column('options', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('series', 'options')
    op.drop_column('runner', 'estdateofbirth')
    # ### end Alembic commands ###