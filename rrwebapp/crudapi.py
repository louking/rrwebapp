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

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask.ext.login import login_required
from flask.views import MethodView
from datatables import DataTables, ColumnDT
from datatables_editor import DataTablesEditor, dt_editor_response, get_request_action, get_request_data

# homegrown
from . import app
from database_flask import db   # this is ok because this module only runs under flask
from request import addscripts

#######################################################################
class CrudApi(MethodView):
#######################################################################
    '''
    provides initial render and RESTful CRUD api

    usage:
        instancename = CrudApi([arguments]):
        instancename.register()

    dbmapping is dict like {'dbattr_n':'formfield_n', 'dbattr_m':f(form), ...}
    formmapping is dict like {'formfield_n':'dbattr_n', 'formfield_m':f(dbrow), ...}
    if order of operation is importand use OrderedDict

    clientcolumns should be like the following. See https://datatables.net/reference/option/columns and 
    https://editor.datatables.net/reference/option/fields for more information

        [
            { 'data': 'name', 'name': 'name', 'label': 'Service Name' },
            { 'data': 'key', 'name': 'key', 'label': 'Key', 'render':'$.fn.dataTable.render.text()' }, 
            { 'data': 'secret', 'name': 'secret', 'label': 'Secret', 'render':'$.fn.dataTable.render.text()' },
        ]

    * name - describes the column and is used within javascript
    * data - used on server-client interface and should be used in the formmapping key and dbmapping value
    * label - used for the DataTable table column and the Editor form label 
    * optional render key is eval'd into javascript
    * id - is specified by idSrc, and should be in the mapping function but not columns
    
    servercolumns - if present table will be displayed through ajax get calls

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
        app.logger.debug('CrudApi object = {}'.format(self))

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

        self.pagename = args['pagename']
        self.endpoint = args['endpoint']
        self.writepermission = args['writepermission']
        self.dbtable = args['dbtable']
        self.byclub = args['byclub']
        self.clientcolumns = args['clientcolumns']
        self.servercolumns = args['servercolumns']
        self.idSrc = args['idSrc']
        self.buttons = args['buttons']

        # set up mapping between database and editor form
        self.dte = DataTablesEditor(args['dbmapping'], args['formmapping'])

        app.logger.debug('endpoint={}'.format(self.endpoint))

    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        # create supported endpoints
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}'.format(self.endpoint),view_func=self.renderpage,methods=['GET',])
        app.add_url_rule('/{}/rest'.format(self.endpoint),view_func=my_view,methods=['GET', 'POST'])
        app.add_url_rule('/{}/rest/<int:thisid>'.format(self.endpoint),view_func=my_view,methods=['PUT', 'DELETE'])
        # makes url_for include /rest

    #----------------------------------------------------------------------
    def renderpage(self):
    #----------------------------------------------------------------------
        app.logger.debug('CrudApi object = {}'.format(self))

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

            # build table data
            if self.servercolumns == None:
                dbrecords = self.dbtable.query.all(**queryparms)
                tabledata = []
                for dbrecord in dbrecords:
                    thisentry = self.dte.get_response_data(dbrecord)
                    tabledata.append(thisentry)
            else:
                tabledata = url_rule('/{}/rest'.format(self.endpoint))

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

            app.logger.debug('self.endpoint={} url_for(self.endpoint)={}'.format(self.endpoint, url_for(self.endpoint)))
            ed_options = {
                'idSrc': self.idSrc,
                'ajax': {
                    'create': {
                        'type': 'POST',
                        'url':  '{}'.format(url_for(self.endpoint)),
                    },
                    'edit': {
                        'type': 'PUT',
                        'url':  '{}/{}'.format(url_for(self.endpoint),'_id_'),
                    },
                    'remove': {
                        'type': 'DELETE',
                        'url':  '{}/{}'.format(url_for(self.endpoint),'_id_'),
                    },
                },
                
                'fields': [
                ],
            }
            for column in self.clientcolumns:
                # pick keys which matter
                edcolumn = { key: column[key] for key in ['name', 'label']}
                ed_options['fields'].append(edcolumn)
            app.logger.debug(ed_options)

            # commit database updates and close transaction
            db.session.commit()

            # render page
            return flask.render_template('datatables.html', 
                                         pagename = self.pagename,
                                         pagejsfiles = addscripts(['datatables.js']),
                                         tabledata = tabledata, 
                                         tablebuttons = self.buttons,
                                         options = {'dtopts': dt_options, 'editoropts': ed_options},
                                         inhibityear = True,    # NOTE: prevents common CrudApi
                                         writeallowed = self.writepermission())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def get(self):
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
            rowTable = DataTables(request.args, self.dbtable, self.dbtable.query.filter_by(queryparms), columns, dialect='mysql')
            output_result = rowTable.output_result()

            # back to client
            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def _editormethod(self, methodcore, checkaction='', formrequest=True):
    #----------------------------------------------------------------------
        '''
        decorator for CrudApi methods used by Editor

        :param methodcore: function() containing core of method to execute
        :param checkaction: Editor name of action which is used by the decorated method, one of 'create', 'edit', 'remove' or '' if no check required
        :param formrequest: True if request action, data is in form (False for 'remove' action)
        '''
        # see http://python-3-patterns-idioms-test.readthedocs.io/en/latest/PythonDecorators.html
        # def wrap(f):
        #     def wrapped_f(self, *args):
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
            methodcore()

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
        #     return wrapped_f
        # return wrap

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        app.logger.debug('CrudApi object = {}'.format(self))

        def methodcore():
            # retrieve data from request
            thisdata = self._data[0]
            
            # create item
            dbitem = self.dbtable(self._dbparms)
            self.dte.set_dbrow(thisdata, dbitem)
            app.logger.debug('creating dbrow={}'.format(dbitem))
            db.session.add(dbitem)
            db.session.flush()

            # prepare response
            thisrow = self.dte.get_response_data(dbitem)
            self._responsedata = [thisrow]

        return self._editormethod(methodcore, checkaction='create', formrequest=True)



    #----------------------------------------------------------------------
    def put(self, thisid):
    #----------------------------------------------------------------------
        app.logger.debug('CrudApi object = {}'.format(self))

        def methodcore():
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

        return self._editormethod(methodcore, checkaction='edit', formrequest=True)

    #----------------------------------------------------------------------
    def delete(self, thisid):
    #----------------------------------------------------------------------
        def methodcore():
            # remove item
            dbitem = self.dbtable.query.filter_by(id=thisid).first()
            app.logger.debug('deleting id={} dbrow={}'.format(thisid, dbitem))
            db.session.delete(dbitem)

            # prepare response
            self._responsedata = []

        return self._editormethod(methodcore, checkaction='remove', formrequest=False)
