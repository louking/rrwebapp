###########################################################################################
# result - result views for result results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/01/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import time

# pypi
import flask
from flask import make_response,request
from flask_login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import app
from .accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from .model import db   # this is ok because this module only runs under flask
from .apicommon import failure_response, success_response
from .forms import ExportResultsForm
from loutilities import timeu
from .exportresults import collectresults

# module specific needs
import os.path
from .member import normalizeRAmemberlist

#----------------------------------------------------------------------
def allowed_file(filename):
#----------------------------------------------------------------------
    return '.' in filename and filename.split('.')[-1] in ['csv']

#######################################################################
class FormatMemberlist(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('normalizememberlist.html',pagename='Normalize Memberlist')
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            expdate = flask.request.args.get('expdate',None)
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # get file extention
            requestfile = request.files['file']
            root,ext = os.path.splitext(requestfile.filename)
            
            # make sure valid file
            if not requestfile:
                db.session.rollback()
                cause = 'Unexpected Error: Missing file'
                flask.flash(cause)
                return flask.redirect(flask.url_for('normalizememberlist'))
            if not allowed_file(requestfile.filename):
                db.session.rollback()
                cause = 'Invalid file type {} for file {}'.format(ext,requestfile.filename)
                flask.flash(cause)
                return flask.redirect(flask.url_for('normalizememberlist'))

            # return normalized multiple record inputfile
            response = make_response(normalizeRAmemberlist(requestfile.stream,filterexpdate=expdate))
            response.headers["Content-Disposition"] = "attachment; filename={}-normalized{}".format(root,ext)
            
            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/tool/normalizememberlist',view_func=FormatMemberlist.as_view('normalizememberlist'),methods=['GET','POST'])
#----------------------------------------------------------------------

#######################################################################
class ExportResults(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)

            form = ExportResultsForm()

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('exportresults.html',form=form, pagename='Export Results')
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']

            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)

            # specify the form
            form = ExportResultsForm()

            # this should not fire if date fields are StringField
            if not form.validate():
                flask.flash('Dates must be formatted as yyyy-mm-dd')
                db.session.rollback()
                return flask.render_template('exportresults.html', form=form, pagename='Export Results')

            # check date validity
            ddymd = timeu.asctime('%Y-%m-%d')
            try:
                if form.start.data:
                    temp = ddymd.asc2dt(form.start.data)
                    form.start.data = ddymd.dt2asc(temp)    # normalize format
                if form.end.data:
                    temp = ddymd.asc2dt(form.end.data)
                    form.end.data = ddymd.dt2asc(temp)    # normalize format
            except ValueError:
                flask.flash('Dates must be formatted as yyyy-mm-dd')
                db.session.rollback()
                return flask.render_template('exportresults.html', form=form, pagename='Export Results')
            
            # return results
            today = ddymd.epoch2asc(time.time())
            response = make_response(collectresults(club_id, begindate=form.start.data, enddate=form.end.data))
            response.headers["Content-Disposition"] = "attachment; filename=clubresults-{}.csv".format(today)
            
            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/tool/exportresults',view_func=ExportResults.as_view('exportresults'),methods=['GET','POST'])
#----------------------------------------------------------------------

