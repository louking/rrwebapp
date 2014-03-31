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
from nav import setnavigation
from loutilities import apikey

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
configdir = getapikey('configdir')
#if not secretkey:
#    secretkey = os.urandom(24)
#    ak.updatekey('secretkey',keyvalue)

# configure app
DEBUG = debug
if DEBUG:
    SECRET_KEY = 'flask development key'
else:
    SECRET_KEY = secretkey
app.config.from_object(__name__)

if configdir and os.path.exists(os.path.join(configdir,'rrwebapp.cfg')):
    app.logger.info('configuring from rrwebapp.cfg')
    app.config.from_pyfile(os.path.join(configdir,'rrwebapp.cfg'))
    
# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# set up logging
ADMINS = ['lking@pobox.com']
if not app.debug:
    import logging
    from logging.handlers import SMTPHandler
    from logging import FileHandler, Formatter
    mail_handler = SMTPHandler('smtp.secureserver.net',
                               'noreply@steeplechasers.org',
                               ADMINS, 'rrwebapp error')
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
    
    if logdir:
        file_handler = FileHandler(os.path.join(logdir,'rrwebapp.log'),delay=True)
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
    
        file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
    
# import all views
import login
import club
import userrole
import race
import member
import results
import standings
import sysinfo

@app.before_request
def before_request():
    setnavigation()

########################################################################
########################################################################
#----------------------------------------------------------------------
@app.route('/')
def index():
#----------------------------------------------------------------------
    return flask.render_template('index.html')

########################################################################
########################################################################
#----------------------------------------------------------------------
@app.route('/ownerconsole')
@login_required
def ownerconsole():
#----------------------------------------------------------------------
    return flask.render_template('ownerconsole.html')

#----------------------------------------------------------------------
# main processing - run application
#----------------------------------------------------------------------
if __name__ == '__main__':
    app.run()