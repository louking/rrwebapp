###########################################################################################
#   location - read location from cache or google
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/18/16    Lou King    Create
#
#   Copyright 2016 Lou King
###########################################################################################
'''
location - read location from cache or google
===================================================================

Read location for a given address from the cache (database) or from google
Update the cache as necessary
'''

# standard
from datetime import timedelta

# pypi
from flask import current_app

# home grown
from . import bp
from ...accesscontrol import owner_permission
from ...crudapi import CrudApi
from ...model import Location


###########################################################################################
# locations endpoint
###########################################################################################

loc_dbattrs = 'id,name,latitude,longitude,cached_at,lookuperror'.split(',')
loc_formfields = 'rowid,loc,lat,long,cached,error'.split(',')
loc_dbmapping = dict(list(zip(loc_dbattrs, loc_formfields)))
loc_formmapping = dict(list(zip(loc_formfields, loc_dbattrs)))
loc = CrudApi(
    app = bp,
    pagename = 'Locations', 
    endpoint = 'admin.locations', 
    rule = '/locations',
    dbmapping = loc_dbmapping, 
    formmapping = loc_formmapping, 
    writepermission = owner_permission.can, 
    dbtable = Location, 
    clientcolumns = [
       {'data': 'loc', 'name': 'loc', 'label': 'Location Name'},
       {'data': 'lat', 'name': 'lat', 'label': 'Latitude'},
       {'data': 'long', 'name': 'long', 'label': 'Longitude'},
       {'data': 'cached', 'name': 'cached', 'label': 'Cached'},
       {'data': 'error', 'name': 'error', 'label': 'Error', '_treatment': {'boolean': {'formfield': 'error', 'dbfield': 'lookuperror'}}},
    ],
    serverside = True,
    byclub = False,
    idSrc = 'rowid', 
    buttons = ['create', 'edit', 'remove']
    )
loc.register()


