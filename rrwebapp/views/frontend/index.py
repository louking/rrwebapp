###########################################################################################
# index - just some boilerplate
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/04/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import smtplib
import urllib.request, urllib.parse, urllib.error

# pypi
import flask
from flask import current_app, request, g
from flask.views import MethodView

# home grown
from . import bp
from ...model import db   # this is ok because this module only runs under flask

# module specific needs
from ... import version

#######################################################################
class ViewIndex(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('index.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
bp.add_url_rule('/',view_func=ViewIndex.as_view('index'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ViewFeatures(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('features.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
bp.add_url_rule('/features',view_func=ViewFeatures.as_view('features'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ViewTerms(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('tos.html',addfooter=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
bp.add_url_rule('/termsofservice',view_func=ViewTerms.as_view('terms'),methods=['GET'])
#----------------------------------------------------------------------
