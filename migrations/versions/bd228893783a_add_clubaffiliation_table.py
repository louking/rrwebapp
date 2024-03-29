"""add clubaffiliation table

Revision ID: bd228893783a
Revises: ee692403f211
Create Date: 2021-07-08 12:28:36.119347

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd228893783a'
down_revision = 'ee692403f211'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('clubaffiliation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('club_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('shortname', sa.Text(), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('alternates', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['club_id'], ['club.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('raceresult', sa.Column('clubaffiliation_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'raceresult', 'clubaffiliation', ['clubaffiliation_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'raceresult', type_='foreignkey')
    op.drop_column('raceresult', 'clubaffiliation_id')
    op.drop_table('clubaffiliation')
    # ### end Alembic commands ###
