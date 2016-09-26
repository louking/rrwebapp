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
from collections import OrderedDict

# homegrown
from crudapi import CrudApi
from accesscontrol import owner_permission
from racedb import ApiCredentials


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
             buttons = ['create', 'edit', 'remove', 'csv'])
sc.register()
