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
from ConfigParser import SafeConfigParser

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

# define product name (don't import nav until after app.jinja_env.globals['_rrwebapp_productname'] set)
app.jinja_env.globals['_rrwebapp_productname'] = '<span class="brand-all"><span class="brand-left">score</span><span class="brand-right">tility</span></span>'
#from nav import productname

# must set up logging after setting configuration
import applogging
applogging.setlogging()

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# copy configuration into app.config
def getwebappconfig(app, filepath):
    config = SafeConfigParser()
    config.readfp(open(filepath))
    appconfig = config.items('app')

    # apply configuration to app
    # eval is safe because this configuration is controlled at root
    for key,value in appconfig:
        try:
            app.config[key.upper()] = eval(value)
        except:
            app.config[key.upper()] = value

# get configuration
thisdir = os.path.dirname(__file__)
sep = os.path.sep
configdir = sep.join(thisdir.split(sep)[:-2])
app.configpath = os.path.join(configdir, 'rrwebapp.cfg')
getwebappconfig(app, app.configpath)

import time
from loutilities import timeu
tu = timeu.asctime('%Y-%m-%d %H:%M:%S')
app.configtime = tu.epoch2asc(time.time())

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


