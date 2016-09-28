###########################################################################################
# services - external service access
#
#       Date            Author          Reason
#       ----            ------          ------
#       09/23/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
#
###########################################################################################

# pypi
from flask import url_for
from collections import OrderedDict
from datatables import ColumnDT

# homegrown
from crudapi import CrudApi, DbQueryApi
from accesscontrol import owner_permission
from racedb import ApiCredentials, RaceResultService


#----------------------------------------------------------------------
# servicecredentials endpoint
#----------------------------------------------------------------------

sc_dbattrs = 'id,name,key,secret'.split(',')
sc_formfields = 'rowid,name,key,secret'.split(',')
sc_dbmapping = OrderedDict(zip(sc_dbattrs, sc_formfields))
sc_formmapping = OrderedDict(zip(sc_formfields, sc_dbattrs))
sc = CrudApi(pagename = 'Service Credentials', 
             endpoint = 'servicecredentials', 
             dbmapping = sc_dbmapping, 
             formmapping = sc_formmapping, 
             writepermission = owner_permission.can, 
             dbtable = ApiCredentials, 
             clientcolumns = [
                { 'data': 'name', 'name': 'name', 'label': 'Service Name' },
                { 'data': 'key', 'name': 'key', 'label': 'Key', 'render':'$.fn.dataTable.render.text()' }, 
                { 'data': 'secret', 'name': 'secret', 'label': 'Secret', 'render':'$.fn.dataTable.render.text()' }
             ], 
             servercolumns = None,  # no ajax
             byclub = False, 
             idSrc = 'rowid', 
             buttons = ['create', 'edit', 'remove'])
sc.register()

rrs_services = DbQueryApi(endpoint = 'services',
                          permission = owner_permission.can,
                          byclub = False,
                          dbtable = ApiCredentials,
                          jsonmapping = {'label':'name', 'value':'id'}
                         )
rrs_services.register()

rrs_dbattrs = 'id,apicredentials_id'.split(',')
rrs_formfields = 'rowid,service'.split(',')
rrs_dbmapping = OrderedDict(zip(rrs_dbattrs, rrs_formfields))
rrs_formmapping = OrderedDict(zip(rrs_formfields, rrs_dbattrs))
rrs_formmapping['service'] = lambda rrsrow: ApiCredentials.query.filter_by(id=rrsrow.apicredentials_id).first().name
rrs_apicredentials = ApiCredentials.query.all()
rrs = CrudApi(pagename = 'Race Result Services', 
             endpoint = 'raceresultservices', 
             dbmapping = rrs_dbmapping, 
             formmapping = rrs_formmapping, 
             writepermission = owner_permission.can, 
             dbtable = RaceResultService, 
             clientcolumns = [
                { 'data': 'service', 'name': 'service', 'label': 'Service Name',
                  'type': 'selectize', 'options': [],
                  'opts': { 
                    'searchField': 'label',
                    'openOnFocus': False
                   },
                  '_update': {
                    'endpoint': 'services',
                    'wrapper' : {'options': {'service':'_response_'} },
                    'on': 'open',
                  }
                },
             ], 
             servercolumns = None,  # no ajax
             byclub = True, 
             idSrc = 'rowid', 
             buttons = ['create', 'edit', 'remove'])
rrs.register()

