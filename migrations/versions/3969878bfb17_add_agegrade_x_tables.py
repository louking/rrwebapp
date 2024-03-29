"""add agegrade_x tables

Revision ID: 3969878bfb17
Revises: cb7ec4f78d48
Create Date: 2023-01-05 06:48:22.545208

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3969878bfb17'
down_revision = 'cb7ec4f78d48'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('agegrade_table',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('last_update', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('agegrade_category',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('factortable_id', sa.Integer(), nullable=True),
    sa.Column('gender', sa.Enum('M', 'F', 'X'), nullable=True),
    sa.Column('surface', sa.Enum('road', 'track'), nullable=True),
    sa.Column('dist_mm', sa.Integer(), nullable=True),
    sa.Column('oc_secs', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['factortable_id'], ['agegrade_table.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('factortable_id', 'gender', 'surface', 'dist_mm')
    )
    op.create_table('agegrade_factor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('factor', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['category_id'], ['agegrade_category.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('club', sa.Column('agegradetable_id', sa.Integer(), nullable=True))
    op.create_foreign_key('club_ibfk_1', 'club', 'agegrade_table', ['agegradetable_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('club_ibfk_1', 'club', type_='foreignkey')
    op.drop_column('club', 'agegradetable_id')
    op.drop_table('agegrade_factor')
    op.drop_table('agegrade_category')
    op.drop_table('agegrade_table')
    # ### end Alembic commands ###
