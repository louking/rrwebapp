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
from flask import Flask
from flask.ext.login import login_required
import flask.ext.principal as principal
import flask.ext.wtf as flaskwtf
import wtforms
from celery import Celery

# homegrown -- why were these here?
#import database_flask # this is ok because this subpackage only runs under flask
#from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
#                                    UpdateClubDataPermission, ViewClubDataPermission
from loutilities.configparser import getitems

# import os
# print 'pid={} __init__.py executed'.format(os.getpid())

# create app and celery tasking back end
app = Flask('rrwebapp')

# define product name (don't import nav until after app.jinja_env.globals['_rrwebapp_productname'] set)
# TODO: this really should be set in rrwebapp.cfg
app.jinja_env.globals['_rrwebapp_productname'] = '<span class="brand-all"><span class="brand-left">score</span><span class="brand-right">tility</span></span>'
app.jinja_env.globals['_rrwebapp_productname_text'] = 'scoretility'
#from nav import productname

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# get configuration
configpath = os.path.join(os.path.sep.join(os.path.dirname(__file__).split(os.path.sep)[:-2]), 'rrwebapp.cfg')
appconfig = getitems(configpath, 'app')
app.config.update(appconfig)

celery = Celery('rrwebapp')

configpath = os.path.join(os.path.sep.join(os.path.dirname(__file__).split(os.path.sep)[:-2]), 'rrwebapp.cfg')
celeryconfig = getitems(configpath, 'celery')
celery.conf.update(celeryconfig)

import time
from loutilities import timeu
tu = timeu.asctime('%Y-%m-%d %H:%M:%S')
app.configtime = tu.epoch2asc(time.time())

# must set up logging after setting configuration
import applogging
applogging.setlogging()

# import all views
import services
import request
import index
import login
import club
import userrole
import race
import member
import results
import resultsanalysis
import standings
import tools
import sysinfo
import docs
import staticfiles

# initialize versions for scripts
# need to force app context with test_request_context() else get
#    RuntimeError: Attempted to generate a URL without the application context being pushed.
# see http://kronosapiens.github.io/blog/2014/08/14/understanding-contexts-in-flask.html
# NOTE: with app_context() was not sufficient to prevent runtime error
with app.test_request_context():
    request.setscripts()


