###########################################################################################
# raceresultswebapp.runserver - run the web application for windows debug
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/03/13        Lou King        Create
#
#   Copyright 2013 Lou King
#
###########################################################################################

'''
use this script to run the Race Results web application

Usage::

    python runserver.py
'''

# standard
import pdb
import os
import os.path

from rrwebapp import app

app.run(debug=True)