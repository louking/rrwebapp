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

# standard
from json import loads, dumps

# pypi
from flask import url_for
from collections import OrderedDict

# homegrown
from . import app
from crudapi import CrudApi, DbQueryApi
from accesscontrol import owner_permission
from racedb import ApiCredentials, RaceResultService, insert_or_update


###########################################################################################
class ServiceAttributes(object):
###########################################################################################
    '''
    access for service attributes in RaceResultService

    :param servicename: name of service
    '''

    #----------------------------------------------------------------------
    def _getconfigattrs(self):
    #----------------------------------------------------------------------
        apicredentials = ApiCredentials.query.filter_by(name=self.servicename).first()
        if not apicredentials:
            return {}

        self.rrs = RaceResultService.query.filter_by(club_id=self.club_id, apicredentials_id=apicredentials.id).first()
        if not self.rrs or not self.rrs.attrs:
            return {}

        # app.logger.debug('self.rrs.attrs {}'.format(self.rrs.attrs))
        return loads(self.rrs.attrs)

    #----------------------------------------------------------------------
    def __init__(self, club_id, servicename):
    #----------------------------------------------------------------------
        self.club_id = club_id
        self.servicename = servicename
        
        # update defaults here
        self.attrs = dict(
                         maxdistance = None,
                        )

        # get configured attributes
        configattrs = self._getconfigattrs()

        # bring in configuration, if any
        self.attrs.update(configattrs)
        # app.logger.debug('service {} configattrs {} self.attrs {}'.format(servicename, configattrs, self.attrs))

        # attrs become attributes of this object
        for attr in self.attrs:
            setattr(self, attr, self.attrs[attr])

    #----------------------------------------------------------------------
    def set_attr(self, name, value):
    #----------------------------------------------------------------------
        configattrs = self._getconfigattrs()
        configattrs[name] = value
        
        # update database
        self.rrs.attrs = dumps(configattrs)
        insert_or_update(db.session, RaceResultService, self.rrs, skipcolumns=['id'], name=self.service)


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

#----------------------------------------------------------------------
# raceresultservices endpoint
#----------------------------------------------------------------------

rrs_services = DbQueryApi(endpoint = 'services',
                          permission = owner_permission.can,
                          byclub = False,
                          dbtable = ApiCredentials,
                          jsonmapping = {'label':'name', 'value':'id'}
                         )
rrs_services.register()

rrs_dbattrs = 'id,apicredentials_id,attrs'.split(',')
rrs_formfields = 'rowid,service,attrs'.split(',')
rrs_dbmapping = OrderedDict(zip(rrs_dbattrs, rrs_formfields))
rrs_formmapping = OrderedDict(zip(rrs_formfields, rrs_dbattrs))
rrs_formmapping['service'] = lambda rrsrow: ApiCredentials.query.filter_by(id=rrsrow.apicredentials_id).first().name
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
                { 'data': 'attrs', 'name': 'attrs', 'label': 'Attributes (json object)' },
             ], 
             servercolumns = None,  # no ajax
             byclub = True, 
             idSrc = 'rowid', 
             buttons = ['create', 'edit', 'remove'])
rrs.register()

