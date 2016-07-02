#!/usr/bin/python
###########################################################################################
# app - define the application 
#
#	Date		Author		Reason
#	----		------		------
#       01/11/14        Lou King        Create
#
#   Copyright 2014 Lou King
#
###########################################################################################
'''
app - define the application
====================================
'''

from . import app, celery

if __name__ == '__main__':
    app.run(debug=True)