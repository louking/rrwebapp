###########################################################################################
# request - generic request processing
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/05/14        Lou King        Create
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
    setscripts()


