###########################################################################################
# raceresultswebapp - package
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/03/13        Lou King        Create
#
#   Copyright 2013 Lou King
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
import logging

# pypi
import flask
from flask.ext.login import login_required
import flask.ext.principal as principal
import flask.ext.wtf as flaskwtf
import wtforms

# homegrown
from app import app
import database_flask # this is ok because this subpackage only runs under flask
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from loutilities import apikey

# define product name (don't import nav until after app.jinja_env.globals['_rrwebapp_productname'] set)
app.jinja_env.globals['_rrwebapp_productname'] = '<span class="brand-all"><span class="brand-left">score</span><span class="brand-right">tility</span></span>'
#from nav import productname

ak = apikey.ApiKey('Lou King','raceresultswebapp')

def getapikey(key):
    try:
        keyval = ak.getkey(key)
        return eval(keyval)
    except apikey.unknownKey:
        return None
    except:     # NameError, SyntaxError, what else?
        return keyval
    
# get api keys
logdir = getapikey('logdirectory')
debug = True if getapikey('debug') else False
secretkey = getapikey('secretkey')
#configdir = getapikey('configdir')
#fileloglevel = getapikey('fileloglevel')
#mailloglevel = getapikey('emailloglevel')
#if not secretkey:
#    secretkey = os.urandom(24)
#    ak.updatekey('secretkey',keyvalue)

# configure app
# TODO: these should come from rrwebapp.cfg
DEBUG = debug
if DEBUG:
    SECRET_KEY = 'flask development key'
else:
    SECRET_KEY = secretkey
app.config.from_object(__name__)

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# TODO: move this to new module logging, bring in from dispatcher
# set up logging
ADMINS = ['lking@pobox.com']
if not app.debug:
    from logging.handlers import SMTPHandler
    from logging import FileHandler, Formatter
    mail_handler = SMTPHandler('localhost',
                               'noreply@steeplechasers.org',
                               ADMINS, '[scoreTILITY] exception encountered')
    if 'LOGGING_LEVEL_MAIL' in app.config:
        mailloglevel = app.config['LOGGING_LEVEL_MAIL']
    else:
        mailloglevel = logging.ERROR
    mail_handler.setLevel(mailloglevel)
    mail_handler.setFormatter(Formatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s
    
    Message:
    
    %(message)s
    '''))
    app.logger.addHandler(mail_handler)
    
    if logdir:
        file_handler = FileHandler(os.path.join(logdir,'rrwebapp.log'),delay=True)
        if 'LOGGING_LEVEL_FILE' in app.config:
            fileloglevel = app.config['LOGGING_LEVEL_FILE']
        else:
            fileloglevel = logging.WARNING
        file_handler.setLevel(fileloglevel)
        app.logger.addHandler(file_handler)
    
        file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
    
# import all views
import request
import index
import login
import club
import userrole
import race
import member
import results
import standings
import sysinfo

# initialize versions for scripts
request.setscripts()
