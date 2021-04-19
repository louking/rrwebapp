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
"""
request - generic request processing
========================================
"""
# standard
import os
import os.path
import stat
from datetime import timedelta
from functools import update_wrapper


# pypi
import flask
from flask import url_for, make_response, request, current_app
from flask_login import login_required
from flask.views import MethodView

# home grown
from . import app

# # module specific needs
# from .nav import setnavigation

class invalidScript(Exception): pass

# all scripts required by this application are specified here
# scripts are listed in the order they must be processed
# all css scripts are processed before all js scripts - see layout.html for details

# in SCRIPTS files from a CDN are contained in (filename, version, cdn) tuples
#    cdn is host for content data network
#    filename may contain {ver}, {min} as replacement_field {field_name}
#    {min} gets replaced with '.min' if app.config['MINIMIZE_CDN_JAVASCRIPT'] is True
#    {ver} gets replaced with version

# if scriptitem in request.SCRIPTS is not a tuple, it is assumed to be the string filename 
# of a file located in server static directory. v arg is set to modification time of the
# file to assure updated files will be downloaded (i.e., cache won't be used)

#----------------------------------------------------------------------
def annotatescripts(scripts):
#----------------------------------------------------------------------
    '''
    annotate scripts with version = file timestamp
    this is used to force browser to reload script file when it changes

    in scripts files from a CDN are contained in (filename, version, cdn) tuples
       cdn is host for content data network
       filename may contain {ver}, {min} as replacement_field {field_name}
       {min} gets replaced with '.min' if app.config['MINIMIZE_CDN_JAVASCRIPT'] is True
       {ver} gets replaced with version

    if scriptitem in request.SCRIPTS is not a tuple, it is assumed to be the string filename 
    of a file located in server static directory. v arg is set to modification time of the
    file to assure updated files will be downloaded (i.e., cache won't be used)

    :param scripts: list of scriptitems to annotate
    :rtype: list of {'filename':filename, 'version':version}

    '''
    annotated = []
    
    for scriptitem in scripts:
        # handle CDN items
        if isinstance(scriptitem, tuple):
            thisfile, version, cdn = scriptitem

            # maybe get minimized version
            cdnmin = ''
            if 'MINIMIZE_CDN_JAVASCRIPT' in app.config and app.config['MINIMIZE_CDN_JAVASCRIPT']:
                cdnmin = '.min'

            # format based on whether query options are already included
            # query options not present
            if '?' not in cdn:
                # remove any trailing '/' from cdn
                if cdn[-1] == '/':
                    cdn = cdn[:-1]
                fileref = '{}/{}?v={}'.format(cdn,thisfile.format(ver=version,min=cdnmin),version)
            # query options already present
            # NOTE: this part of the logic doesn't work because somewhere string is getting url quoted
            else:
                fileref = '{}{}&v={}'.format(cdn,thisfile.format(ver=version,min=cdnmin),version)
        
        # handle static file items
        else:
            filepath = os.path.join(app.static_folder,scriptitem)
            version = os.stat(filepath)[stat.ST_MTIME]
            fileurl = url_for('static', filename=scriptitem)
            fileref = '{}?v={}'.format(fileurl, version)
        
        annotated.append(fileref)

    return annotated
    
#----------------------------------------------------------------------
def addscripts(scriptlist):
#----------------------------------------------------------------------
    '''
    return script tags for designated filenames. the result must be passed into
    template to be added to standard scripts. this can be used for js or css files
    but all in the list must be the same

    :param scriptlist: list of local filenames to be added to the jsfiles list when template is built
    :rtype: list of annotated scripts to be passed to template
    '''
    
    if len(scriptlist) == 0:
        return []

    # get filetype of first file
    thisfile = scriptlist[0]
    firstfiletype = scriptlist[0].split('.')[-1]
    if firstfiletype not in ['css', 'js']:
        raise invalidScript('Invalid script filename: {}'.format(thisfile))

    # make sure all scripts referenced are of same type as first
    for thisfile in scriptlist:
        filetype = thisfile.split('.')[-1]
        if filetype != firstfiletype:
            raise invalidScript('All scripts in script list must be of same type: {}'.format(scriptlist))

    return annotatescripts(scriptlist)

# moved to module __init__.create_app
# #----------------------------------------------------------------------
# @app.before_request
# def before_request():
# #----------------------------------------------------------------------
#     setnavigation()

# #----------------------------------------------------------------------
# @app.after_request
# def after_request(response):
# #----------------------------------------------------------------------
#     if not app.config['DEBUG']:
#         app.logger.info('{}: {} {} {}'.format(request.remote_addr, request.method, request.url, response.status_code))
#     return response


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
    if headers is not None and not isinstance(headers, str):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, str):
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
