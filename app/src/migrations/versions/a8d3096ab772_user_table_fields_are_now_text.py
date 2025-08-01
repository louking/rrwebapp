"""user table fields are now Text

Revision ID: a8d3096ab772
Revises: 3969878bfb17
Create Date: 2025-07-21 15:40:07.497318

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a8d3096ab772'
down_revision = '3969878bfb17'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'name',
               existing_type=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=120),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('user', 'pw_hash',
               existing_type=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=128),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('user', 'password',
               existing_type=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=255),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('user', 'last_login_ip',
               existing_type=mysql.VARCHAR(length=39),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('user', 'current_login_ip',
               existing_type=mysql.VARCHAR(length=39),
               type_=sa.Text(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'current_login_ip',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=39),
               existing_nullable=True)
    op.alter_column('user', 'last_login_ip',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=39),
               existing_nullable=True)
    op.alter_column('user', 'password',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=255),
               existing_nullable=True)
    op.alter_column('user', 'pw_hash',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=128),
               existing_nullable=True)
    op.alter_column('user', 'name',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(charset='utf8mb3', collation='utf8mb3_general_ci', length=120),
               existing_nullable=True)
    # ### end Alembic commands ###
