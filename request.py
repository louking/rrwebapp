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

class invalidScript(Exception): pass

# all scripts required by this application are specified here
# scripts are listed in the order they must be processed
# all css scripts are processed before all js scripts - see layout.html for details
SCRIPTS = [
    'js/jquery-1.11.3.min.js',

    # 'js/jquery-ui-1.11.4/jquery-ui.js',
    # 'js/jquery-ui-1.11.4/themes/smoothness/jquery-ui.css',
    'js/jquery-ui-1.10.4.custom.js',
    'css/sm-f0-8em-theme/jquery-ui-1.10.4.custom.min.css',

    'js/DataTables-1.10.11/DataTables-1.10.11/js/jquery.dataTables.js',
    'js/DataTables-1.10.11/DataTables-1.10.11/js/dataTables.jqueryui.js',
    'js/DataTables-1.10.11/DataTables-1.10.11/css/dataTables.jqueryui.css',

    'js/DataTables-1.10.11/Buttons-1.1.2/js/dataTables.buttons.js',
    'js/DataTables-1.10.11/Buttons-1.1.2/js/buttons.jqueryui.js',

    'js/DataTables-1.10.11/Buttons-1.1.2/js/buttons.html5.js',
    'js/DataTables-1.10.11/Buttons-1.1.2/css/buttons.jqueryui.css',

    'js/DataTables-1.10.11/Editor-1.5.5/js/dataTables.editor.js',
    'js/DataTables-1.10.11/Editor-1.5.5-errorfix/js/editor.jqueryui.js',
    'js/DataTables-1.10.11/Editor-1.5.5/css/editor.jqueryui.css',

    'js/DataTables-1.10.11/Select-1.1.2/js/dataTables.select.js',
    'js/DataTables-1.10.11/Select-1.1.2/css/select.jqueryui.css',

    # 'js/chosen_v1.4.2/chosen.jquery.min.js',
    # 'js/chosen_v1.4.2/chosen.min.css',

    'js/select2-4.0.1/js/select2.full.js',
    'js/select2-4.0.1/css/select2.css',

    'js/selectize.js-0.12.1/css/selectize.css',
    'js/selectize.js-0.12.1/js/standalone/selectize.js',
    'js/DataTables-1.10.11/FieldType-Selectize/editor.selectize.js',
    'js/DataTables-1.10.11/FieldType-Selectize/editor.selectize.css',

    'js/yadcf-0.8.9/jquery.dataTables.yadcf.js',
    'js/yadcf-0.8.9/jquery.dataTables.yadcf.css',

    'js/jquery.ui.dialog-clickoutside.js', # from https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside

    'RaceResults.js',
    'style.css',

]

#----------------------------------------------------------------------
def annotatescripts(scripts):
#----------------------------------------------------------------------
    '''
    annotate scripts with version = file timestamp
    this is used to force browser to reload script file when it changes

    :param scripts: list of script filenames to annotate
    :rtype: list of {'filename':filename, 'version':version}
    '''
    annotated = []
    for thisfile in scripts:
        version = os.stat(os.path.join(app.static_folder,thisfile))[stat.ST_MTIME]
        annotation = {'filename':thisfile,'version':version}
        annotated.append(annotation)

    return annotated
    
#----------------------------------------------------------------------
def setscripts():
#----------------------------------------------------------------------
    '''
    setscripts caches the versions for js and css scripts, identified in
    request.SCRIPTS
    '''
    cssfiles = []
    jsfiles = []
    for thisfile in SCRIPTS:
        filetype = thisfile.split('.')[-1]  # gets file extension
        if filetype == 'css':
            cssfiles.append(thisfile)
        elif filetype == 'js':
            jsfiles.append(thisfile)
        else:
            raise invalidScript,'Invalid script filename: {}'.format(thisfile)
    
    # make these available to any template
    app.jinja_env.globals['_rrwebapp_cssfiles'] = annotatescripts(cssfiles)
    app.jinja_env.globals['_rrwebapp_jsfiles'] = annotatescripts(jsfiles)
    
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
        app.logger.info('{}: {} {} {}'.format(request.remote_addr, request.method, request.url, response.status_code))
    return response


