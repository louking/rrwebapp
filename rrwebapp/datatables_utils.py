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

# pypi
import flask
from . import app

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



