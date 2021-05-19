###########################################################################################
"""
club - club view
==================
"""
# standard

# pypi
from flask import session

# home grown
from . import bp
from ...accesscontrol import owner_permission, UpdateClubDataPermission
from ...crudapi import CrudApi, DbQueryApi

# module specific needs
from ...model import Club

###########################################################################################
# manageclubs endpoint
###########################################################################################

club_dbattrs = 'id,shname,name,location,memberserviceapi,memberserviceid'.split(',')
club_formfields = 'rowid,shname,name,location,service,serviceid'.split(',')
club_dbmapping = dict(list(zip(club_dbattrs, club_formfields)))
club_formmapping = dict(list(zip(club_formfields, club_dbattrs)))
club = CrudApi(
   app = bp,
   pagename = 'Clubs', 
   endpoint = '.manageclubs', 
   rule = '/manageclubs',
   dbmapping = club_dbmapping, 
   formmapping = club_formmapping, 
   writepermission = owner_permission.can, 
   dbtable = Club, 
   clientcolumns = [
      { 'data': 'shname', 'name': 'shname', 'label': 'Short Name (slug)' },
      { 'data': 'name', 'name': 'name', 'label': 'Long Name' },
      { 'data': 'location', 'name': 'location', 'label': 'Location' },
      { 'data': 'service', 'name': 'service', 'label': 'Service' },
      { 'data': 'serviceid', 'name': 'serviceid', 'label': 'Service ID' },
   ], 
   servercolumns = None,  # not server side
   byclub = False, 
   idSrc = 'rowid', 
   buttons = ['create', 'edit', 'remove'])
club.register()

###########################################################################################
# clubservice api endpoint
###########################################################################################

club_service = DbQueryApi(
   app = bp,
   endpoint = '._clubservice',
   rule = '/_clubservice',
   permission = lambda: UpdateClubDataPermission(session['club_id']).can(),
   byclub = False,
   dbtable = Club,
   jsonmapping = {'service':'memberserviceapi', 'serviceid':'memberserviceid'}
   )
club_service.register()
