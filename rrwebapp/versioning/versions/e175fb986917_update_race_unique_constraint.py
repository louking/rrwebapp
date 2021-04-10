"""update race unique constraint

Revision ID: e175fb986917
Revises: 7578b01555e0
Create Date: 2016-10-26 11:52:25.789000

"""

# revision identifiers, used by Alembic.
revision = 'e175fb986917'
down_revision = '7578b01555e0'

from alembic import op
import sqlalchemy as sa

#added
from sqlalchemy.sql import table, column

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('race', sa.Column('fixeddist', sa.String(length=10), nullable=True))
    op.drop_index('name', table_name='race')
    op.create_unique_constraint(None, 'race', ['name', 'year', 'club_id', 'fixeddist'])
    ### end Alembic commands ###

    # update 
    race = table('race',
               column('id', sa.Integer),
               column('distance', sa.Float),
               column('fixeddist', sa.String),
              )

    # row specific values
    # we build a quick link for the current connection of alembic
    # adapted from https://julo.ch/blog/migrating-content-with-alembic
    connection = op.get_bind()
    for thisrace in connection.execute(race.select()):

        connection.execute(
            race.update().where(
                race.c.id == thisrace.id
            ).values(
                fixeddist='{:.4g}'.format(thisrace.distance),
            )
        )

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'race', type_='unique')
    op.create_index('name', 'race', ['name', 'year', 'club_id'], unique=True)
    op.drop_column('race', 'fixeddist')
    ### end Alembic commands ###
