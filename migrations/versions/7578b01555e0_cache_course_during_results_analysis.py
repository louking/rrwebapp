"""cache course during results analysis

Revision ID: 7578b01555e0
Revises: c471bfff1a49
Create Date: 2016-10-19 14:00:10.207000

"""

# revision identifiers, used by Alembic.
revision = '7578b01555e0'
down_revision = 'c471bfff1a49'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('course',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=True),
    sa.Column('sourceid', sa.String(length=128), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('date', sa.String(length=10), nullable=True),
    sa.Column('distmiles', sa.Float(), nullable=True),
    sa.Column('distkm', sa.Float(), nullable=True),
    sa.Column('surface', sa.Enum('road', 'track', 'trail', name='SurfaceType'), nullable=True),
    sa.Column('location', sa.String(length=64), nullable=True),
    sa.Column('raceid', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'sourceid')
    )
    op.add_column('raceresult', sa.Column('sourceresultid', sa.String(length=128), nullable=True))
    op.add_column('raceresultservice', sa.Column('attrs', sa.String(length=200), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('raceresultservice', 'attrs')
    op.drop_column('raceresult', 'sourceresultid')
    op.drop_table('course')
    ### end Alembic commands ###
