###########################################################################################
# accesscontrol - access control permission and need definitions
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/18/14        Lou King        Create
#
#   Copyright 2014 Lou King
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
from flask_login import current_user
from flask_principal import Principal, Permission, RoleNeed, UserNeed

# home grown
from . import app
from .model import db   # this is ok because this module only runs under flask

########################################################################
# permissions definition
########################################################################
# load principal extension, and define permissions
# see http://pythonhosted.org/Flask-Principal/ section on Granular Resource Protection
principals = Principal(app)
owner_permission = Permission(RoleNeed('owner'))
admin_permission = Permission(RoleNeed('admin'))
viewer_permission = Permission(RoleNeed('viewer'))

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


