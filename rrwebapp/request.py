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
from datetime import timedelta
from functools import update_wrapper


# pypi
import flask
from flask import make_response, request, current_app
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
def addscripts(scriptlist):
#----------------------------------------------------------------------
    '''
    return script tags for designated filenames. the result must be passed into
    template to be added to standard scripts. this can be used for js or css files
    but all in the list must be the same

    :param scriptlist: list of filenames to be added to the jsfiles list when template is built
    :rtype: list of annotated scripts to be passed to template
    '''
    
    if len(scriptlist) == 0:
        return []

    # get filetype of first file
    firstfiletype = scriptlist[0].split('.')[-1]
    if firstfiletype not in ['css', 'js']:
        raise invalidScript,'Invalid script filename: {}'.format(thisfile)

    # make sure all scripts referenced are of same type as first
    for thisfile in scriptlist:
        filetype = thisfile.split('.')[-1]
        if filetype != firstfiletype:
            raise invalidScript,'All scripts in script list must be of same type: {}'.format(scriptlist)

    return annotatescripts(scriptlist)

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


#----------------------------------------------------------------------
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
#----------------------------------------------------------------------
    '''
    crossdomain decorator

    methods: Optionally a list of methods that are allowed for this view. If not provided it will allow all methods that are implemented.
    headers: Optionally a list of headers that are allowed for this request.
    origin: '*' to allow all origins, otherwise a string with a URL or a list of URLs that might access the resource.
    max_age: The number of seconds as integer or timedelta object for which the preflighted request is valid.
    attach_to_all: True if the decorator should add the access control headers to all HTTP methods or False if it should only add them to OPTIONS responses.
    automatic_options: If enabled the decorator will use the default Flask OPTIONS response and attach the headers there, otherwise the view function will be called to generate an appropriate response.

    from http://flask.pocoo.org/snippets/56/
    '''
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
