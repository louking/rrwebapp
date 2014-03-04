#!/usr/bin/python
###########################################################################################
# webdatabase  -- access to database for flask web application
#
#	Date		Author		Reason
#	----		------		------
#       01/07/14        Lou King        Create
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
webdatabase  -- access to database for flask web application
=================================================================

'''

# standard
import pdb

# pypi
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

# github

# other

# home grown
from loutilities import apikey
from app import app
#app = Flask('rrwebapp')

# build database name, details kept in apikey database
ak = apikey.ApiKey('Lou King','raceresultswebapp')
dbuser = ak.getkey('dbuser')
password = ak.getkey('dbpassword')
dbserver = ak.getkey('dbserver')
dbname = ak.getkey('dbname')
print 'using mysql://{uname}:*******@{server}/{dbname}'.format(uname=dbuser,server=dbserver,dbname=dbname)

# temp test code
#dbuser = 'testuser'
#password = 'testuserpw'
#dbserver = '127.0.0.1'
#dbname = 'testdemo'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{uname}:{pw}@{server}/{dbname}'.format(uname=dbuser,pw=password,server=dbserver,dbname=dbname)
#app.config['SQLALCHEMY_POOL_RECYCLE'] = 3200  # try to fix "MySQL server has gone away" error

db = SQLAlchemy(app)
Table = db.Table
Column = db.Column
Integer = db.Integer
Float = db.Float
Boolean = db.Boolean
String = db.String
Date = db.Date
Sequence = db.Sequence
Enum = db.Enum
UniqueConstraint = db.UniqueConstraint
ForeignKey = db.ForeignKey
relationship = db.relationship
backref = db.backref
object_mapper = db.object_mapper
Base = db.Model
metadata = db.metadata

Session = None
setracedb = None

#----------------------------------------------------------------------
def setracedb(dbfilename=None):
#----------------------------------------------------------------------
# for compatibility with database_script module
    '''
    initialize race database
    
    :params dbfilename: filename for race database, if None get from configuration
    '''
    pass