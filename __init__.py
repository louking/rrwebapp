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

# configure app
DEBUG = True
if DEBUG:
    SECRET_KEY = 'flask development key'
else:
    SECRET_KEY = os.urandom(24)
app.config.from_object(__name__)

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# import all views
import login
import club
import userrole
import race
import member
import results
import standings
import hello

@app.before_request
def before_request():
    setnavigation()

# db commit is done in each request handler
#@app.teardown_request
#def teardown_request(exception):
#    db.session.commit()

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