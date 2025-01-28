#!/usr/bin/python
###########################################################################################
# userpw - userpw support for running club web app
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/05/13        Lou King        Create
#
#   Copyright 2013 Lou King
#
###########################################################################################
'''
userpw - userpw support for running club web app
===================================================================

methods to access /api/userpw webapp methods - see :mod:`userpwapp`
'''

# standard
import datetime
import urllib.request, urllib.parse, urllib.error
import json
import binascii

# pypi
import httplib2

# home grown
import config
from config import accessError,CF,SECCF,OPTUSERPWAPI

HTTPTIMEOUT = 5
HTTP = httplib2.Http(timeout=HTTPTIMEOUT)

###########################################################################################
class UserPw():
###########################################################################################
    '''
    access /api/userpw within runningclub webapp
    
    :param apiurl: url for webapp api
    '''

    #----------------------------------------------------------------------
    def __init__(self,apiurl):
    #----------------------------------------------------------------------
        #APIURL = 'http://localhost:9080/api/userpw/'
        self.apiurl = apiurl
        
    #----------------------------------------------------------------------
    def _setattr(self,runningclub,username,method,attr=None,value=None):
    #----------------------------------------------------------------------
        '''
        sets single attribute under userpw
        
        :param runningclub: abbreviated name of running club
        :param username: user name for which attr should be set (or None)
        :param method: api method name
        :param attr: name of attribute
        :param value: value to be set to attribute
        '''
    
        if attr:
            params = {'runningclub':runningclub,
                      'username':username,
                      attr:value}
        else:
            params = {'runningclub':runningclub,
                      'username':username}
        
        # remove username if not needed (createrunningclub does this)
        if not username:
            params.pop('username')
            
        url = self.apiurl+'{method}?{params}'.format(method=method,params=urllib.parse.urlencode(params))
        resp,jsoncontent = HTTP.request(url,method='POST',headers={'content-length':'0'})
    
        if resp.status != 200:
            raise accessError('URL response status = {}, req=POST {}'.format(resp.status,url))
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
    
        if content['status'] != 'OK':
            raise accessError('URL content status = {}, req=POST {}'.format(content['status'],url))
        
    #----------------------------------------------------------------------
    def _getattr(self,runningclub,username,method,attr):
    #----------------------------------------------------------------------
        '''
        sets single attribute under userpw
        
        :param runningclub: abbreviated name of running club
        :param username: user name for which attr should be set
        :param attr: name of attribute
        '''
    
        params = {'runningclub':runningclub,
                  'username':username}
            
        url = self.apiurl+'{method}?{params}'.format(method=method,params=urllib.parse.urlencode(params))
        resp,jsoncontent = HTTP.request(url,method='GET',headers={'content-length':'0'})
    
        if resp.status != 200:
            raise accessError('URL response status = {}, req=GET {}'.format(resp.status,url))
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
    
        if content['status'] != 'OK':
            raise accessError('URL content status = {}, req=GET {}'.format(content['status',url]))
        
        return content[attr]
        
    #----------------------------------------------------------------------
    def createrunningclub(self,runningclub,email=None):
    #----------------------------------------------------------------------
        '''
        create user in userpw database
        '''
        
        # skip user parameter
        self._setattr(runningclub,None,'createrunningclub','email',email)   
    
    #----------------------------------------------------------------------
    def createuser(self,runningclub,username):
    #----------------------------------------------------------------------
        '''
        create user in userpw database
        '''
        
        self._setattr(runningclub,username,'createuser')
    
    #----------------------------------------------------------------------
    def updateemail(self,runningclub,username,email):
    #----------------------------------------------------------------------
        '''
        update user email in userpw database
        '''
        
        self._setattr(runningclub,username,'updateemail','email',email)
    
    #----------------------------------------------------------------------
    def updatekey(self,runningclub,username,publickey):
    #----------------------------------------------------------------------
        '''
        update user publickey in userpw database
        '''
        
        self._setattr(runningclub,username,'updatekey','publickey',publickey)
    
    #----------------------------------------------------------------------
    def updateencryptedpw(self,runningclub,username,encrypteddbpassword):
    #----------------------------------------------------------------------
        '''
        update user encrypteddbpassword in userpw database
        '''
        
        passwordtext = binascii.hexlify(encrypteddbpassword)
        self._setattr(runningclub,username,'updatepw','encrypteddbpassword',passwordtext)
    
    #----------------------------------------------------------------------
    def getpublickey(self,runningclub,username):
    #----------------------------------------------------------------------
        '''
        retrieve user publickey from userpw database
        '''
        
        return self._getattr(runningclub,username,'getkey','publickey')

    #----------------------------------------------------------------------
    def getencryptedpw(self,runningclub,username):
    #----------------------------------------------------------------------
        '''
        retrieve user encrypteddbpassword from userpw database
        '''
        
        passwordtext = self._getattr(runningclub,username,'getpw','encrypteddbpassword')
        return binascii.unhexlify(passwordtext)

