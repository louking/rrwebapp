# standard

# pypi
import flask
from flask import current_app, abort
from flask.views import MethodView

# home grown
from . import bp
from ...accesscontrol import owner_permission
from ...model import db   # this is ok because this module only runs under flask

# module specific needs
from ... import version

class testException(Exception): pass

class ViewDebug(MethodView):
    
    def get(self):
        try:
            # only owner can do this
            if not owner_permission.can():
                return abort(403)
            
            thisversion = version.__version__
            appconfigpath = getattr(current_app,'configpath','<not set>')
            appconfigtime = getattr(current_app,'configtime','<not set>')

            # collect groups of system variables                        
            sysvars = []
            
            # collect app.config variables
            configkeys = sorted(list(current_app.config.keys()))
            appconfig = []
            for key in configkeys:
                value = current_app.config[key]
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
bp.add_url_rule('/_debuginfo',view_func=ViewDebug.as_view('debug'),methods=['GET'])


class TestException(MethodView):
    
    def get(self):
        try:
            raise testException
                    
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/xcauseexception',view_func=TestException.as_view('testexception'),methods=['GET'])
