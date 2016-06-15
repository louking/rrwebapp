###########################################################################################
#       Date            Author          Reason
#       ----            ------          ------
#       06/15/16        Lou King        Create
#
#   from http://stackoverflow.com/questions/14048779/with-flask-how-can-i-serve-robots-txt-and-sitemap-xml-as-static-files
#   Copyright 2016 Lou King
###########################################################################################

from flask import Flask, request, send_from_directory
from app import app

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])