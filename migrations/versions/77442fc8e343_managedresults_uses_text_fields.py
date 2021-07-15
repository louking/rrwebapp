"""ManagedResults uses Text fields

Revision ID: 77442fc8e343
Revises: bd228893783a
Create Date: 2021-07-14 06:41:04.343278

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '77442fc8e343'
down_revision = 'bd228893783a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('managedresult', 'city',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'club',
               existing_type=mysql.VARCHAR(length=20),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'fname',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'hometown',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'lname',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'name',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('managedresult', 'state',
               existing_type=mysql.VARCHAR(length=2),
               type_=sa.Text(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('managedresult', 'state',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=2),
               existing_nullable=True)
    op.alter_column('managedresult', 'name',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('managedresult', 'lname',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('managedresult', 'hometown',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('managedresult', 'fname',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('managedresult', 'club',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=20),
               existing_nullable=True)
    op.alter_column('managedresult', 'city',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    # ### end Alembic commands ###
