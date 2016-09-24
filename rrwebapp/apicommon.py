###########################################################################################
# apicommon - helper functions for api building
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/17/14        Lou King        Create
#
#   Copyright 2014 Lou King
#
###########################################################################################
'''
apicommon - helper functions for api building
==================================================
'''

# standard

# pypi
import flask

#----------------------------------------------------------------------
def success_response(**respargs):
#----------------------------------------------------------------------
    '''
    build success response for API
    
    :param respargs: arguments for response
    :rtype: json response
    '''

    return flask.jsonify(success=True,**respargs)

#----------------------------------------------------------------------
def failure_response(**respargs):
#----------------------------------------------------------------------
    '''
    build failure response for API
    
    :param respargs: arguments for response
    :rtype: json response
    '''

    return flask.jsonify(success=False,**respargs)

#----------------------------------------------------------------------
def check_header(requiredfields, headerfields):
#----------------------------------------------------------------------
    '''
    verify all the fields in requiredfields are in the csv header

    :param requiredfields: list with fields which are required to be in the csv file
    :param headerfields: list of fields in header
    :rtype: boolean - True means header is ok, False otherwise
    '''

    # each requiredfield must be in the csv header
    for requiredfield in requiredfields:
        if requiredfield not in headerfields:
            return False

    # didn't find any problems
    return True

#######################################################################
class MapDict():
#######################################################################
    '''
    convert dict d to new dict based on mapping
    mapping is dict like {'outkey_n':'inkey_n', 'outkey_m':f(dbrow), ...}

    :param mapping: mapping dict with key for each output field
    '''

    #----------------------------------------------------------------------
    def __init__(self,mapping):
    #----------------------------------------------------------------------
        self.mapping = mapping

    #----------------------------------------------------------------------
    def convert(self,from_dict):
    #----------------------------------------------------------------------
        '''
        convert dict d to new dict based on mapping

        :param from_dict: dict-like object
        :param mapping: dict with keys like {'to1':'from1', ...}
        :rtype: object of same type as from_dict, with the converted keys
        '''

        # create intance of correct type
        to_dict = type(from_dict)()

        # go through keys, skipping the ones which are not present
        for to_key in self.mapping:
            if hasattr(self.mapping[to_key], '__call__'):
                callback = self.mapping[to_key]
                to_dict[to_key] = callback(from_dict)

            # simple map from from_dict field
            else:
                from_key = self.mapping[to_key]
                if from_key in from_dict:
                    to_dict[to_key] = from_dict[from_key]

        return to_dict

