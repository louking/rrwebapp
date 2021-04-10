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
import time
from datetime import timedelta

# pypi

# github
from googlemaps import Client
from googlemaps.geocoding import geocode
from haversine import haversine

# home grown
from . import app
from .accesscontrol import owner_permission
from .racedb import ApiCredentials, Location, MAX_LOCATION_LEN, insert_or_update
from .crudapi import CrudApi
from loutilities.timeu import epoch2dt
from .database_flask import db   # this is ok because this module only runs under flask

CACHE_REFRESH = timedelta(30)   # 30 days, per https://cloud.google.com/maps-platform/terms/maps-service-terms/?&sign=0 (sec 3.4)

#----------------------------------------------------------------------
def get_distance(loc1, loc2, miles=True):
#----------------------------------------------------------------------
    '''
    retrieves distance between two Location objects
    if either location is unknown (lookuperror occurred), None is returned
    NOTE: must check for error like "if get_distance() != None" because 0 is a valid return value

    :param loc1: Location object
    :param loc2: Location object
    :rtype: distance between loc1 and loc2, or None if error
    '''
    # check for bad data
    if loc1.lookuperror or loc2.lookuperror:
        return None

    # return great circle distance between points
    loc1latlon = (loc1.latitude, loc1.longitude)
    loc2latlon = (loc2.latitude, loc2.longitude)
    return haversine(loc1latlon, loc2latlon, miles=miles)

###########################################################################################
class LocationServer(object):
###########################################################################################

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------

        googlekey = ApiCredentials.query.filter_by(name='googlemaps').first().key
        self.client = Client(key=googlekey)

    #----------------------------------------------------------------------
    def getlocation(self, address):
    #----------------------------------------------------------------------
        '''
        retrieve location from database, if available, else get from googlemaps api

        :param address: address for lookup
        :rtype: Location instance
        '''

        dbaddress = address
        if len(dbaddress) > MAX_LOCATION_LEN:
            dbaddress = dbaddress[0:MAX_LOCATION_LEN]

        loc = Location.query.filter_by(name=dbaddress).first()

        now = epoch2dt(time.time())
        if not loc or (now - loc.cached_at > CACHE_REFRESH):
            # new location
            loc = Location(name=dbaddress)

            # get geocode from google
            # use the full address, not dbaddress which gets s
            gc = geocode(self.client, address=address)

            # if we got good data, fill in the particulars
            # assume first in list is good, give warning if multiple entries received back
            if gc:
                # notify if multiple values returned
                if len(gc) > 1:
                    app.logger.warning('geocode: multiple locations ({}) received from googlemaps for {}'.format(len(gc), address))

                # save lat/long from first value returned
                loc.latitude  = gc[0]['geometry']['location']['lat']
                loc.longitude = gc[0]['geometry']['location']['lng']

            # if no response, still store in database, but flag as error
            else:
                loc.lookuperror = True

            # remember when last retrieved
            loc.cached_at = now

            # insert or update -- flush is done within, so id should be set after this
            insert_or_update(db.session, Location, loc, skipcolumns=['id'], name=dbaddress)

        # and back to caller
        return loc

###########################################################################################
# locations endpoint
###########################################################################################

loc_dbattrs = 'id,name,latitude,longitude,cached_at,lookuperror'.split(',')
loc_formfields = 'rowid,loc,lat,long,cached,error'.split(',')
loc_dbmapping = dict(list(zip(loc_dbattrs, loc_formfields)))
loc_formmapping = dict(list(zip(loc_formfields, loc_dbattrs)))
loc = CrudApi(pagename = 'Locations', 
             endpoint = 'locations', 
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
             buttons = ['create', 'edit', 'remove'])
loc.register()


