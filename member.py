###########################################################################################
#member - member views for member results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/01/14        Lou King        Create
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

# standard
import json
import csv

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
from racedb import Runner, Club
from forms import MemberForm 
#from runningclub import memberfile   # required for xlsx support
from loutilities.csvu import DictReaderStr2Num

#######################################################################
class ManageMembers(MethodView):
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
                
            form = MemberForm()
    
            members = []
            # TODO: if thisyear is not current year, need to look at expirationdate and renewdate, not active (issue #8)
            members = Runner.query.filter_by(club_id=club_id,active=True).order_by('name').all()
    
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('managemembers.html',form=form,members=members,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/managemembers',view_func=ManageMembers.as_view('managemembers'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class MemberSettings(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,memberid):
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
                
            # memberid == 0 means add
            if memberid == 0:
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                member = Runner(club_id)
                form = MemberForm()
                action = 'Add'
                pagename = 'Add Member'
            
            # memberid != 0 means update
            else:
                member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
    
                # copy source attributes to form
                params = {}
                for field in vars(member):
                    params[field] = getattr(member,field)
                
                form = MemberForm(**params)
                action = 'Update'
                pagename = 'Edit Member'
    
            # commit database updates and close transaction
            db.session.commit()
            # delete button only for edit (memberid != 0)
            return flask.render_template('membersettings.html',thispagename=pagename,
                                         action=action,deletebutton=(memberid!=0),
                                         form=form,member=member,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,memberid):
    #----------------------------------------------------------------------
        form = MemberForm()

        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            # handle Cancel
            if request.form['whichbutton'] == 'Cancel':
                db.session.rollback() # throw out any changes which have been made
                return flask.redirect(flask.url_for('managemembers'))
    
            # handle Delete
            elif request.form['whichbutton'] == 'Delete':
                member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
                # db.session.delete(member)   # should we allow member deletion?  maybe not
                member.active = False

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('managemembers'))

            # handle Update and Add
            elif request.form['whichbutton'] in ['Update','Add']:
                if not form.validate_on_submit():
                    return 'error occurred on form submit -- update error message and display form again'
                    
                readcheck = ViewClubDataPermission(club_id)
                writecheck = UpdateClubDataPermission(club_id)
                
                # verify user can at write the data, otherwise abort
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                
                # add
                if request.form['whichbutton'] == 'Add':
                    member = Runner(club_id)
                # update
                else:
                    member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
                
                # copy fields from form to db object
                for field in vars(member):
                    # only copy attributes which are in the form class already
                    if field in form.data:
                        setattr(member,field,form.data[field])
                
                # add
                if request.form['whichbutton'] == 'Add':
                    db.session.add(member)
                    db.session.flush()  # needed to update member.id
                    memberid = member.id    # not needed yet, but here for consistency

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('managemembers'))
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/membersettings/<int:memberid>',view_func=MemberSettings.as_view('membersettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxImportMembers(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        def allowed_file(filename):
            return '.' in filename and filename.split('.')[-1] in ['csv']
    
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            thisfile = request.files['file']
            
            # get file extention
            thisfileext = thisfile.filename.split('.')[-1]
            
            # make sure valid file
            if not thisfile:
                db.session.rollback()
                cause = 'Unexpected Error: Missing file'
                print cause
                return failure_response(cause=cause)
            if not allowed_file(thisfile.filename):
                db.session.rollback()
                cause = 'Invalid file type "{}"'.format(thisfileext)
                print cause
                return failure_response(cause=cause)
            
            # get all the members currently in the database for the indicated year
            allmembers = Runner.query.filter_by(club_id=club_id,active=True).all()
            
            # if some members exist, verify user wants to overwrite
            #print 'force = ' + request.args.get('force')
            if allmembers and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite members for this year?',confirm=True)
            
            # handle csv file
            if thisfileext == 'csv':
                thisfilecsv = DictReaderStr2Num(thisfile.stream)
                filemembers = []
                for row in thisfilecsv:
                    ## make sure all members are within correct year
                    #if int(row['year']) != flask.session['year']:
                    #    db.session.rollback()
                    #    cause = 'File year {} does not match session year {}'.format(row['year'],flask.session['year'])
                    #    print cause
                    #    return failure_response(cause=cause)
                    filemembers.append(row)
                    
            # how did this happen?  see allowed_file() for error
            else:
                db.session.rollback()
                cause = 'Unexpected Error: Invalid file extention encountered "{}"'.format(thisfileext)
                print cause
                return failure_response(cause=cause)
            
            # prepare to invalidate any members which are currently there, but not in the file
            inactivemembers = {}
            for thismember in allmembers:
                inactivemembers[thismember.name,thismember.dateofbirth] = thismember
            
            # process each name in member list
            for thismember in filemembers:
                # add or update member in database
                member = Runner(club_id,thismember['year'],thismember['member'],thismember['membernum'],thismember['date'],thismember['time'],thismember['distance'],thismember['surface'])
                added = racedb.insert_or_update(db.session,Runner,member,skipcolumns=['id'],name=member.name,dateofbirth=member.dateofbirth)
                
                # remove this member from collection of members which should be deleted in database
                if (member.name,member.year) in inactivemembers:
                    inactivemembers.pop((member.name,member.year))
                    
            # any members remaining in 'inactivemembers' should be deactivated
            for (name,year) in inactivemembers:
                thismember = Runner.query.filter_by(name=name,year=year).first() # should be only one returned by filter
                thismember.active = False
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_importmembers',view_func=AjaxImportMembers.as_view('_importmembers'),methods=['POST'])
#----------------------------------------------------------------------

