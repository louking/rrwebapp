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
from flask import current_app
from flask_login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import bp
from ...accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from ...model import db   # this is ok because this module only runs under flask
from ...apicommon import failure_response, success_response

# module specific needs
from ... import version

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
bp.add_url_rule('/sysinfo',view_func=ViewSysinfo.as_view('sysinfo'),methods=['GET'])
#----------------------------------------------------------------------


