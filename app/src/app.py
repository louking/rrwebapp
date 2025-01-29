'''
app.py is only used to support flask commands

app_server.py for webserver execution
    must match with app.py except for under "flask command processing"
'''
# standard
import os.path

# pypi
from flask_migrate import Migrate

# homegrown
from rrwebapp import create_app
from rrwebapp.settings import Production, get_configfiles
from rrwebapp.model import db

configfiles = get_configfiles()

# init_for_operation=False because when we create app this would use database and cause
# sqlalchemy.exc.OperationalError if one of the updating tables needs migration
app = create_app(Production(configfiles), configfiles, init_for_operation=False)

# set up flask command processing (not needed within app_server.py)
migrate = Migrate(app, db, compare_type=True)


