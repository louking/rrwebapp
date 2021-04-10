"""fix disposition fields, rename to initialdisposition

Revision ID: 3b423d1e443d
Revises: f40369e94ad
Create Date: 2014-03-08 16:40:56.586000

"""

# revision identifiers, used by Alembic.
revision = '3b423d1e443d'
down_revision = 'f40369e94ad'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managedresult', sa.Column('initialdisposition', sa.Enum('definite', 'similar', 'missed', 'excluded', '', name='disposition_type'), nullable=True))
    op.drop_column('managedresult', 'selectionmethod')
    op.drop_column('managedresult', 'disposition')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managedresult', sa.Column('disposition', mysql.ENUM('exact', 'close', 'missed', 'excluded'), nullable=True))
    op.add_column('managedresult', sa.Column('selectionmethod', mysql.ENUM('auto', 'user'), nullable=True))
    op.drop_column('managedresult', 'initialdisposition')
    ### end Alembic commands ###
