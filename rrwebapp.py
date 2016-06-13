###########################################################################################
# run the web application from mod_wsgi
#
#       Date            Author          Reason
#       ----            ------          ------
#       06/11/16        Lou King        Create
#
#   Copyright 2013 Lou King
###########################################################################################

from flask import Flask
import os.path

from rrwebapp import app

if __name__ == "__main__":
    app.run()