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
import os.path

# pypi
from flask import Flask, send_from_directory
from jinja2 import ChoiceLoader, PackageLoader

from celery import Celery

# homegrown -- why were these here?
#import database_flask # this is ok because this subpackage only runs under flask
#from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
#                                    UpdateClubDataPermission, ViewClubDataPermission
import loutilities
from loutilities.configparser import getitems

# bring in js, css assets
from . import assets
from .assets import asset_env, asset_bundles

# create app and celery tasking back end
app = Flask('rrwebapp')

# get configuration
configpath = os.path.join(os.path.sep.join(os.path.dirname(__file__).split(os.path.sep)[:-2]), 'rrwebapp.cfg')
appconfig = getitems(configpath, 'app')
app.config.update(appconfig)

# add loutilities tables-assets for js/css/template loading
# see https://adambard.com/blog/fresh-flask-setup/
#    and https://webassets.readthedocs.io/en/latest/environment.html#webassets.env.Environment.load_path
# loutilities.__file__ is __init__.py file inside loutilities; os.path.split gets package directory
loutilitiespath = os.path.join(os.path.split(loutilities.__file__)[0], 'tables-assets', 'static')

@app.route('/loutilities/static/<path:filename>')
def loutilities_static(filename):
    return send_from_directory(loutilitiespath, filename)

with app.app_context():
    # js/css files
    asset_env.append_path(app.static_folder)
    asset_env.append_path(loutilitiespath, '/loutilities/static')

    # templates
    loader = ChoiceLoader([
        app.jinja_loader,
        PackageLoader('loutilities', 'tables-assets/templates')
    ])
    app.jinja_loader = loader

# initialize assets
asset_env.init_app(app)
asset_env.register(asset_bundles)

# define product name (don't import nav until after app.jinja_env.globals['_productname'] set)
# TODO: this really should be set in rrwebapp.cfg
app.jinja_env.globals['_productname'] = '<span class="brand-all"><span class="brand-left">score</span><span class="brand-right">tility</span></span>'
app.jinja_env.globals['_productname_text'] = 'scoretility'
#from nav import productname

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

celery = Celery('rrwebapp')

configpath = os.path.join(os.path.sep.join(os.path.dirname(__file__).split(os.path.sep)[:-2]), 'rrwebapp.cfg')
celeryconfig = getitems(configpath, 'celery')
celery.conf.update(celeryconfig)

import time
from loutilities import timeu
tu = timeu.asctime('%Y-%m-%d %H:%M:%S')
app.configtime = tu.epoch2asc(time.time())

# must set up logging after setting configuration
from . import applogging
applogging.setlogging()

# import all views
from . import services
from . import request
from . import index
from . import login
from . import club
from . import userrole
from . import race
from . import member
from . import results
from . import resultsanalysis
from . import standings
from . import location
from . import tools
from . import sysinfo
from . import docs
from . import staticfiles
from . import agegradeapi


