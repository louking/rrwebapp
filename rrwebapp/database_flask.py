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
###########################################################################################
'''
webdatabase  -- access to database for flask web application
=================================================================

'''

# standard
import pdb
import os.path
from ConfigParser import SafeConfigParser

# pypi
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

# github

# other

# home grown
from rrwebapp import app
#app = Flask('rrwebapp')

# build database name, details kept in apikey database
# get configuration
thisdir = os.path.dirname(__file__)
sep = os.path.sep
configdir = sep.join(thisdir.split(sep)[:-2])
configpath = os.path.join(configdir, 'rrwebapp.cfg')
config = SafeConfigParser()
config.readfp(open(configpath))

dbuser = config.get('database', 'dbuser')
password = config.get('database', 'dbpassword')
dbserver = config.get('database', 'dbserver')
dbname = config.get('database', 'dbname')
app.logger.debug('using mysql://{uname}:*******@{server}/{dbname}'.format(uname=dbuser,server=dbserver,dbname=dbname))

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

## db close session is done whenever app tears down
## TODO: was lack of this causing Operation Error on godaddy.com?
#@app.teardown_appcontext
##----------------------------------------------------------------------
#def shutdown_session(exception=None):
##----------------------------------------------------------------------
#    db.session.close()    

