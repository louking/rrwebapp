###########################################################################################
# apicommon - helper functions for api building
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/17/14        Lou King        Create
#
#   Copyright 2014 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
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

    #respargs.update({'success':True})
    #response = make_response(json.dumps(respargs))
    #response.content_type = 'application/json'
    return flask.jsonify(success=True,**respargs)

#----------------------------------------------------------------------
def failure_response(**respargs):
#----------------------------------------------------------------------
    '''
    build failure response for API
    
    :param respargs: arguments for response
    :rtype: json response
    '''

    #respargs.update({'success':False})
    #response = make_response(json.dumps(respargs))
    #response.content_type = 'application/json'
    return flask.jsonify(success=False,**respargs)
