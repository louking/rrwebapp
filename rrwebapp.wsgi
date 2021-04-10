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
from configparser import SafeConfigParser

# get configuration
config = SafeConfigParser()
thisdir = os.path.dirname(__file__)
parentdir = '/'.join(thisdir.split('/')[:-1])
config.readfp(open(os.path.join(parentdir, 'rrwebapp.cfg')))
PROJECT_DIR = config.get('project', 'PROJECT_DIR')

activate_this = os.path.join(PROJECT_DIR, 'bin', 'activate_this.py')
exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))
sys.path.append(PROJECT_DIR)

from rrwebapp import app as application
