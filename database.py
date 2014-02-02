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