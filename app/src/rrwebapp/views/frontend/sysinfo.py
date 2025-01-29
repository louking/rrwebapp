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
import os

# pypi
from flask import render_template, current_app, session
from flask.views import MethodView
from flask_security import roles_accepted
from loutilities.flask_helpers.blueprints import add_url_rules
from loutilities.user.roles import ROLE_SUPER_ADMIN

# home grown
from . import bp
from ...model import db   # this is ok because this module only runs under flask

# module specific needs
from ...version import __version__
from ...version import __docversion__

adminguide = f'https://docs.scoretility.com/en/{__docversion__}/admin-guide.html'
thisversion = __version__

class testException(Exception): pass

class ViewSysinfo(MethodView):
    # decorators = [lambda f: roles_accepted(ROLE_SUPER_ADMIN, 'event-admin')(f)]
    url_rules = {
                'sysinfo': ['/sysinfo',('GET',)],
                }

    def get(self):
        try:
            
            # commit database updates and close transaction
            db.session.commit()
            return render_template('sysinfo.html',pagename='About',version=thisversion,
                                    inhibityear=True,inhibitclub=True,addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
add_url_rules(bp, ViewSysinfo)

