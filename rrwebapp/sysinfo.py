###########################################################################################
# result - result views for result results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/30/14        Lou King        Create
#
#   Copyright 2014 Lou King
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
from flask_login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import app
from .accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from .model import db   # this is ok because this module only runs under flask
from .apicommon import failure_response, success_response

# module specific needs
from . import version

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
            configkeys = sorted(list(app.config.keys()))
            appconfig = []
            for key in configkeys:
                value = app.config[key]
                if not owner_permission.can():
                    if key in ['SQLALCHEMY_DATABASE_URI','SECRET_KEY']:
                        value = '<obscured>'
                appconfig.append({'label':key, 'value':value})
            sysvars.append(['app.config',appconfig])
            
            # collect flask.session variables
            sessionkeys = list(flask.session.keys())
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

