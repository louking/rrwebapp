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

# module specific needs
from racedb import Runner, ManagedResults, RaceResult, RaceSeries, Race
from forms import ManagedResultForm 

# module globals
tYmd = timeu.asctime('%Y-%m-%d')

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
#######################################################################
class ResultSettings(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,resultid):
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
                
            # resultid == 0 means add
            if resultid == 0:
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                result = Runner(club_id)
                form = ManagedResultForm()
                action = 'Add'
                pagename = 'Add Result'
            
            # resultid != 0 means update
            else:
                result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
    
                # copy source attributes to form
                params = {}
                for field in vars(result):
                    params[field] = getattr(result,field)
                
                form = ManagedResultForm(**params)
                action = 'Update'
                pagename = 'Edit Result'
    
            # commit database updates and close transaction
            db.session.commit()
            # delete button only for edit (resultid != 0)
            return flask.render_template('resultsettings.html',thispagename=pagename,
                                         action=action,deletebutton=(resultid!=0),
                                         form=form,result=result,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,resultid):
    #----------------------------------------------------------------------
        form = ManagedResultForm()

        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            # handle Cancel
            if request.form['whichbutton'] == 'Cancel':
                db.session.rollback() # throw out any changes which have been made
                return flask.redirect(flask.url_for('manageresults'))
    
            # handle Delete
            elif request.form['whichbutton'] == 'Delete':
                result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
                # db.session.delete(result)   # should we allow result deletion?  maybe not
                result.active = False

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('manageresults'))

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
                    result = Runner(club_id)
                # update
                else:
                    result = Runner.query.filter_by(club_id=club_id,active=True,id=resultid).first()
                
                # copy fields from form to db object
                for field in vars(result):
                    # only copy attributes which are in the form class already
                    if field in form.data:
                        setattr(result,field,form.data[field])
                
                # add
                if request.form['whichbutton'] == 'Add':
                    db.session.add(result)
                    db.session.flush()  # needed to update result.id
                    resultid = result.id    # not needed yet, but here for consistency

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('manageresults'))
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/resultsettings/<int:resultid>',view_func=ResultSettings.as_view('resultsettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxImportResults(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        def allowed_file(filename):
            return '.' in filename and filename.split('.')[-1] in ['csv','xlsx','xls']
    
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

            # save file for import
            tempdir = tempfile.mkdtemp()
            resultfilename = secure_filename(resultfile.filename)
            resultpathname = os.path.join(tempdir,resultfilename)
            resultfile.save(resultpathname)            

            # bring in data from the file
            if ext in ['.xls','.xlsx']:
                results = clubmember.XlClubResult(resultpathname)
            elif ext in ['.csv']:
                results = clubmember.CsvClubResult(resultpathname)
            
            # how did this happen?  check allowed_file() for bugs
            else:
                db.session.rollback()
                cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext,resultfile.filename,resultpathname)
                print cause
                return failure_response(cause=cause)
            
            # remove file and temporary directory
            os.remove(resultpathname)
            try:
                os.rmdir(tempdir)
            # no idea why this can happen; hopefully doesn't happen on linux
            except WindowsError,e:
                print 'exception ignored: {}'.format(e)

            # get old clubmembers from database
            dbresults = clubmember.DbClubResult()   # use default database

            # get all the result runners currently in the database
            # hash them into dict by (name,dateofbirth)
            allrunners = Runner.query.filter_by(result=True,active=True).all()
            inactiverunners = {}
            for thisrunner in allrunners:
                inactiverunners[thisrunner.name,thisrunner.dateofbirth] = thisrunner

            # if some results exist, verify user wants to overwrite
            #print 'force = ' + request.args.get('force')
            if allrunners and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite results?',confirm=True)
            
            # prepare for age check
            thisyear = timeu.epoch2dt(time.time()).year
            asofasc = '{}-1-1'.format(thisyear) # jan 1 of current year
            asof = tYmd.asc2dt(asofasc) 
    
            # process each name in new resultship list
            allresults = results.getresults()
            for name in allresults:
                theseresults = allresults[name]
                # NOTE: may be multiple results with same name
                for thisresult in theseresults:
                    thisname = thisresult['name']
                    thisfname = thisresult['fname']
                    thislname = thisresult['lname']
                    thisdob = thisresult['dob']
                    thisgender = thisresult['gender'][0].upper()    # male -> M, female -> F
                    thishometown = thisresult['hometown']
                    thisrenewdate = thisresult['renewdate']
                    thisexpdate = thisresult['expdate']
        
                    # prep for if .. elif below by running some queries
                    # handle close matches, if DOB does match
                    age = timeu.age(asof,tYmd.asc2dt(thisdob))
                    matchingresult = dbresults.findresult(thisname,age,asofasc)
                    dbresult = None
                    if matchingresult:
                        resultname,resultdob = matchingresult
                        if resultdob == thisdob:
                            dbresult = racedb.getunique(db.session,Runner,result=True,name=resultname,dateofbirth=thisdob)
                    
                    # TODO: need to handle case where dob transitions from '' to actual date of birth
                    
                    # no result found, maybe there is nonresult of same name already in database
                    if dbresult is None:
                        dbnonresult = racedb.getunique(db.session,Runner,result=False,name=thisname)
                        # TODO: there's a slim possibility that there are two nonresults with the same name, but I'm sure we've already
                        # bolloxed that up in importresult as there's no way to discriminate between the two
                        
                        ## make report for new results
                        #NEWMEMCSV.writerow({'name':thisname,'dob':thisdob})
                        
                    # see if this runner is a result in the database already, or was a result once and make the update
                    # add or update runner in database
                    # get instance, if it exists, and make any updates
                    found = False
                    if dbresult is not None:
                        thisrunner = Runner(club_id,resultname,thisdob,thisgender,thishometown,
                                            fname=thisfname,lname=thislname,
                                            renewdate=thisrenewdate,expdate=thisexpdate)
                        
                        # this is also done down below, but must be done here in case result's name has changed
                        if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                            inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))
        
                        # overwrite result's name if necessary
                        thisrunner.name = thisname  
                        
                        added = racedb.update(db.session,Runner,dbresult,thisrunner,skipcolumns=['id'])
                        found = True
                        
                    # if runner's name is in database, but not a result, see if this runner is a nonmeresult which can be converted
                    # Check first result for age against age within the input file
                    # if ages match, convert nonresult to result
                    elif dbnonresult is not None:
                        # get dt for date of birth, if specified
                        try:
                            dob = tYmd.asc2dt(thisdob)
                        except ValueError:
                            dob = None
                            
                        # nonresult came into the database due to a nonresult race result, so we can use any race result to check nonresult's age
                        if dob:
                            result = RaceResult.query.filter_by(runnerid=dbnonresult.id).first()
                            resultage = result.agage
                            racedate = tYmd.asc2dt(result.race.date)
                            expectedage = racedate.year - dob.year - int((racedate.month, racedate.day) < (dob.month, dob.day))
                        
                        # we found the right person, always if dob isn't specified, but preferably check race result for correct age
                        if dob is None or resultage == expectedage:
                            thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                                fname=thisfname,lname=thislname,
                                                renewdate=thisrenewdate,expdate=thisexpdate)
                            added = racedb.update(db.session,Runner,dbnonresult,thisrunner,skipcolumns=['id'])
                            found = True
                        else:
                            print '{} found in database, wrong age, expected {} found {} in {}'.format(thisname,expectedage,resultage,result)
                            # TODO: need to make file for these, also need way to force update, because maybe bad date in database for result
                            # currently this will cause a new runner entry
                    
                    # if runner was not found in database, just insert new runner
                    if not found:
                        thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                            fname=thisfname,lname=thislname,
                                            renewdate=thisrenewdate,expdate=thisexpdate)
                        added = racedb.insert_or_update(db.session,Runner,thisrunner,skipcolumns=['id'],name=thisname,dateofbirth=thisdob)
                        
                    # remove this runner from collection of runners which should be deactivated in database
                    if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                        inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))
                
            # any runners remaining in 'inactiverunners' should be deactivated
            for (name,dateofbirth) in inactiverunners:
                thisrunner = Runner.query.filter_by(name=name,dateofbirth=dateofbirth).first() # should be only one returned by filter
                thisrunner.active = False
        
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_importresults',view_func=AjaxImportResults.as_view('_importresults'),methods=['POST'])
#----------------------------------------------------------------------

