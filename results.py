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
import json
import csv
import os.path
import time
import tempfile
import os
from datetime import timedelta
import traceback

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
import raceresults
import clubmember
from racedb import dbdate, Runner, ManagedResult, RaceResult, RaceSeries, Race, Exclusion, Series, Divisions, dbdate
from forms import ManagedResultForm, SeriesResultForm, RunnerResultForm
from loutilities.namesplitter import split_full_name
import loutilities.renderrun as render
from loutilities import timeu, agegrade
tYmd = timeu.asctime('%Y-%m-%d')

# control behavior of import
DIFF_CUTOFF = 0.7   # ratio of matching characters for cutoff handled by 'clubmember'
NONMEMBERCUTOFF = 0.9   # insist on high cutoff for nonmember matching
AGE_DELTAMAX = 3    # +/- num years to be included in DISP_MISSED
JOIN_GRACEPERIOD = timedelta(7) # allow runner to join 1 week beyond race date

# support age grade
ag = agegrade.AgeGrade()

# initialdisposition values
# * match - exact name match found in runner table, with age consistent with dateofbirth
# * close - close name match found, with age consistent with dateofbirth
# * missed - close name match found, but age is inconsistent with dateofbirth
# * excluded - this name is in the exclusion table, either prior to import **or as a result of user decision**

DISP_MATCH = 'definite'         # exact match of member (or non-member for non 'membersonly' race)
DISP_CLOSE = 'similar'          # similar match to member, matching age
DISP_MISSED = 'missed'          # similar to some member(s), age mismatch (within window)
DISP_EXCLUDED = 'excluded'      # DISP_CLOSE match, but found in exclusions table
DISP_NOTUSED = ''               # not used for results

class BooleanError(Exception): pass

#----------------------------------------------------------------------
def filtermissed(club_id,missed,racedate,resultage):
#----------------------------------------------------------------------
    '''
    filter missed matches which are greater than a configured max age delta
    also filter missed matches which were in the exclusions table
    
    :param club_id: club id for missed matches
    :param missed: list of missed matches, as returned from clubmember.xxx().getmissedmatches()
    :param racedate: race date in dbdate format
    :param age: resultage from race result, if None, '', 0, empty list is returned
    
    :rtype: missed list, including only elements within the allowed age range
    '''
    # make a local copy in case the caller wants to preserve the original list
    localmissed = missed[:]
    
    # if age in result is invalid, empty list is returned
    if not resultage:
        return []
    
    racedatedt = dbdate.asc2dt(racedate)
    for thismissed in missed:
        # don't consider 'missed matches' where age difference from result is too large
        dobdt = dbdate.asc2dt(thismissed['dob'])
        if abs(timeu.age(racedatedt,dobdt) - resultage) > AGE_DELTAMAX:
            localmissed.remove(thismissed)
        else:
            resultname = thismissed['name']
            runnername = thismissed['dbname']
            ascdob = thismissed['dob']
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            exclusion = Exclusion.query.filter_by(club_id=club_id,foundname=resultname,runnerid=runner.id).first()
            if exclusion:
                localmissed.remove(thismissed)
                
            # TODO: also need to skip runners who were not members at the time of the race
            #if membersonly and runner.renewdate and dbdate.asc2dt(runner.renewdate) > dbdate.asc2dt(racedate)+JOIN_GRACEPERIOD:
            #    localmissed.remove(thismissed)

    return localmissed

#----------------------------------------------------------------------
def getmembertype(runner):
#----------------------------------------------------------------------
    '''
    determine member type based on runner field values
    
    :param runner: record from runner table or None
    
    :rtype: 'member', 'inactive', 'nonmember', ''
    '''
    
    if not runner:
        return 'nonmember'
    
    elif runner.member:
        if runner.active:
            return 'member'
    
        else:
            return 'inactive'
        
    else:
        return 'nonmember'

#######################################################################
class EditParticipants(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,raceid):
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
    
            # get all the results, and the race record
            results = []
            results = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).order_by('time').all()

            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            racedatedt = dbdate.asc2dt(race.date)
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(flask.url_for('manageraces'))

            # active is ClubMember object for active members; if race isn't for members only nonmember is ClubMember object for nonmembers
            membersonly = race.series[0].series.membersonly
            if membersonly:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)
            
            # fix up the following:
            #   * time gets converted from seconds
            #   * determine member matching, set runnerid choices and initially selected choice
            #   * based on matching, set disposition
            times = []
            dispositions = []
            runnerchoices = []
            runnervalues = []
            membertypes = []
            for result in results:
                thistime = render.rendertime(result.time,0)
                thisdisposition = result.initialdisposition # set in AjaxImportResults.post()
                thisrunnervalue = result.runnerid           # set in AjaxImportResults.post()
                thisrunnerchoice = [(None,'<not included>')]
                
                # need to repeat logic from AjaxImportResults() because AjaxImportResults() may leave null in runnerid field of managedresult
                candidate = pool.findmember(result.name,result.age,race.date)
                
                runner = None
                runnername = ''
                if thisdisposition in [DISP_MATCH,DISP_CLOSE]:
                    # found a possible runner
                    if candidate:
                        runnername,ascdob = candidate
                        runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
                        thisrunnerchoice.append([runner.id,runner.name])
                    
                    # this shouldn't happen
                    else:
                        stophere
                        pass    # TODO: this is a bug -- that to do?

                # didn't find runner, what were other possibilities?
                elif thisdisposition == DISP_MISSED:
                    # this is possible because maybe (new) member was chosen in prior use of editparticipants
                    if candidate:
                        runnername,ascdob = candidate
                        runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
                        thisrunnerchoice.append([runner.id,runner.name])
                    
                    # this handles case where age mismatch was chosen in prior use of editparticipants
                    elif thisrunnervalue:
                        runner = Runner.query.filter_by(club_id=club_id,id=thisrunnervalue).first()

                    # remove runners who were not within the age window, or who were excluded
                    missed = pool.getmissedmatches()                        
                    missed = filtermissed(club_id,missed,race.date,result.age)
                    for thismissed in missed:
                        missedrunner = Runner.query.filter_by(club_id=club_id,name=thismissed['dbname'],dateofbirth=thismissed['dob']).first()
                        dobdt = dbdate.asc2dt(thismissed['dob'])
                        nameage = '{} ({})'.format(missedrunner.name,timeu.age(racedatedt,dobdt))
                        thisrunnerchoice.append((missedrunner.id,nameage))
                    
                # for no match and excluded entries, change choice
                elif thisdisposition in [DISP_NOTUSED,DISP_EXCLUDED]:
                    if membersonly:
                        thisrunnerchoice = [(None,'n/a')]
                    else:
                        # leave default
                        pass
                
                # for non membersonly race, maybe need to add new name to member database, give that option
                if not membersonly and thisdisposition != DISP_MATCH:
                    # it's possible that result.name == runnername if (new) member was added in prior use of editparticipants
                    if result.name != runnername:
                        thisrunnerchoice.append(('new','{} (new)'.format(result.name)))
                
                # include all the metadata for this result
                times.append(thistime)
                dispositions.append(thisdisposition)
                runnerchoices.append(thisrunnerchoice)
                runnervalues.append(thisrunnervalue)
                membertypes.append(getmembertype(runner))

            resultsdata = zip(results,times,dispositions,runnerchoices,runnervalues,membertypes)
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('editparticipants.html',form=form,race=race,membersonly=membersonly,resultsdata=resultsdata,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/editparticipants/<int:raceid>',view_func=EditParticipants.as_view('editparticipants'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class SeriesResults(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self,raceid):
    #----------------------------------------------------------------------
        try:
            seriesarg = request.args.get('series','')
            division = request.args.get('div','')
            gender = request.args.get('gen','')
            printerarg = request.args.get('printerfriendly','false')
            printerfriendly = (printerarg == 'true')

            form = SeriesResultForm()
    
            # get race record
            race = Race.query.filter_by(id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(flask.url_for('manageraces'))
            
            # get all the results, and the race record
            results = []
            for series in race.series:
                seriesid = series.series.id
                seriesresults = RaceResult.query.filter_by(raceid=raceid,seriesid=seriesid).order_by(series.series.orderby).all()
                # this is easier, code-wise, than using sqlalchemy desc() function
                if series.series.hightolow:
                    seriesresults.reverse()
                results += seriesresults
            
            # fix up the following:
            #   * time gets converted from seconds
            #   * determine member matching, set runnerid choices and initially selected choice
            #   * based on matching, set disposition
            displayresults = []
            for result in results:
                runner = Runner.query.filter_by(id=result.runnerid).first()
                thisname = runner.name
                series = Series.query.filter_by(id=result.seriesid).first()
                thisseries = series.name
                thistime = render.rendertime(result.time,0)
                thisagtime = render.rendertime(result.agtime,0)
                thispace = render.rendertime(result.time / race.distance, 0, useceiling=False)
                if result.divisionlow:
                    if result.divisionlow == 0:
                        thisdiv = 'up to {}'.format(result.divisionhigh)
                    elif result.divisionhigh == 99:
                        thisdiv = '{} and up'.format(result.divisionlow)
                    else:
                        thisdiv = '{} - {}'.format(result.divisionlow,result.divisionhigh)
                else:
                    thisdiv = ''

                if result.genderplace:
                    thisplace = result.genderplace
                elif result.agtimeplace:
                    thisplace = result.agtimeplace
                else:
                    thisplace = None

                # order must match that which is expected within seriesresults.html
                displayresults.append((result,thisseries,thisplace,thisname,thistime,thisdiv,thisagtime,thispace))
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('seriesresults.html',form=form,race=race,resultsdata=displayresults,
                                         series=seriesarg,division=division,gender=gender,printerfriendly=printerfriendly,
                                         inhibityear=True,inhibitclub=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/seriesresults/<int:raceid>',view_func=SeriesResults.as_view('seriesresults'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class RunnerResults(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            starttime = time.time()
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)
                
            form = RunnerResultForm()

            # filter on valid runnerid, if present
            resultfilter = {}
            name = None
            pagename = 'Results'
            if runnerid:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    resultfilter['runnerid'] = runnerid
                    name = runner.name
                    pagename = '{} Results'.format(name)

            # get all the results
            results = []
            for series in Series.query.all():
                seriesid = series.id
                resultfilter['seriesid'] = seriesid
                seriesresults = RaceResult.query.filter_by(**resultfilter).order_by(series.orderby).all()
                # this is easier, code-wise, than using sqlalchemy desc() function
                if series.hightolow:
                    seriesresults.reverse()
                # remove results for inactive races
                results += [s for s in seriesresults if s.race.active]
            
            # kludge alert!  filter out results when raceseries is inactive
            allraceseries = RaceSeries.query.all()
            raceseries = {}
            for rs in allraceseries:
                raceseries[rs.raceid,rs.seriesid] = rs.active
            filteredresults = []
            for result in results[:]:
                if raceseries[result.raceid,result.seriesid]:
                    filteredresults.append(result)
            results = filteredresults
            
            # sort results by date
            dateresults = [(r.race.date,r) for r in results]
            dateresults.sort()
            results = [dr[1] for dr in dateresults]
            
            # fix up the following:
            #   * time gets converted from seconds
            #   * determine member matching, set runnerid choices and initially selected choice
            #   * based on matching, set disposition
            displayresults = []
            for result in results:
                thisname = result.runner.name
                thisseries = result.series.name
                thisrace = result.race.name
                thisdate = result.race.date
                thisdistance = result.race.distance
                thistime = render.rendertime(result.time,0)
                thisagtime = render.rendertime(result.agtime,0)
                thispace = render.rendertime(result.time / result.race.distance, 0, useceiling=False)
                if result.divisionlow:
                    if result.divisionlow == 0:
                        thisdiv = 'up to {}'.format(result.divisionhigh)
                    elif result.divisionhigh == 99:
                        thisdiv = '{} and up'.format(result.divisionlow)
                    else:
                        thisdiv = '{} - {}'.format(result.divisionlow,result.divisionhigh)
                else:
                    thisdiv = ''

                if result.genderplace:
                    thisplace = result.genderplace
                elif result.agtimeplace:
                    thisplace = result.agtimeplace
                else:
                    thisplace = None

                # order must match that which is expected within results.html
                displayresults.append((result,thisseries,thisrace,thisdate,thisdistance,thisplace,thisname,thistime,thisdiv,thisagtime,thispace))
            
            # commit database updates and close transaction
            db.session.commit()
            finishtime = time.time()
            app.logger.debug('RunnerResults elapsed time = {} seconds'.format(finishtime-starttime))
            return flask.render_template('results.html',form=form,pagename=pagename,resultsdata=displayresults,
                                         name=name,series=seriesarg,
                                         inhibityear=True,inhibitclub=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/results',view_func=RunnerResults.as_view('results'),methods=['GET'])
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
                app.logger.error(cause)
                return failure_response(cause=cause)
            if not allowed_file(resultfile.filename):
                db.session.rollback()
                cause = 'Invalid file type {} for file {}'.format(ext,resultfile.filename)
                app.logger.warning(cause)
                return failure_response(cause=cause)

            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if not race:
                db.session.rollback()
                cause = 'race id={} does not exist for this club'.format(raceid)
                app.logger.warning(cause)
                return failure_response(cause=cause)

            # do we have any results yet?  If so, make sure it is ok to overwrite them
            dbresults = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).all()

            # if some results exist, verify user wants to overwrite
            if dbresults:
                # verify overwrite
                if not request.args.get('force')=='true':
                    db.session.rollback()
                    return failure_response(cause='Overwrite results?',confirm=True)
                # force is true.  delete all the current results for this race
                else:
                    app.logger.debug('editparticipants overwrite started')
                    nummrdeleted = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
                    numrrdeleted = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
                    app.logger.debug('{} managedresults deleted; {} raceresults deleted'.format(nummrdeleted,numrrdeleted))
                    # also delete any nonmembers who do not have results, as these were most likely brought in by past version of this race
                    nonmembers = Runner.query.filter_by(club_id=club_id,member=False)
                    for nonmember in nonmembers:
                        nonmemberresults = RaceResult.query.filter_by(club_id=club_id,runnerid=nonmember.id).all()
                        app.logger.debug('nonmember={}/{} nonmemberresults={}'.format(nonmember.name,nonmember.id,nonmemberresults))
                        if len(nonmemberresults) == 0:
                            db.session.delete(nonmember)
                    # pick up any deletes for later processing
                    db.session.flush()
            
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
                app.logger.warning(cause)
                return failure_response(cause=cause)
                
            # how did this happen?  check allowed_file() for bugs
            except raceresults.dataError,e:
                db.session.rollback()
                #cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext,resultfile.filename,resultpathname)
                cause =  'Program Error: {}'.format(e)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # get race and list of runners who should be included in this race, based on race's membersonly configuration
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            racedatedt = dbdate.asc2dt(race.date)
            if len(race.series) == 0:
                db.session.rollback()
                cause =  'Race needs to be included in at least one series to import results'
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # active is ClubMember object for active members; if race isn't for members only inactive and nonmember ClubMember objects for nonmembers
            membersonly = race.series[0].series.membersonly
            if membersonly:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)
                
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
                    app.logger.debug('Processing {}'.format(dbresult.name))
                    
                    # create initial disposition
                    candidate = pool.findmember(dbresult.name,dbresult.age,race.date)
                    app.logger.debug('  candidate = {}'.format(candidate))

                    # for members or people who were once members, set age based on date of birth in database
                    # note this clause will be executed for membersonly races
                    if candidate:
                        # note some candidates' ascdob may come back as None (these must be nonmembers because we have dob for all current/previous members)
                        runnername,ascdob = candidate
                        
                        # set active or inactive member's id
                        runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
                        dbresult.runnerid = runner.id
                        app.logger.debug('  using runner.id = {}'.format(runner.id))
                    
                        # if candidate has renewdate and did not join in time for member's only race, indicate this result isn't used
                        if membersonly and runner.renewdate and dbdate.asc2dt(runner.renewdate) > dbdate.asc2dt(race.date)+JOIN_GRACEPERIOD:
                                # discard candidate
                                candidate = None
                                
                                # was...
                                #dbresult.initialdisposition = DISP_NOTUSED
                                #dbresult.runnerid = None
                                #dbresult.confirmed = True
                                #app.logger.debug('    DISP_NOTUSED')
                        
                        # runner joined in time for race, or not member's only race
                        # if exact match, indicate we have a match
                        elif runnername.lower() == dbresult.name.lower():
                            # if current or former member
                            if ascdob:
                                dbresult.initialdisposition = DISP_MATCH
                                dbresult.confirmed = True
                                app.logger.debug('    DISP_MATCH')
                                
                            # otherwise was nonmember, included from some non memberonly race
                            else:
                                # must check current result age against any previous result age
                                thisresultage = dbresult.age
                                if thisresultage:
                                    thisracedate = tYmd.asc2dt(race.date)
                                    pastresult = RaceResult.query.filter_by(club_id=club_id,runnerid=runner.id).first()
                                    pastresultage = pastresult.agage
                                    pastracedate = tYmd.asc2dt(pastresult.race.date)
                                    
                                    # make sure this result age is consistent with previous result +/- 1 year
                                    deltayears = abs((thisracedate - pastracedate).days / 365.25)
                                    deltaage = abs(int(thisresultage) - pastresultage)
                                    if abs(deltaage - deltayears) <= 1:
                                        dbresult.initialdisposition = DISP_MATCH
                                        dbresult.confirmed = True
                                        app.logger.debug('    DISP_MATCH')

                                    # if inconsistent, ignore candidate
                                    else:
                                        candidate = None

                                # ignore candidates when we do not have age in result
                                else:
                                    candidate = None
                                    dbresult.runnerid = None

                        # runner joined in time for race, or not member's only race, but match wasn't exact
                        # check for exclusions
                        else:
                            exclusion = Exclusion.query.filter_by(club_id=club_id,foundname=dbresult.name,runnerid=dbresult.runnerid).first()
                            
                            # if results name not found against this runner id in exclusions table, indicate we found close match
                            if not exclusion:
                                dbresult.initialdisposition = DISP_CLOSE
                                dbresult.confirmed = False
                                app.logger.debug('    DISP_CLOSE')
                                
                            # results name vs this runner id has been excluded
                            else:
                                candidate = None
                                
                                # was...
                                #dbresult.initialdisposition = DISP_NOTUSED  # was DISP_EXCLUDED
                                #dbresult.runnerid = None
                                #dbresult.confirmed = True
                                #app.logger.debug('    DISP_NOTUSED')
                    
                    # didn't find runner on initial search, or candidate was discarded
                    if not candidate:
                        # clear runnerid in case we discarded candidate above
                        dbresult.runnerid = None

                        # favor active members, then inactive members
                        # note: nonmembers are not looked at for missed because filtermissed() depends on DOB
                        missed = pool.getmissedmatches()
                        app.logger.debug('  pool.getmissedmatches() = {}'.format(missed))
                        
                        # don't consider 'missed matches' where age difference from result is too large, or excluded
                        app.logger.debug('  missed before filter = {}'.format(missed))
                        missed = filtermissed(club_id,missed,race.date,dbresult.age)
                        app.logger.debug('  missed after filter = {}'.format(missed))

                        # if there remain are any missed results, indicate missed (due to age difference)
                        # or missed (due to new member proposed for not membersonly)
                        if len(missed) > 0 or not membersonly:
                            dbresult.initialdisposition = DISP_MISSED
                            dbresult.confirmed = False
                            app.logger.debug('    DISP_MISSED')
                            
                        # otherwise, this result isn't used
                        else:
                            dbresult.initialdisposition = DISP_NOTUSED
                            dbresult.confirmed = True
                            app.logger.debug('    DISP_NOTUSED')
                            
                        # not membersonly and didn't find a nonmember, need to create runner 
                        #else:
                        #    runner = Runner(club_id,dbresult.name,None,dbresult.gender,None,member=False)
                        #    added = racedb.insert_or_update(db.session,Runner,runner,skipcolumns=['id'],name=dbresult.name,dateofbirth=None,member=False)
                        #    dbresult.runnerid = runner.id
                        #    app.logger.debug('  added runner.id = {}'.format(runner.id))
                        #    dbresult.initialdisposition = DISP_MATCH
                        #    dbresult.confirmed = True
                        #    app.logger.debug('    DISP_MATCH')
                            
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
                app.logger.warning('exception ignored: {}'.format(e))

            # commit database updates and close transaction
            db.session.commit()
            return success_response(redirect=flask.url_for('editparticipants',raceid=raceid))
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_importresults/<int:raceid>',view_func=AjaxImportResults.as_view('_importresults'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxUpdateManagedResult(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self,resultid):
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
                
            # make sure result exists
            result = ManagedResult.query.filter_by(club_id=club_id,id=resultid).first()
            if not result:
                db.session.rollback()
                cause = 'Unexpected Error: result id {} not found'.format(resultid)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # which field changed?  if not allowed, return failure response
            field = flask.request.args.get('field','<not supplied>')
            if field not in ['runnerid','confirmed']:
                db.session.rollback()
                cause = 'Unexpected Error: field {} not supported'.format(field)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # is value ok? if not allowed, return failure response
            value = flask.request.args.get('value','')
            if value == '':
                db.session.rollback()
                cause = 'Unexpected Error: value must be supplied'
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # handle argmuments provided if nonmember is to be added or removed from runner table
            # note: (newname,newgen) and (removeid) are mutually exclusive
            newname  = flask.request.args.get('newname',None)
            newgen   = flask.request.args.get('newgen',None)
            removeid = flask.request.args.get('removeid',None)
            if newgen and (newgen not in ['M','F'] or not newname):
                db.session.rollback()
                cause = 'Unexpected Error: invalid gender'
                app.logger.error(cause)
                return failure_response(cause=cause)
            # verify exclusivity of newname and removeid
            # let exception handler catch if removeid not an integer
            if removeid:
                if newname:
                    db.session.rollback()
                    cause = 'Unexpected Error: cannot have newname and removeid in same request'
                    app.logger.error(cause)
                    return failure_response(cause=cause)
                removeid = int(removeid)
            
            # try to make update, handle exception
            try:
                # maybe response needs arguments
                respargs = {}
                
                #app.logger.debug("field='{}', value='{}'".format(field,value))
                if field == 'runnerid':
                    # newname present means that this name is a new nonmember to be put in the database
                    if newname:
                        runner = Runner(club_id,newname,None,newgen,None,member=False)
                        added = racedb.insert_or_update(db.session,Runner,runner,skipcolumns=['id'],name=newname,dateofbirth=None,member=False)
                        respargs['action'] = 'newname'
                        respargs['actionsuccess'] = True
                        respargs['id'] = runner.id
                        respargs['name'] = runner.name
                        value = runner.id
                        app.logger.debug('new member value={}'.format(value))
                    
                    # removeid present means that this id should be removed from the database, if possible
                    if removeid:
                        runner = Runner.query.filter_by(club_id=club_id,id=removeid).first()
                        if not runner:
                            db.session.rollback()
                            cause = 'Unexpected Error: member with id={} not found for club'.format(removeid)
                            app.logger.error(cause)
                            return failure_response(cause=cause)
                            
                        # make sure no results for member
                        results = RaceResult.query.filter_by(club_id=club_id,runnerid=removeid).all()
                        if len(results) == 0:
                            # no results, ok to remove member
                            db.session.delete(runner)
                            respargs['action'] = 'removeid'
                            respargs['id'] = removeid
                            respargs['name'] = runner.name
                            respargs['actionsuccess'] = True
                        else:
                            #respargs['action'] = 'removeid'
                            #respargs['actionsuccess'] = False
                            #respargs['removefailcause'] = 'Could not remove id={}.  Had results'.format(removeid)
                            db.session.rollback()
                            cause = 'Unexpected Error: Could not remove id={}.  Had results'.format(removeid)
                            app.logger.error(cause)
                            return failure_response(cause=cause)

                    if value != 'None':
                        result.runnerid = int(value)
                    else:
                        result.runnerid = None
                elif field == 'confirmed':
                    if value in ['true','false']:
                        result.confirmed = (value == 'true')
                    else:
                        raise BooleanError, "invalid literal for boolean: '{}'".format(value)
                else:
                    pass    # this was handled above
                
                # handle exclusions
                # if user is confirming, items get *added* to exclusions table
                # however, if user is removing confirmation, items get *removed* from exclusions table
                exclude = flask.request.args.get('exclude')
                include = flask.request.args.get('include')
                # remove included entry from exclusions, add excluded entries
                if include:
                    #app.logger.debug("include='{}'".format(include))
                    if include not in ['None','new']:
                        incl = Exclusion.query.filter_by(club_id=club_id,foundname=result.name,runnerid=int(include)).first()
                        if incl:
                            # not excluded from future results any more
                            db.session.delete(incl)
                # exclude contains a list of runnerids which should be excluded
                if exclude:
                    #app.logger.debug("exclude='{}'".format(exclude))
                    exclude = eval(exclude) 
                    for thisexcludeid in exclude:
                        # None might get passed in as well as runnerids, so skip that item
                        if thisexcludeid in ['None','new']: continue
                        thisexcludeid = int(thisexcludeid)
                        excl = Exclusion.query.filter_by(club_id=club_id,foundname=result.name,runnerid=thisexcludeid).first()
                        # user is confirming entry -- if not already in table, add exclusion
                        if result.confirmed and not excl:
                            # now excluded from future results
                            newexclusion = Exclusion(club_id,result.name,thisexcludeid)
                            db.session.add(newexclusion)
                        # user is removing confirmation -- if exclusion exists, remove it
                        elif not result.confirmed and excl:
                            db.session.delete(excl)
                        

                    
            except Exception,e:
                db.session.rollback()
                cause = "Unexpected Error: value '{}' not allowed for field {}, {}".format(value,field,e)
                app.logger.error(traceback.format_exc())
                return failure_response(cause=cause)
                
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response(**respargs)
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_updatemanagedresult/<int:resultid>',view_func=AjaxUpdateManagedResult.as_view('_updatemanagedresult'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxTabulateResults(MethodView):
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
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # do we have any series results yet?  If so, make sure it is ok to overwrite them
            dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).all()

            # if some results exist, verify user wants to overwrite
            if dbresults:
                # verify overwrite
                if not request.args.get('force')=='true':
                    db.session.rollback()
                    return failure_response(cause='Overwrite results?',confirm=True)
                # force is true.  delete all the current results for this race
                else:
                    numdeleted = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
    
            # get all the results, and the race record
            results = []
            results = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).order_by('time').all()

            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # need race date division date later for age calculation
            # "date" for division's age calculation is Jan 1 of date race was run
            racedate = dbdate.asc2dt(race.date)
            divdate = racedate.replace(month=1,day=1)

            # get precision for time rendering
            timeprecision,agtimeprecision = render.getprecision(race.distance)

            # for each series for this race - 'series' describes how to tabulate the results
            theseseries = [s.series for s in race.series]
            for series in theseseries:
                # get divisions for this series, if appropriate
                if series.divisions:
                    alldivs = Divisions.query.filter_by(club_id=club_id,seriesid=series.id,active=True).all()
                    
                    if len(alldivs) == 0:
                        cause = "Series '{0}' indicates divisions to be calculated, but no divisions found".format(series.name)
                        db.session.rollback()
                        app.logger.error(cause)
                        return failure_response(cause=cause)
                    
                    divisions = []
                    for div in alldivs:
                        divisions.append((div.divisionlow,div.divisionhigh))

                # collect results from database
                # NOTE: filter() method requires fully qualified field names (e.g., *ManagedResult.*club_id)
                results = ManagedResult.query.filter(ManagedResult.club_id==club_id, ManagedResult.raceid==race.id, ManagedResult.runnerid!=None).order_by('time').all()
                
                # loop through result entries, collecting overall, bygender, division and agegrade results
                for thisresult in results:
                    # get runner information
                    runner = Runner.query.filter_by(club_id=club_id,id=thisresult.runnerid).first()
                    runnerid = runner.id
                    gender = runner.gender
            
                    # we don't have dateofbirth for non-members
                    if runner.dateofbirth:
                        try:
                            dob = dbdate.asc2dt(runner.dateofbirth)
                        except ValueError:
                            dob = None      # should not really happen, but this runner does not get division placement
                    else:
                        dob = None
            
                    # for members, set agegrade age (race date based)
                    # NOTE: the code below assumes that races by divisions are only for members
                    # this is because we need to know the runner's age as of Jan 1 for division standings
                    if dob:
                        agegradeage = timeu.age(racedate,dob)
                        divage = timeu.age(divdate,dob)
                    else:
                        try:
                            agegradeage = int(thisresult.age)
                        except:
                            agegradeage = None
                        divage = None
            
                    # at this point, there should always be a runnerid in the database, even if non-member
                    # create RaceResult entry
                    resulttime = thisresult.time
                    raceresult = RaceResult(club_id,runnerid,race.id,series.id,resulttime,gender,agegradeage)
            
                    # always add age grade to result if we know the age
                    # we will decide whether to render, later based on series.calcagegrade, in another script
                    if agegradeage:
                        timeprecision,agtimeprecision = render.getprecision(race.distance)
                        adjtime = render.adjusttime(resulttime,timeprecision)    # ceiling for adjtime
                        raceresult.agpercent,raceresult.agtime,raceresult.agfactor = ag.agegrade(agegradeage,gender,race.distance,adjtime)
            
                    if series.divisions:
                        # member's age to determine division is the member's age on Jan 1
                        # if member doesn't give date of birth for membership list, member is not eligible for division awards
                        # if non-member, also no division awards, because age as of Jan 1 is not known
                        age = divage    # None if not available
                        if age:
                            # linear search for correct division
                            for thisdiv in divisions:
                                divlow = thisdiv[0]
                                divhigh = thisdiv[1]
                                if age in range(divlow,divhigh+1):
                                    raceresult.divisionlow = divlow
                                    raceresult.divisionhigh = divhigh
                                    break
            
                    # make result persistent
                    db.session.add(raceresult)
                
                # flush the results so they show up below
                db.session.flush()
                
                # process overall and bygender results, sorted by time
                # TODO: is series.overall vs. series.orderby=='time' redundant?  same question for series.agegrade vs. series.orderby=='agtime'
                if series.orderby == 'time':
                    # get all the results which have been stored in the database for this race/series
                    ### TODO: use series.orderby, series.hightolow
                    dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id).order_by(RaceResult.time).all()
                    numresults = len(dbresults)
                    for rrndx in range(numresults):
                        raceresult = dbresults[rrndx]
                        
                        # set place if it has not been set before
                        # place may have been determined at previous iteration, if a tie was detected
                        if not raceresult.overallplace:
                            thisplace = rrndx+1
                            tieindeces = [rrndx]
                            
                            # detect tie in subsequent results based on rendering,
                            # which rounds to a specific precision based on distance
                            time = render.rendertime(raceresult.time,timeprecision)
                            for tiendx in range(rrndx+1,numresults):
                                if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                                    break
                                tieindeces.append(tiendx)
                            lasttie = tieindeces[-1] + 1
                            for tiendx in tieindeces:
                                numsametime = len(tieindeces)
                                if numsametime > 1 and series.averagetie:
                                    dbresults[tiendx].overallplace = (thisplace+lasttie) / 2.0
                                else:
                                    dbresults[tiendx].overallplace = thisplace
            
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(RaceResult.time).all()
            
                        numresults = len(dbresults)
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                        
                            # set place if it has not been set before
                            # place may have been determined at previous iteration, if a tie was detected
                            if not raceresult.genderplace:
                                thisplace = rrndx+1
                                tieindeces = [rrndx]
                                
                                # detect tie in subsequent results based on rendering,
                                # which rounds to a specific precision based on distance
                                time = render.rendertime(raceresult.time,timeprecision)
                                for tiendx in range(rrndx+1,numresults):
                                    if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                                        break
                                    tieindeces.append(tiendx)
                                lasttie = tieindeces[-1] + 1
                                for tiendx in tieindeces:
                                    numsametime = len(tieindeces)
                                    if numsametime > 1 and series.averagetie:
                                        dbresults[tiendx].genderplace = (thisplace+lasttie) / 2.0
                                    else:
                                        dbresults[tiendx].genderplace = thisplace
            
                    if series.divisions:
                        for gender in ['F','M']:
                            
                            # linear search for correct division
                            for thisdiv in divisions:
                                divlow = thisdiv[0]
                                divhigh = thisdiv[1]
            
                                dbresults = RaceResult.query  \
                                              .filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender,divisionlow=divlow,divisionhigh=divhigh) \
                                              .order_by(racedb.RaceResult.time).all()
                    
                                numresults = len(dbresults)
                                for rrndx in range(numresults):
                                    raceresult = dbresults[rrndx]
            
                                    # set place if it has not been set before
                                    # place may have been determined at previous iteration, if a tie was detected
                                    if not raceresult.divisionplace:
                                        thisplace = rrndx+1
                                        tieindeces = [rrndx]
                                        
                                        # detect tie in subsequent results based on rendering,
                                        # which rounds to a specific precision based on distance
                                        time = render.rendertime(raceresult.time,timeprecision)
                                        for tiendx in range(rrndx+1,numresults):
                                            if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                                                break
                                            tieindeces.append(tiendx)
                                        lasttie = tieindeces[-1] + 1
                                        for tiendx in tieindeces:
                                            numsametime = len(tieindeces)
                                            if numsametime > 1 and series.averagetie:
                                                dbresults[tiendx].divisionplace = (thisplace+lasttie) / 2.0
                                            else:
                                                dbresults[tiendx].divisionplace = thisplace
            
                # process age grade results, ordered by agtime
                elif series.orderby == 'agtime':
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(RaceResult.agtime).all()
            
                        numresults = len(dbresults)
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                        
                            # set place if it has not been set before
                            # place may have been determined at previous iteration, if a tie was detected
                            if not raceresult.agtimeplace:
                                thisplace = rrndx+1
                                tieindeces = [rrndx]
                                
                                # detect tie in subsequent results based on rendering,
                                # which rounds to a specific precision based on distance
                                time = render.rendertime(raceresult.agtime,agtimeprecision)
                                for tiendx in range(rrndx+1,numresults):
                                    if render.rendertime(dbresults[tiendx].agtime,agtimeprecision) != time:
                                        break
                                    tieindeces.append(tiendx)
                                lasttie = tieindeces[-1] + 1
                                for tiendx in tieindeces:
                                    numsametime = len(tieindeces)
                                    if numsametime > 1 and series.averagetie:
                                        dbresults[tiendx].agtimeplace = (thisplace+lasttie) / 2.0
                                        #if dbresults[tiendx].agtimeplace == (thisplace+lasttie) / 2:
                                        #    dbresults[tiendx].agtimeplace = int(dbresults[tiendx].agtimeplace)
                                    else:
                                        dbresults[tiendx].agtimeplace = thisplace

                # process age grade results, ordered by agtime
                elif series.orderby == 'agpercent':
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(RaceResult.agpercent.desc()).all()
            
                        numresults = len(dbresults)
                        #app.logger.debug('orderby=agpercent, club_id={}, race.id={}, series.id={}, gender={}, numresults={}'.format(club_id,race.id,series.id,gender,numresults))
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                            thisplace = rrndx+1                                
                            dbresults[rrndx].agtimeplace = thisplace

            # commit database updates and close transaction
            db.session.commit()
            return success_response(redirect=flask.url_for('seriesresults',raceid=raceid))
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_tabulateresults/<int:raceid>',view_func=AjaxTabulateResults.as_view('_tabulateresults'),methods=['POST'])
#----------------------------------------------------------------------

