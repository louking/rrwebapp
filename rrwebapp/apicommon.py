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
