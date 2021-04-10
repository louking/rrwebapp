###########################################################################################
# racedb  -- manage race database
#
#	Date		Author		Reason
#	----		------		------
#       05/08/13        Lou King        Create
#       01/11/14        Lou King        support Flask database
#                                       see http://michaelmartinez.in/basic-alembic-migrations-with-flask.html
#
#   Copyright 2013,2014 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###########################################################################################


from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# make sure this package is available
import os, sys
sys.path.append(os.getcwd())

# get the app model
# from rrwebapp import app

from rrwebapp import racedb   # needs to be before database_flask imported
from rrwebapp.database_flask import db, db_uri

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Overwrite the sqlalchemy.url in the alembic.ini file.
# config.set_main_option('sqlalchemy.url', app.config['SQLALCHEMY_DATABASE_URI'])
# configpath = os.path.join(os.path.sep.join(os.getcwd().split(os.path.sep)[:-2]), 'rrwebapp.cfg')
# print 'os.getcwd()="{}", configpath="{}"'.format(os.getcwd(),configpath)
# appconfig = getitems(configpath, 'app')
config.set_main_option('sqlalchemy.url', db_uri)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata
#target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, 
        compare_type=True,
        )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # compare_type=True needed to change type of column, e.g., String(50) -> String(100)
                # see http://stackoverflow.com/questions/17174636/can-alembic-autogenerate-column-alterations
                compare_type=True,  
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

