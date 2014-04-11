###########################################################################################
# result - result views for result results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/30/14        Lou King        Create
#
#   Copyright 2014 Lou King
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

# standard
import json
import csv
import os.path
import time
import tempfile
import os
from datetime import timedelta
import traceback

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
import version

class testException(Exception): pass

#######################################################################
class ViewSysinfo(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            thisversion = version.__version__
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('sysinfo.html',pagename='About',version=thisversion,
                                         inhibityear=True,inhibitclub=True,addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/sysinfo',view_func=ViewSysinfo.as_view('sysinfo'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ViewDebug(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            thisversion = version.__version__
            appconfigpath = getattr(app,'configpath','<not set>')
            appconfigtime = getattr(app,'configtime','<not set>')

            # collect groups of system variables                        
            sysvars = []
            
            # collect app.config variables
            configkeys = app.config.keys()
            configkeys.sort()
            appconfig = []
            for key in configkeys:
                value = app.config[key]
                if not owner_permission.can():
                    if key in ['SQLALCHEMY_DATABASE_URI','SECRET_KEY']:
                        value = '<obscured>'
                appconfig.append({'label':key, 'value':value})
            sysvars.append(['app.config',appconfig])
            
            # collect flask.session variables
            sessionkeys = flask.session.keys()
            sessionkeys.sort()
            sessionconfig = []
            for key in sessionkeys:
                value = flask.session[key]
                sessionconfig.append({'label':key, 'value':value})
            sysvars.append(['flask.session',sessionconfig])
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('sysinfo.html',pagename='Debug',
                                         version=thisversion,
                                         configpath=appconfigpath,
                                         configtime=appconfigtime,
                                         sysvars=sysvars,
                                         owner=owner_permission.can(),
                                         inhibityear=True,inhibitclub=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_debuginfo',view_func=ViewDebug.as_view('debug'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class TestException(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            raise testException
                    
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/xcauseexception',view_func=TestException.as_view('testexception'),methods=['GET'])
#----------------------------------------------------------------------

