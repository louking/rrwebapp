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
from urllib.parse import urlencode

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask_login import login_required
from flask.views import MethodView
from .datatables_utils import DataTablesEditor, dt_editor_response, get_request_action, get_request_data

# homegrown
from . import app
from .database_flask import db   # this is ok because this module only runs under flask
from .request import addscripts
from loutilities.tables import DbCrudApi
from .accesscontrol import UpdateClubDataPermission, ViewClubDataPermission

class parameterError(Exception): pass

#----------------------------------------------------------------------
def _editormethod(checkaction='', formrequest=True):
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
class CrudApi(DbCrudApi):
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
    :param queryparams: dict of query parameters relevant to this table to retrieve table or rows
    :param byclub: True if results are to be limited by club_id
    :param clientcolumns: list of dicts for input to dataTables and Editor
    :param servercolumns: list of ColumnDT for input to sqlalchemy-datatables.DataTables
    :param idSrc: idSrc for use by Editor
    :param buttons: list of buttons for DataTable, from ['create', 'remove', 'edit', 'csv']
    :param pagejsfiles: list of javascript files to be included at end
    :param pagecssfiles: list of css files to be included at end
    :param dtoptions: datatables options to override / add
    '''

    decorators = [login_required]

    #----------------------------------------------------------------------
    def __init__(self, **kwargs):
        # the args dict has all the defined parameters to
        # caller supplied keyword args are used to update the defaults
        # all arguments are made into attributes for self
        self.kwargs = kwargs
        args = dict(db = None,
                    app = None,
                    model = None,
                    pagename = None,
                    endpoint = None, 
                    dbmapping = {}, 
                    formmapping = {}, 
                    writepermission = lambda: False,
                    permission = None,
                    dbtable = None, 
                    queryparams = {},
                    clientcolumns = None, 
                    byclub = True,
                    byyear = False,
                    idSrc = 'DT_RowId', 
                    buttons = ['create', 'edit', 'remove', 'csv'],
                    pagejsfiles = [],
                    pagecssfiles = [],
                    dtoptions = {},
                    addltemplateargs = {'inhibityear':True}
                    )

        # update defaults with kwargs from caller
        args.update(kwargs)

        # legacy support: initialize a couple of arguments required by inherited class
        if not args['db']:
            args['db'] = db
        if not args['app']:
            args['app'] = app
        if not args['model']:
            args['model'] = args['dbtable']
        if not args['permission']:
            args['permission'] = args['writepermission']

        # initialize inherited class, and a couple of attributes
        super(CrudApi, self).__init__(**args)

    #----------------------------------------------------------------------
    def beforequery(self):
        if self.byclub:
            self.queryparams['club_id'] = flask.session['club_id']
        if self.byyear:
            self.queryparams['year'] = flask.session['year']

    #----------------------------------------------------------------------
    def _renderpage(self):
        self._club_id = flask.session['club_id']
        return super(CrudApi, self)._renderpage()

    #----------------------------------------------------------------------
    def _retrieverows(self):
        self._club_id = flask.session['club_id']
        return super(CrudApi, self)._retrieverows()

#----------------------------------------------------------------------
def deepupdate(obj, val, newval):
    '''
    recursively searches obj object and replaces any val values with newval
    does not update opj
    returns resultant object
    
    :param obj: object which requires updating
    :param val: val to look for
    :param newval: replacement for val
    '''
    thisobj = deepcopy(obj)

    if isinstance(thisobj, dict):
        for k in thisobj:
            thisobj[k] = deepupdate(thisobj[k], val, newval)

    elif isinstance(thisobj, list):
        for k in range(len(thisobj)):
            thisobj[k] = deepupdate(thisobj[k], val, newval)

    else:
        if thisobj == val:
            thisobj = newval

    return thisobj


#######################################################################
class DbQueryApi(MethodView):
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
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}/query'.format(self.endpoint),view_func=my_view,methods=['POST',])

    #----------------------------------------------------------------------
    def post(self):
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
