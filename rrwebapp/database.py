#!/usr/bin/python
###########################################################################################
# database  -- access to database 
#
#	Date		Author		Reason
#	----		------		------
#       01/07/14        Lou King        Create
#
#   Copyright 2014 Lou King
#
###########################################################################################
'''
database  -- access to database
====================================
'''

# standard
import os

# choose which database type to use and expose appropriate variables, classes, methods

if os.getenv('USEFLASK'):
    from rrwebapp.database_flask import *
else:
    from database_script         import *

__all__ = ('setracedb,Base,Session,Table,Column,Integer,Float,Boolean,String,Date,Sequence,Enum,' 
            + 'UniqueConstraint,ForeignKey,metadata,object_mapper,relationship,backref').split(',')