'''
app.py is only used to support flask commands

develop execution from run.py; production execution from rrwebapp.wsgi
'''
# standard
import os.path

# pypi
from flask_migrate import Migrate
from sqlalchemy.orm import scoped_session, sessionmaker

# homegrown
from rrwebapp import create_app
from rrwebapp.settings import Production
from rrwebapp.model import db
from rrwebapp.applogging import setlogging

abspath = os.path.abspath(__file__)
configpath = os.path.join('config', 'rrwebapp.cfg')
# userconfigpath = os.path.join('config', 'users.cfg')
# userconfigpath first so configpath can override
configfiles = [configpath]

# init_for_operation=False because when we create app this would use database and cause
# sqlalchemy.exc.OperationalError if one of the updating tables needs migration
app = create_app(Production(configfiles), configfiles, init_for_operation=False)

# set up scoped session
with app.app_context():
# this causes SQLALCHEMY_BINDS not to work ('user' bind missing)
#     db.session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=db.engine))
#     db.query = db.session.query_property()

    # turn on logging
    setlogging()

migrate = Migrate(app, db, compare_type=True)


