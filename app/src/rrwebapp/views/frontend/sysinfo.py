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

class ViewDebug(MethodView):
    decorators = [lambda f: roles_accepted(ROLE_SUPER_ADMIN)(f)]
    url_rules = {
                'debug': ['/_debuginfo',('GET',)],
                }

    def get(self):
        try:
            appconfigpath = getattr(current_app,'configpath','<not set>')
            appconfigtime = getattr(current_app,'configtime','<not set>')

            # collect groups of system variables                        
            sysvars = []
            
            # collect current_app.config variables
            configkeys = list(current_app.config.keys())
            configkeys.sort()
            appconfig = []
            for key in configkeys:
                value = current_app.config[key]
                if True:    # maybe check for something else later
                    if key in ['SQLALCHEMY_DATABASE_URI', 'SQLALCHEMY_BINDS',
                               'SECRET_KEY',
                               'SECURITY_PASSWORD_SALT',
                               'GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET',
                               'GMAPS_API_KEY', 'GMAPS_ELEV_API_KEY',
                               'APP_OWNER_PW',
                               'RSU_KEY', 'RSU_SECRET',
                               'MC_KEY',
                               'MAIL_PASSWORD',
                               ]:
                        value = '[obscured]'
                appconfig.append({'label':key, 'value':value})
            sysvars.append(['current_app.config',appconfig])
            
            # collect flask.session variables
            sessionkeys = list(session.keys())
            sessionkeys.sort()
            sessionconfig = []
            for key in sessionkeys:
                value = session[key]
                sessionconfig.append({'label':key, 'value':value})
            sysvars.append(['flask.session',sessionconfig])
            
            # commit database updates and close transaction
            db.session.commit()
            return render_template('sysinfo.jinja2',pagename='Debug',
                version=thisversion,
                adminguide=adminguide,
                configpath=appconfigpath,
                configtime=appconfigtime,
                                         sysvars=sysvars)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
add_url_rules(bp, ViewDebug)

class TestException(MethodView):
    decorators = [lambda f: roles_accepted(ROLE_SUPER_ADMIN)(f)]
    url_rules = {
                'testexception': ['/xcauseexception',('GET',)],
                }
    
    def get(self):
        try:
            raise testException
                    
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
add_url_rules(bp, TestException)

