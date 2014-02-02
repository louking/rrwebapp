###########################################################################################
# accesscontrol - access control permission and need definitions
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/18/14        Lou King        Create
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
'''
accesscontrol - access control permission and need definitions
===================================================================

'''

# standard
from collections import namedtuple
from functools import partial

# pypi
import flask
from flask.ext.login import current_user
from flask.ext.principal import Principal, Permission, RoleNeed, UserNeed

# home grown
from . import app
from database_flask import db   # this is ok because this module only runs under flask

########################################################################
# permissions definition
########################################################################
# load principal extension, and define permissions
# see http://pythonhosted.org/Flask-Principal/ section on Granular Resource Protection
principals = Principal(app)
owner_permission = Permission(RoleNeed('owner'))
#admin_permission = Permission(RoleNeed('admin'))
#viewer_permission = Permission(RoleNeed('viewer'))

ClubDataNeed = namedtuple('club_data', ['method', 'value'])
UpdateClubDataNeed = partial(ClubDataNeed,'update')
ViewClubDataNeed = partial(ClubDataNeed,'view')

class UpdateClubDataPermission(Permission):
    def __init__(self, clubid):
        need = UpdateClubDataNeed(clubid)
        super(UpdateClubDataPermission, self).__init__(need)

class ViewClubDataPermission(Permission):
    def __init__(self, clubid):
        need = ViewClubDataNeed(clubid)
        super(ViewClubDataPermission, self).__init__(need)


