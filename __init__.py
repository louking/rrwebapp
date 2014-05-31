###########################################################################################
# raceresultswebapp - package
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/03/13        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
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
import tools
import sysinfo
import docs

# initialize versions for scripts
request.setscripts()
