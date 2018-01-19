###########################################################################################
# datatables_utils
#
#       Date            Author          Reason
#       ----            ------          ------
#       02/08/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
###########################################################################################

# standard
from collections import defaultdict
from csv import DictReader

# pypi
import flask
from flask.views import MethodView
from flask_login import login_required

# homegrown
from . import app
from database_flask import db   # this is ok because this module only runs under flask
from request import addscripts
from loutilities.transform import Transform

class ParameterError(Exception): pass;

#----------------------------------------------------------------------
def dt_editor_response(**respargs):
#----------------------------------------------------------------------
    '''
    build response for datatables editor
    
    :param respargs: arguments for response
    :rtype: json response
    '''

    return flask.jsonify(**respargs)


#----------------------------------------------------------------------
def get_request_action(form):
#----------------------------------------------------------------------
    # TODO: modify get_request_action and get_request_data to allow either request object or form object, 
    # and remove if/else for formrequest, e.g., action = get_request_action(request)
    # (allowing form object deprecated for legacy code)
    '''
    return dict list with data from request.form

    :param form: MultiDict from `request.form`
    :rtype: action - 'create', 'edit', or 'remove'
    '''
    return form['action']

#----------------------------------------------------------------------
def get_request_data(form):
#----------------------------------------------------------------------
    # TODO: modify get_request_action and get_request_data to allow either request object or form object, 
    # and remove if/else for formrequest, e.g., action = get_request_action(request)
    # (allowing form object deprecated for legacy code)
    '''
    return dict list with data from request.form

    :param form: MultiDict from `request.form`
    :rtype: {id1: {field1:val1, ...}, ...} [fieldn and valn are strings]
    '''

    # request.form comes in multidict [('data[id][field]',value), ...]
    
    # fill in id field automatically
    data = defaultdict(lambda: {})

    # fill in data[id][field] = value
    for formkey in form.keys():
        if formkey == 'action': continue
        datapart,idpart,fieldpart = formkey.split('[')
        if datapart != 'data': raise ParameterError, "invalid input in request: {}".format(formkey)

        idvalue = int(idpart[0:-1])
        fieldname = fieldpart[0:-1]

        data[idvalue][fieldname] = form[formkey]

    # return decoded result
    return data

#----------------------------------------------------------------------
def getDataTableParams(updates, printerfriendly = False):
#----------------------------------------------------------------------

    sDomValue = '<"H"lBpfr>t<"F"i>'
    sPrinterFriendlyDomValue = 'lpfrt'

    if not printerfriendly:
        params = {
                'dom': sDomValue,
                'jQueryUI': True,
                'paging': False,
                # 'scrollY': gettableheight(),  # can't call js from here
                'scrollCollapse': True,
                'buttons': [],
                # responsive: True,    # causes + button on left, which is not user friendly
                'scrollX': True,
                'scrollXInner': "100%",
                }

    else:
        params = {
                'dom': sPrinterFriendlyDomValue,
                'jQueryUI': True,
                'paging': False,
                'ordering': False,
                'scrollCollapse': True,
                }

    params.update(updates)
    return params
    


###########################################################################################
class DataTablesEditor():
###########################################################################################
    '''
    handle CRUD request from dataTables Editor

    dbmapping is dict like {'dbattr_n':'formfield_n', 'dbattr_m':f(form), ...}
    formmapping is dict like {'formfield_n':'dbattr_n', 'formfield_m':f(dbrow), ...}
    if order of operation is importand use OrderedDict

    :param dbmapping: mapping dict with key for each db field, value is key in form or function(dbentry)
    :param formmapping: mapping dict with key for each form row, value is key in db row or function(form)
    '''

    #----------------------------------------------------------------------
    def __init__(self, dbmapping, formmapping):
    #----------------------------------------------------------------------
        self.dbmapping = dbmapping
        self.formmapping = formmapping

    #----------------------------------------------------------------------
    def get_response_data(self, dbentry):
    #----------------------------------------------------------------------
        '''
        set form values based on database model object

        :param dbentry: database entry (model object)
        '''

        data = {}

        # create data fields based on formmapping
        for key in self.formmapping:
            # call the function to fill data[key]
            if hasattr(self.formmapping[key], '__call__'):
                callback = self.formmapping[key]
                data[key] = callback(dbentry)
            
            # simple map from dbentry field
            else:
                dbattr = self.formmapping[key]
                data[key] = getattr(dbentry, dbattr)

        return data

    #----------------------------------------------------------------------
    def set_dbrow(self, inrow, dbrow):
    #----------------------------------------------------------------------
        '''
        update database entry from form entry

        :param inrow: input row
        :param dbrow: database entry (model object)
        '''

        for dbattr in self.dbmapping:
            # call the function to fill dbrow.<dbattr>
            if hasattr(self.dbmapping[dbattr], '__call__'):
                callback = self.dbmapping[dbattr]
                setattr(dbrow, dbattr, callback(inrow))

            # simple map from inrow field
            else:
                key = self.dbmapping[dbattr]
                if key in inrow:
                    setattr(dbrow, dbattr, inrow[key])
                else:
                    # ignore -- leave dbrow unchanged for this dbattr
                    pass


#######################################################################
class DatatablesCsv(MethodView):
#######################################################################
    '''
    provides render for csv file as dataTables table

    usage:
        instancename = DatatablesCsv([arguments]):
        instancename.register()

    **columns** should be like the following. See https://datatables.net/reference/option/columns and 
    https://editor.datatables.net/reference/option/fields for more information

        [
            { 'data': 'name', 'name': 'name', 'label': 'Service Name' },
            { 'data': 'key', 'name': 'key', 'label': 'Key' }, 
            { 'data': 'secret', 'name': 'secret', 'label': 'Secret', 'render':'$.fn.dataTable.render.text()' },
        ]

        * name - describes the column and is used within javascript
        * data - used on server-client interface 
        * label - used for the DataTable table column. CSV file headers must match this
        * optional render key is eval'd into javascript
    
    :param pagename: name to be displayed at top of html page
    :param endpoint: endpoint parameter used by flask.url_for()
    :param csvfile: csv file path, or function to retrieve path of csv file which contains data
    :param readpermission: function to check write permission for page access
    :param columns: list of dicts for input to dataTables, or function to get this list
    :param buttons: list of buttons for DataTable
    '''

    #----------------------------------------------------------------------
    def __init__(self, **kwargs):
    #----------------------------------------------------------------------
        # the args dict has all the defined parameters to 
        # caller supplied keyword args are used to update the defaults
        # all arguments are made into attributes for self
        self.kwargs = kwargs
        args = dict(pagename = None, 
                    endpoint = None, 
                    dtoptions = {},
                    csvfile = None,
                    readpermission = lambda: False, 
                    columns = None, 
                    buttons = ['csv'])
        args.update(kwargs)        
        for key in args:
            setattr(self, key, args[key])

    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        # create supported endpoints
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}'.format(self.endpoint),view_func=my_view,methods=['GET',])

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # verify user can read the data, otherwise abort
            if not self.readpermission():
                db.session.rollback()
                flask.abort(403)
            
            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [],
                'ordering': True,
                'serverSide': False,
            }
            dt_options.update(self.dtoptions)

            # set up columns
            if hasattr(self.columns, '__call__'):
                columns = self.columns()
            else:
                columns = self.columns
            for column in columns:
                dt_options['columns'].append(column)

            # set up buttons
            if hasattr(self.buttons, '__call__'):
                buttons = self.buttons()
            else:
                buttons = self.buttons

            # set up column transformation from header items to data items
            mapping = { c['data']:c['label'] for c in columns }
            headers2data = Transform(mapping, sourceattr=False, targetattr=False)

            # build table data
            if hasattr(self.csvfile, '__call__'):
                csvfile = self.csvfile()
            else:
                csvfile = self.csvfile
            with open(csvfile, 'rb') as _CSV:
                tabledata = []
                CSV = DictReader(_CSV)
                for csvrow in CSV:
                    datarow = {}
                    headers2data.transform(csvrow, datarow)
                    tabledata.append(datarow)

            # commit database updates and close transaction
            db.session.commit()

            # render page
            return flask.render_template('datatables.html', 
                                         pagename = self.pagename,
                                         pagejsfiles = addscripts(['datatables.js', 'buttons.colvis.js']),
                                         tabledata = tabledata, 
                                         tablebuttons = buttons,
                                         options = {'dtopts': dt_options},
                                         inhibityear = True,    # NOTE: prevents common DatatablesCsv
                                        )
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise


#######################################################################
class AdminDatatablesCsv(DatatablesCsv):
#######################################################################
    decorators = [login_required]


