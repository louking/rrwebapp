###########################################################################################
# crudapi - crudapi handling
#
#       Date            Author          Reason
#       ----            ------          ------
#       09/25/16        Lou King        Create
#
#   Copyright 2016 Lou King
#
###########################################################################################
'''
crudapi - crudapi handling
==================================================
'''

# standard
import traceback
from copy import deepcopy
from json import dumps, loads
from urllib import urlencode

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask.ext.login import login_required
from flask.views import MethodView
from datatables import DataTables, ColumnDT
from datatables_utils import DataTablesEditor, dt_editor_response, get_request_action, get_request_data

# homegrown
from . import app
from database_flask import db   # this is ok because this module only runs under flask
from request import addscripts

#----------------------------------------------------------------------
def _editormethod(checkaction='', formrequest=True):
#----------------------------------------------------------------------
    '''
    decorator for CrudApi methods used by Editor

    :param methodcore: function() containing core of method to execute
    :param checkaction: Editor name of action which is used by the decorated method, one of 'create', 'edit', 'remove' or '' if no check required
    :param formrequest: True if request action, data is in form (False for 'remove' action)
    '''
    # see http://python-3-patterns-idioms-test.readthedocs.io/en/latest/PythonDecorators.html
    def wrap(f):
        def wrapped_f(self, *args, **kwargs):
            self._club_id = flask.session['club_id']

            # prepare for possible errors
            self._error = ''
            self._fielderrors = []

            try:
                # verify user can write the data, otherwise abort
                if not self.writepermission():
                    db.session.rollback()
                    cause = 'operation not permitted for user'
                    return dt_editor_response(error=cause)
                
                # get action
                # TODO: modify get_request_action and get_request_data to allow either request object or form object, 
                # and remove if/else for formrequest, e.g., action = get_request_action(request)
                # (allowing form object deprecated for legacy code)
                if formrequest:
                    action = get_request_action(request.form)
                    self._data = get_request_data(request.form)
                else:
                    action = request.args['action']

                if checkaction and action != checkaction:
                    db.session.rollback()
                    cause = 'unknown action "{}"'.format(action)
                    app.logger.warning(cause)
                    return dt_editor_response(error=cause)

                # set up parameters to query, based on whether results are limited to club
                self._dbparms = {}
                if self.byclub:
                    self._dbparms['club_id'] = self._club_id

                # execute core of method
                f(self,*args, **kwargs)

                # commit database updates and close transaction
                db.session.commit()
                return dt_editor_response(data=self._responsedata)
            
            except:
                # roll back database updates and close transaction
                db.session.rollback()
                if self._fielderrors:
                    cause = 'please check indicated fields'
                elif self._error:
                    cause = self._error
                else:
                    cause = traceback.format_exc()
                    app.logger.error(traceback.format_exc())
                return dt_editor_response(data=[], error=cause, fieldErrors=self._fielderrors)
        return wrapped_f
    return wrap


#######################################################################
class CrudApi(MethodView):
#######################################################################
    '''
    provides initial render and RESTful CRUD api

    usage:
        instancename = CrudApi([arguments]):
        instancename.register()

    **dbmapping** is dict like {'dbattr_n':'formfield_n', 'dbattr_m':f(form), ...}
    **formmapping** is dict like {'formfield_n':'dbattr_n', 'formfield_m':f(dbrow), ...}
    if order of operation is important for either of these use OrderedDict

    **clientcolumns** should be like the following. See https://datatables.net/reference/option/columns and 
    https://editor.datatables.net/reference/option/fields for more information

        [
            { 'data': 'name', 'name': 'name', 'label': 'Service Name' },
            { 'data': 'key', 'name': 'key', 'label': 'Key', 'render':'$.fn.dataTable.render.text()' }, 
            { 'data': 'secret', 'name': 'secret', 'label': 'Secret', 'render':'$.fn.dataTable.render.text()' },
            { 'data': 'service', 'name': 'service_id', 
              'label': 'Service Name',
              'type': 'selectize', 
              'options': [{'label':'yes', 'value':1}, {'label':'no', 'value':0}],
              'opts': { 
                'searchField': 'label',
                'openOnFocus': False
               },
              '_update' {
                'endpoint' : <url endpoint to retrieve options from>,
                'on' : <event>
                'wrapper' : <wrapper for query response>
              }
            },
        ]

        * name - describes the column and is used within javascript
        * data - used on server-client interface and should be used in the formmapping key and dbmapping value
        * label - used for the DataTable table column and the Editor form label 
        * optional render key is eval'd into javascript
        * id - is specified by idSrc, and should be in the mapping function but not columns

        additionally the update option can be used to _update the options for any type = 'select', 'selectize'

        * _update - dict with following keys
            * endpoint - url endpoint to retrieve new options 
            * on - event which triggers update. supported events are
                * 'open' - triggered when form opens (actually when field is focused)
                * 'change' - triggered when field changes - use wrapper to indicate what field(s) are updated
            * wrapper - dict which is wrapped around query response. value '_response_' indicates where query response should be placed
    
    **servercolumns** - if present table will be displayed through ajax get calls

    :param pagename: name to be displayed at top of html page
    :param endpoint: endpoint parameter used by flask.url_for()
    :param dbmapping: mapping dict with key for each db field, value is key in form or function(dbentry)
    :param formmapping: mapping dict with key for each form row, value is key in db row or function(form)
    :param writepermission: function to check write permission for api access
    :param dbtable: db model class for table being updated
    :param byclub: True if results are to be limited by club_id
    :param clientcolumns: list of dicts for input to dataTables and Editor
    :param servercolumns: list of ColumnDT for input to sqlalchemy-datatables.DataTables
    :param idSrc: idSrc for use by Editor
    :param buttons: list of buttons for DataTable, from ['create', 'remove', 'edit', 'csv']
    '''

    decorators = [login_required]

    #----------------------------------------------------------------------
    def __init__(self, **kwargs):
    #----------------------------------------------------------------------
        # the args dict has all the defined parameters to 
        # caller supplied keyword args are used to update the defaults
        # all arguments are made into attributes for self
        self.kwargs = kwargs
        args = dict(pagename = None, 
                    endpoint = None, 
                    dbmapping = {}, 
                    formmapping = {}, 
                    writepermission = lambda: False, 
                    dbtable = None, 
                    clientcolumns = None, 
                    servercolumns = None, 
                    byclub = True,        # NOTE: prevents common CrudApi
                    idSrc = 'DT_RowId', 
                    buttons = ['create', 'edit', 'remove', 'csv'])
        args.update(kwargs)        
        for key in args:
            setattr(self, key, args[key])

        # set up mapping between database and editor form
        self.dte = DataTablesEditor(self.dbmapping, self.formmapping)

    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        # create supported endpoints
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}'.format(self.endpoint),view_func=my_view,methods=['GET',])
        app.add_url_rule('/{}/rest'.format(self.endpoint),view_func=my_view,methods=['GET', 'POST'])
        app.add_url_rule('/{}/rest/<int:thisid>'.format(self.endpoint),view_func=my_view,methods=['PUT', 'DELETE'])

    #----------------------------------------------------------------------
    def _renderpage(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            # verify user can write the data, otherwise abort
            if not self.writepermission():
                db.session.rollback()
                flask.abort(403)
            
            # set up parameters to query, based on whether results are limited to club
            queryparms = {}
            if self.byclub:
                queryparms['club_id'] = club_id

            # peel off any _update options
            update_uptions = []
            for column in self.clientcolumns:
                if '_update' in column:
                    update = column['_update']  # convenience alias
                    update['url'] = url_for(update['endpoint']) + '?' + urlencode({'_wrapper':dumps(update['wrapper'])})
                    update['name'] = column['name']
                    update_uptions.append(update)

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [
                    {
                        'data': None,
                        'defaultContent': '',
                        'className': 'select-checkbox',
                        'orderable': False
                    },
                ],
                'select': True,
                'ordering': True,
                'order': [1,'asc']
            }
            for column in self.clientcolumns:
                dt_options['columns'].append(column)

            # build table data
            if self.servercolumns == None:
                dt_options['serverSide'] = False
                dbrecords = self.dbtable.query.filter_by(**queryparms).all()
                tabledata = []
                for dbrecord in dbrecords:
                    thisentry = self.dte.get_response_data(dbrecord)
                    tabledata.append(thisentry)
            else:
                dt_options['serverSide'] = True
                tabledata = '{}/rest'.format(url_for(self.endpoint))

            ed_options = {
                'idSrc': self.idSrc,
                'ajax': {
                    'create': {
                        'type': 'POST',
                        'url':  '{}/rest'.format(url_for(self.endpoint)),
                    },
                    'edit': {
                        'type': 'PUT',
                        'url':  '{}/rest/{}'.format(url_for(self.endpoint),'_id_'),
                    },
                    'remove': {
                        'type': 'DELETE',
                        'url':  '{}/rest/{}'.format(url_for(self.endpoint),'_id_'),
                    },
                },
                
                'fields': [
                ],
            }
            # TODO: these are editor field options as of Editor 1.5.6 -- do we really need to get rid of non-Editor options?
            fieldkeys = ['className', 'data', 'def', 'entityDecode', 'fieldInfo', 'id', 'label', 'labelInfo', 'name', 'type', 'options', 'opts']
            for column in self.clientcolumns:
                # pick keys which matter
                edcolumn = { key: column[key] for key in fieldkeys if key in column}
                ed_options['fields'].append(edcolumn)

            # commit database updates and close transaction
            db.session.commit()

            # render page
            return flask.render_template('datatables.html', 
                                         pagename = self.pagename,
                                         pagejsfiles = addscripts(['datatables.js']),
                                         tabledata = tabledata, 
                                         tablebuttons = self.buttons,
                                         options = {'dtopts': dt_options, 'editoropts': ed_options, 'updateopts': update_uptions},
                                         inhibityear = True,    # NOTE: prevents common CrudApi
                                         writeallowed = self.writepermission())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def _retrieverows(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            # verify user can write the data, otherwise abort
            if not self.writepermission():
                db.session.rollback()
                flask.abort(403)
                
            # set up parameters to query, based on whether results are limited to club
            queryparms = {}
            if self.byclub:
                queryparms['club_id'] = club_id

            # columns to retrieve from database
            columns = self.servercolumns

            # get data from database
            rowTable = DataTables(request.args, self.dbtable, self.dbtable.query.filter_by(**queryparms), columns, dialect='mysql')
            output_result = rowTable.output_result()

            # back to client
            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        if request.path[-4:] != 'rest':
            return self._renderpage()
        else:
            return self._retrieverows()

    #----------------------------------------------------------------------
    @_editormethod(checkaction='create', formrequest=True)
    def post(self):
    #----------------------------------------------------------------------
        # retrieve data from request
        thisdata = self._data[0]
        
        # create item
        dbitem = self.dbtable(**self._dbparms)
        self.dte.set_dbrow(thisdata, dbitem)
        app.logger.debug('creating dbrow={}'.format(dbitem))
        db.session.add(dbitem)
        db.session.flush()

        # prepare response
        thisrow = self.dte.get_response_data(dbitem)
        self._responsedata = [thisrow]


    #----------------------------------------------------------------------
    @_editormethod(checkaction='edit', formrequest=True)
    def put(self, thisid):
    #----------------------------------------------------------------------
        # retrieve data from request
        self._responsedata = []
        thisdata = self._data[thisid]
        
        # edit item
        dbitem = self.dbtable.query.filter_by(id=thisid).first()
        app.logger.debug('editing id={} dbrow={}'.format(thisid, dbitem))
        self.dte.set_dbrow(thisdata, dbitem)
        app.logger.debug('after edit id={} dbrow={}'.format(thisid, dbitem))

        # prepare response
        thisrow = self.dte.get_response_data(dbitem)
        self._responsedata = [thisrow]


    #----------------------------------------------------------------------
    @_editormethod(checkaction='remove', formrequest=False)
    def delete(self, thisid):
    #----------------------------------------------------------------------
        # remove item
        dbitem = self.dbtable.query.filter_by(id=thisid).first()
        app.logger.debug('deleting id={} dbrow={}'.format(thisid, dbitem))
        db.session.delete(dbitem)

        # prepare response
        self._responsedata = []

#----------------------------------------------------------------------
def deepupdate(obj, val, newval):
#----------------------------------------------------------------------
    '''
    recursively searches obj object and replaces any val values with newval
    does not update opj
    returns resultant object
    
    :param obj: object which requires updating
    :param val: val to look for
    :param newval: replacement for val
    '''
    thisobj = deepcopy(obj)

    if type(thisobj) == dict:
        for k in thisobj:
            thisobj[k] = deepupdate(thisobj[k], val, newval)

    elif type(thisobj) == list:
        for k in range(len(thisobj)):
            thisobj[k] = deepupdate(thisobj[k], val, newval)

    else:
        if thisobj == val:
            thisobj = newval

    return thisobj


#######################################################################
class DbQueryApi(MethodView):
#######################################################################
    '''
    class to set up api to get fields from dbtable

    jsonmapping parameter is dict with dbattr indicating the attr to retrieve 
    from dbtable, and jsonkey indicating the key in the json response
    for the returned value.

    a list of {jsonkey: dbattr_value, ...} is returned to the api caller

    url [endpoint]/query is created
    if request has args, the arg=value pairs are treated as a filter into dbtable

    :param endpoint: endpoint parameter used by flask.url_for()
    :param permission: function to check for permission to access this api
    :param byclub: True if table is to be filtered by club_id
    :param dbtable: model class from which query is to be run
    :param jsonmapping: dict {'jsonkey':'dbattr', 'jsonkey':f(dbrow), ...}
    '''

    #----------------------------------------------------------------------
    def __init__(self, **kwargs):
    #----------------------------------------------------------------------

        # the args dict has all the defined parameters to 
        # caller supplied keyword args are used to update the defaults
        # all arguments are made into attributes for self
        self.kwargs = kwargs
        args = dict(
                    endpoint = None,
                    permission = None,
                    byclub = False,
                    dbtable = None,
                    jsonmapping = {},
                   )
        args.update(kwargs)        
        for key in args:
            setattr(self, key, args[key])

        self.convert2json = DataTablesEditor({}, self.jsonmapping)


    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}/query'.format(self.endpoint),view_func=my_view,methods=['POST',])

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        # maybe some filters, maybe club_id required
        filters = request.args.copy()

        # pull of the wrapper if present
        wrapper = filters.pop('_wrapper', None)

        if self.byclub:
            club_id = flask.session['club_id']
            filters['club_id'] = club_id

        # get the data from the table
        dbrows = self.dbtable.query.filter_by(**filters).all()

        # build the response
        response = []
        for dbrow in dbrows:
            responseitem = {}
            responseitem = self.convert2json.get_response_data(dbrow)
            response.append(responseitem)

        # wrap the response, if necessary
        if wrapper:
            pwrapper = loads(wrapper)
            response = deepupdate(pwrapper, '_response_', response)

        return jsonify(response)
