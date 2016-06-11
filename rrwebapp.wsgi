###########################################################################################
# raceresultswebapp.runserver - run the web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       06/04/16        Lou King        Create
#
#   Copyright 2016 Lou King
#
###########################################################################################

import os, sys

# get configuration
config = SafeConfigParser()
thisdir = os.path.dirname(__file__)
parentdir = '/'.join(thisdir.split('/')[:-1])
config.readfp(open(os.path.join(parentdir, 'rrwebapp.cfg')))
PROJECT_DIR = config.get('project', 'PROJECT_DIR')
#PROJECT_DIR = '/var/www/beta.scoretility.com/rrwebapp/rrwebapp'

activate_this = os.path.join(PROJECT_DIR, 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))
sys.path.append(PROJECT_DIR)

# see http://flask.pocoo.org/docs/0.11/deploying/mod_wsgi/
from rrwebapp import app as application