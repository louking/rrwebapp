###########################################################################################
# request - generic request processing
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/05/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import os
import os.path
import stat

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView

# home grown
from . import app
from database_flask import db   # this is ok because this module only runs under flask

# module specific needs
from nav import setnavigation

# all scripts required by this application are specified here
# scripts are listed in the order they must be processed
SCRIPTS_JS = [
    'js/jquery-1.11.0.min.js',
    'js/jquery-ui-1.10.4.custom.min.js',
    'js/jquery.dataTables.min.js',
    'js/jquery.dataTables.yadcf.js',
    'js/jquery.ui.dialog-clickoutside.js', # from https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside
    #'js/jquery.browser.js',         # browser removed from JQueryUI 1.9, needed by FixedColumns
    #'js/FixedColumns.js',
    
    'RaceResults.js',
]
SCRIPTS_CSS = [
    'css/sm-f0-8em-theme/jquery-ui-1.10.4.custom.min.css',
    'css/jquery.dataTables.css',
    'css/jquery.dataTables.yadcf.css',
    
    'style.css',
]

#----------------------------------------------------------------------
def setscripts():
#----------------------------------------------------------------------
    '''
    setscripts caches the versions for js and css scripts, identified in
    request.SCRIPTS_JS and SCRIPTS_CSS, respectively.
    
    This can be called before_request, or at initialization.  If called
    at initialization, the application must be restarted for these to take
    effect.
    '''
    cssfiles = []
    for thisfile in SCRIPTS_CSS:
        version = os.stat(os.path.join(app.static_folder,thisfile))[stat.ST_MTIME]
        fileinfo = {'filename':thisfile,'version':version}
        cssfiles.append(fileinfo)
    
    jsfiles = []
    for thisfile in SCRIPTS_JS:
        version = os.stat(os.path.join(app.static_folder,thisfile))[stat.ST_MTIME]
        fileinfo = {'filename':thisfile,'version':version}
        jsfiles.append(fileinfo)

    # make these available to any template
    app.jinja_env.globals['_rrwebapp_cssfiles'] = cssfiles
    app.jinja_env.globals['_rrwebapp_jsfiles'] = jsfiles
    
#----------------------------------------------------------------------
@app.before_request
def before_request():
#----------------------------------------------------------------------
    setnavigation()

#----------------------------------------------------------------------
@app.after_request
def after_request(response):
#----------------------------------------------------------------------
    if not app.config['DEBUG']:
        app.logger.info('{} {} {}'.format(request.method, request.url, response.status_code))
    return response


