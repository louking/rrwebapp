"""add managedresult table

Revision ID: 4b05b4289d07
Revises: 127a55972386
Create Date: 2014-03-01 19:44:49.705000

"""

# revision identifiers, used by Alembic.
revision = '4b05b4289d07'
down_revision = '127a55972386'

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import table, column
from loutilities.namesplitter import split_full_name

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('managedresult',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('club_id', sa.Integer(), nullable=True),
    sa.Column('raceid', sa.Integer(), nullable=True),
    sa.Column('place', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('fname', sa.String(length=50), nullable=True),
    sa.Column('lname', sa.String(length=50), nullable=True),
    sa.Column('gender', sa.String(length=1), nullable=True),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('city', sa.String(length=50), nullable=True),
    sa.Column('state', sa.String(length=2), nullable=True),
    sa.Column('hometown', sa.String(length=50), nullable=True),
    sa.Column('club', sa.String(length=20), nullable=True),
    sa.Column('chiptime', sa.Float(), nullable=True),
    sa.Column('guntime', sa.Float(), nullable=True),
    sa.Column('runnerid', sa.Integer(), nullable=True),
    sa.Column('disposition', sa.Enum('exact', 'close', 'missed', 'excluded', name='disposition_type'), nullable=True),
    sa.Column('selectionmethod', sa.Enum('auto', 'user', name='selectionmethod_type'), nullable=True),
    sa.ForeignKeyConstraint(['club_id'], ['club.id'], ),
    sa.ForeignKeyConstraint(['raceid'], ['race.id'], ),
    sa.ForeignKeyConstraint(['runnerid'], ['runner.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('runner', sa.Column('expdate', sa.String(length=10), nullable=True))
    op.add_column('runner', sa.Column('fname', sa.String(length=50), nullable=True))
    op.add_column('runner', sa.Column('lname', sa.String(length=50), nullable=True))
    ### end Alembic commands ###

    # note we also need the id to identify rows
    runner = table('runner',
                   column('id', sa.Integer),
                   column('expdate', sa.String),
                   column('name', sa.String),
                   column('fname', sa.String),
                   column('lname', sa.String),
                  )

    # set initial value for expdate
    op.execute(runner.update().values({'expdate':op.inline_literal('')}))
    
    # set initial value for fname, lname
    
    # we build a quick link for the current connection of alembic
    # adapted from https://julo.ch/blog/migrating-content-with-alembic
    connection = op.get_bind()
    #runner.create(connection)
    for thisrunner in connection.execute(runner.select()):
        names = split_full_name(thisrunner.name)
        fname = ' '.join([names['fname'],names['initials']]).strip()
        lname = names['lname']
        if names['suffix']:
            lname += ' '+names['suffix']
        lname = lname.strip()

        connection.execute(
            runner.update().where(
                runner.c.id == thisrunner.id
            ).values(
                fname=fname,
                lname=lname
            )
        )
    #runner.drop(connection)
    
def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('runner', 'lname')
    op.drop_column('runner', 'fname')
    op.drop_column('runner', 'expdate')
    op.drop_table('managedresult')
    ### end Alembic commands ###
