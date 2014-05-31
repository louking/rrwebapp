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

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
import os.path
from member import normalizeRAmemberlist

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

