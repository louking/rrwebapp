###########################################################################################
# result - result views for result results web application
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
import os.path
import time
import tempfile
import os

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
import raceresults
from loutilities.namesplitter import split_full_name

# module specific needs
from racedb import Runner, ManagedResult, RaceResult, RaceSeries, Race
from forms import ManagedResultForm 

#######################################################################
class ManageResults(MethodView):
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
                
            form = ManagedResultForm()
    
            results = []
            # TODO: if thisyear is not current year, need to look at expirationdate and renewdate, not active (issue #8)
            results = Runner.query.filter_by(club_id=club_id,active=True).order_by('lname').all()
    
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('manageresults.html',form=form,results=results,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/manageresults',view_func=ManageResults.as_view('manageresults'),methods=['GET'])
#----------------------------------------------------------------------

# NOTE: THIS HAS NOT BEEN TESTED AND IS NOT CURRENTLY USED
# perhaps some kind of result merge will be required in the future, but editing a result would get overwritten by result import
########################################################################
#class ResultSettings(MethodView):
########################################################################
#    decorators = [login_required]
#    #----------------------------------------------------------------------
#    def get(self,resultid):
#    #----------------------------------------------------------------------
#        try:
#            club_id = flask.session['club_id']
#            thisyear = flask.session['year']
#            
#            readcheck = ViewClubDataPermission(club_id)
#            writecheck = UpdateClubDataPermission(club_id)
#            
#            # verify user can at least read the data, otherwise abort
#            if not readcheck.can():
#                db.session.rollback()
#                flask.abort(403)
#                
#            # resultid == 0 means add
#            if resultid == 0:
#                if not writecheck.can():
#                    db.session.rollback()
#                    flask.abort(403)
#                result = Runner(club_id)
#                form = ManagedResultForm()
#                action = 'Add'
#                pagename = 'Add Result'
#            
#            # resultid != 0 means update
#            else:
#                result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
#    
#                # copy source attributes to form
#                params = {}
#                for field in vars(result):
#                    params[field] = getattr(result,field)
#                
#                form = ManagedResultForm(**params)
#                action = 'Update'
#                pagename = 'Edit Result'
#    
#            # commit database updates and close transaction
#            db.session.commit()
#            # delete button only for edit (resultid != 0)
#            return flask.render_template('resultsettings.html',thispagename=pagename,
#                                         action=action,deletebutton=(resultid!=0),
#                                         form=form,result=result,writeallowed=writecheck.can())
#        
#        except:
#            # roll back database updates and close transaction
#            db.session.rollback()
#            raise
#        
#    #----------------------------------------------------------------------
#    def post(self,resultid):
#    #----------------------------------------------------------------------
#        form = ManagedResultForm()
#
#        try:
#            club_id = flask.session['club_id']
#            thisyear = flask.session['year']
#
#            # handle Cancel
#            if request.form['whichbutton'] == 'Cancel':
#                db.session.rollback() # throw out any changes which have been made
#                return flask.redirect(flask.url_for('manageresults'))
#    
#            # handle Delete
#            elif request.form['whichbutton'] == 'Delete':
#                result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
#                # db.session.delete(result)   # should we allow result deletion?  maybe not
#                result.active = False
#
#                # commit database updates and close transaction
#                db.session.commit()
#                return flask.redirect(flask.url_for('manageresults'))
#
#            # handle Update and Add
#            elif request.form['whichbutton'] in ['Update','Add']:
#                if not form.validate_on_submit():
#                    return 'error occurred on form submit -- update error message and display form again'
#                    
#                readcheck = ViewClubDataPermission(club_id)
#                writecheck = UpdateClubDataPermission(club_id)
#                
#                # verify user can at write the data, otherwise abort
#                if not writecheck.can():
#                    db.session.rollback()
#                    flask.abort(403)
#                
#                # add
#                if request.form['whichbutton'] == 'Add':
#                    result = Runner(club_id)
#                # update
#                else:
#                    result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
#                
#                # copy fields from form to db object
#                for field in vars(result):
#                    # only copy attributes which are in the form class already
#                    if field in form.data:
#                        setattr(result,field,form.data[field])
#                
#                # add
#                if request.form['whichbutton'] == 'Add':
#                    db.session.add(result)
#                    db.session.flush()  # needed to update result.id
#                    resultid = result.id    # not needed yet, but here for consistency
#
#                # commit database updates and close transaction
#                db.session.commit()
#                return flask.redirect(flask.url_for('manageresults'))
#            
#        except:
#            # roll back database updates and close transaction
#            db.session.rollback()
#            raise
##----------------------------------------------------------------------
#app.add_url_rule('/resultsettings/<int:resultid>',view_func=ResultSettings.as_view('resultsettings'),methods=['GET','POST'])
##----------------------------------------------------------------------

#----------------------------------------------------------------------
def allowed_file(filename):
#----------------------------------------------------------------------
    return '.' in filename and filename.split('.')[-1] in ['xls','xlsx','txt','csv']

#----------------------------------------------------------------------
def cleanresult(managedresult):
#----------------------------------------------------------------------
    if not managedresult.name:
        managedresult.name = ' '.join([managedresult.fname,managedresult.lname])
    elif not managedresult.fname or not managedresult.lname:
        names = split_full_name(managedresult.name)
        managedresult.fname = names['fname']
        managedresult.lname = names['lname']
    
    if not managedresult.hometown:
        if managedresult.city and managedresult.state:
            managedresult.hometown = ', '.join([managedresult.city,managedresult.state])
        

#######################################################################
class AjaxImportResults(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self,raceid):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            resultfile = request.files['file']

            # get file extention
            root,ext = os.path.splitext(resultfile.filename)
            
            # make sure valid file
            if not resultfile:
                db.session.rollback()
                cause = 'Unexpected Error: Missing file'
                print cause
                return failure_response(cause=cause)
            if not allowed_file(resultfile.filename):
                db.session.rollback()
                cause = 'Invalid file type {} for file {}'.format(ext,resultfile.filename)
                print cause
                return failure_response(cause=cause)

            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if not race:
                db.session.rollback()
                cause = 'race id={} does not exist for this club'.format(raceid)
                print cause
                return failure_response(cause=cause)

            # do we have any results yet?  If so, make sure it is ok to overwrite them
            dbresults = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).all()

            # if some results exist, verify user wants to overwrite
            #print 'force = ' + request.args.get('force')
            if dbresults:
                # verify overwrite
                if not request.args.get('force')=='true':
                    db.session.rollback()
                    return failure_response(cause='Overwrite results?',confirm=True)
                # force is true.  delete all the current results for this race
                else:
                    numdeleted = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
                    numdeleted = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
            
            # save file for import
            tempdir = tempfile.mkdtemp()
            resultfilename = secure_filename(resultfile.filename)
            resultpathname = os.path.join(tempdir,resultfilename)
            resultfile.save(resultpathname)            

            try:
                rr = raceresults.RaceResults(resultpathname,race.distance)
            
            # format not good enough
            except raceresults.headerError, e:
                db.session.rollback()
                cause =  e
                print cause
                return failure_response(cause=cause)
                
            # how did this happen?  check allowed_file() for bugs
            except raceresults.parameterError,e:
                db.session.rollback()
                #cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext,resultfile.filename,resultpathname)
                cause =  'Program Error: {}'.format(e)
                print cause
                return failure_response(cause=cause)
            
            # collect results from resultsfile
            numentries = 0
            dbresults = []
            while True:
                try:
                    fileresult = rr.next()
                    dbresult   = ManagedResult(club_id,raceid)
                    for field in fileresult:
                        if hasattr(dbresult,field):
                            setattr(dbresult,field,fileresult[field])
                    cleanresult(dbresult)
                    db.session.add(dbresult)
                    dbresults.append(dbresult)
                except StopIteration:
                    break
                numentries += 1

            # remove file and temporary directory
            rr.close()
            os.remove(resultpathname)
            try:
                os.rmdir(tempdir)
            # no idea why this can happen; hopefully doesn't happen on linux
            except WindowsError,e:
                print 'exception ignored: {}'.format(e)

            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_importresults/<int:raceid>',view_func=AjaxImportResults.as_view('_importresults'),methods=['POST'])
#----------------------------------------------------------------------

