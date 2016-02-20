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
from collections import defaultdict, OrderedDict

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename
from datatables import DataTables, ColumnDT
from flask.ext.wtf import Form
from wtforms import SelectField, StringField, IntegerField, BooleanField, validators

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
from datatables_editor import DataTablesEditor, dt_editor_response, get_request_action, get_request_data
from forms import SeriesResultForm, RunnerResultForm
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
class ParameterError(Exception): pass

#######################################################################
class MapDict():
#######################################################################
    '''
    convert dict d to new dict based on mapping
    mapping is dict like {'outkey_n':'inkey_n', 'outkey_m':f(dbrow), ...}

    :param mapping: mapping dict with key for each output field
    '''

    #----------------------------------------------------------------------
    def __init__(self,mapping):
    #----------------------------------------------------------------------
        self.mapping = mapping

    #----------------------------------------------------------------------
    def convert(self,from_dict):
    #----------------------------------------------------------------------
        '''
        convert dict d to new dict based on mapping

        :param from_dict: dict-like object
        :param mapping: dict with keys like {'to1':'from1', ...}
        :rtype: object of same type as from_dict, with the converted keys
        '''

        # create intance of correct type
        to_dict = type(from_dict)()

        # go through keys, skipping the ones which are not present
        for to_key in self.mapping:
            if hasattr(self.mapping[to_key], '__call__'):
                callback = self.mapping[to_key]
                to_dict[to_key] = callback(from_dict)

            # simple map from from_dict field
            else:
                from_key = self.mapping[to_key]
                if from_key in from_dict:
                    to_dict[to_key] = from_dict[from_key]

        return to_dict

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
def getmembertype(runnerid):
#----------------------------------------------------------------------
    '''
    determine member type based on runner field values
    
    :param runnerid: runnerid or None
    
    :rtype: 'member', 'inactive', 'nonmember', ''
    '''
    
    runner = Runner.query.filter_by(id=runnerid).first()

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
class ImportResults():
#######################################################################
    '''
    takes input result and maps to database result

    optional mapping is dict like {'dbattr_n':'inkey_n', 'dbattr_m':'inkey_m', ...}
    if mapping is not present, inresult keys must match dbattrs + dbmetaattrs

    :param club_id: id for club race should be found under
    :param raceid: id for race
    :param mapping: dict with key for each db row to be updated
    '''
    dbattrs = 'place,name,fname,lname,gender,age,city,state,hometown,club,time'.split(',')
    # don't include runnerid or confirmed, as these are updated as side effects of set_initialdisposition()
    dbmetaattrs = 'initialdisposition'.split(',')   
    defaultmapping = dict(zip(dbattrs+dbmetaattrs,dbattrs+dbmetaattrs))
    #----------------------------------------------------------------------
    def __init__(self, club_id, raceid, mapping=defaultmapping):
    #----------------------------------------------------------------------

        # remember what we need later
        self.club_id = club_id

        # mapping method for each database field from input row
        self.map = MapDict(mapping)

        # get race and list of runners who should be included in this race, based on race's membersonly configuration
        self.race = Race.query.filter_by(club_id=club_id,id=raceid).first()
        self.racedatedt = dbdate.asc2dt(self.race.date)
        self.timeprecision,agtimeprecision = render.getprecision(self.race.distance,surface=self.race.surface)

        if len(self.race.series) == 0:
            raise ParameterError, 'Race needs to be included in at least one series to import results'

        # determine candidate pool based on membersonly
        membersonly = self.race.series[0].series.membersonly
        if membersonly:
            self.pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
        else:
            self.pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

        ### all the "work" is here to set up the dbmapping from input result
        # use OrderedDict because some dbattrs depend on others to have been done first (e.g., confirmed must be after initialdisposition)
        # first overwrite a few of these to make sure name, lname, fname, hometown, city, state filled in
        dbmapping = OrderedDict(zip(self.dbattrs,self.dbattrs))
        dbmapping['name']     = lambda inrow: inrow['name'] if inrow.get('name') \
                                else ' '.join([inrow['fname'], inrow['lname']]) if inrow.get('fname') or inrow.get('lname') \
                                else None
        dbmapping['fname']    = lambda inrow: inrow['fname'] if inrow.get('fname') \
                                else split_full_name(inrow['name'])['fname'] if inrow.get('name') \
                                else None
        dbmapping['lname']    = lambda inrow: inrow['lname'] if inrow.get('lname') \
                                else split_full_name(inrow['name'])['lname'] if inrow.get('name') \
                                else None
        dbmapping['hometown'] = lambda inrow: inrow['hometown'] if inrow.get('hometown') \
                                else ', '.join([inrow['city'], inrow['state']]) if inrow.get('city') and inrow.get('state') \
                                else None
        dbmapping['city']     = lambda inrow: inrow['city'] if inrow.get('city') \
                                else inrow['hometown'].split(', ')[0] if inrow.get('hometown') \
                                else None
        dbmapping['state']    = lambda inrow: inrow['state'] if inrow.get('state') \
                                else inrow['hometown'].split(', ')[1] if inrow.get('hometown') \
                                else None
        dbmapping['gender']   = lambda inrow: inrow['gender'].upper() if inrow.get('gender') \
                                else None
        dbmapping['age']      = lambda inrow: int(inrow['age']) if inrow.get('age') \
                                else 0
        dbmapping['time']     = lambda inrow: float(inrow['time'])
        dbmapping['initialdisposition'] = self.set_initialdisposition

        # set up DataTablesEditor object
        # no formmapping needed because we are not creating a form
        self.dte = DataTablesEditor(dbmapping, {})

    #----------------------------------------------------------------------
    def set_initialdisposition(self, inrow):
    #----------------------------------------------------------------------
        '''
        nominally this is a dbmapping function which returns value for initialdisposition
        however, this also has side-effects of updating runnerid and confirmed fields 
        self.runner_choices is updated to include close matches or None as appropriate

        before entry, self.dbresult must be set for the targeted db record

        :param inrow: input row to be translated into dbresult 
        :rtype: initialdisposition
        '''

        # make come convenience assignments
        club_id = self.club_id
        dbresult = self.dbresult
        race = self.race
        racedatedt = dbdate.asc2dt(race.date)

        # need to initialize missed
        missed = []

        # assumes all series for same race have same membersonly
        membersonly = race.series[0].series.membersonly

        # for members or people who were once members, set age based on date of birth in database
        # note this clause will be executed for membersonly races
        candidate = self.pool.findmember(dbresult.name,dbresult.age,self.race.date)
        if candidate:
            # note some candidates' ascdob may come back as None (these must be nonmembers because we have dob for all current/previous members)
            runnername,ascdob = candidate
            
            # set active or inactive member's id
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            dbresult.runnerid = runner.id
        
            # if candidate has renewdate and did not join in time for member's only race, indicate this result isn't used
            if membersonly and runner.renewdate and dbdate.asc2dt(runner.renewdate) > dbdate.asc2dt(self.race.date)+JOIN_GRACEPERIOD:
                    # discard candidate
                    candidate = None
                    
            # runner joined in time for race, or not member's only race
            # if exact match, indicate we have a match
            elif runnername.lower() == dbresult.name.lower():
                # if current or former member
                if ascdob:
                    dbresult.initialdisposition = DISP_MATCH
                    dbresult.confirmed = True
                    # app.logger.debug('    DISP_MATCH')
                    
                # otherwise was nonmember, included from some non memberonly race
                else:
                    # must check current result age against any previous result age
                    thisresultage = dbresult.age
                    if thisresultage:
                        thisracedate = tYmd.asc2dt(self.race.date)
                        pastresult = RaceResult.query.filter_by(club_id=club_id,runnerid=runner.id).first()
                        pastresultage = pastresult.agage
                        pastracedate = tYmd.asc2dt(pastresult.race.date)
                        
                        # make sure this result age is consistent with previous result +/- 1 year
                        deltayears = abs((thisracedate - pastracedate).days / 365.25)
                        deltaage = abs(int(thisresultage) - pastresultage)
                        if abs(deltaage - deltayears) <= 1:
                            dbresult.initialdisposition = DISP_MATCH
                            dbresult.confirmed = True
                            # app.logger.debug('    DISP_MATCH')

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
                    # app.logger.debug('    DISP_CLOSE')
                    
                # results name vs this runner id has been excluded
                else:
                    candidate = None
                           
        # didn't find runner on initial search, or candidate was discarded
        if not candidate:
            # clear runnerid in case we discarded candidate above
            dbresult.runnerid = None

            # favor active members, then inactive members
            # note: nonmembers are not looked at for missed because filtermissed() depends on DOB
            missed = self.pool.getmissedmatches()
            # app.logger.debug('  self.pool.getmissedmatches() = {}'.format(missed))
            
            # don't consider 'missed matches' where age difference from result is too large, or excluded
            # app.logger.debug('  missed before filter = {}'.format(missed))
            missed = filtermissed(club_id,missed,race.date,dbresult.age)
            # app.logger.debug('  missed after filter = {}'.format(missed))

            # if there remain are any missed results, indicate missed (due to age difference)
            # or missed (due to new member proposed for not membersonly)
            if len(missed) > 0 or not membersonly:
                dbresult.initialdisposition = DISP_MISSED
                dbresult.confirmed = False
                # app.logger.debug('    DISP_MISSED')
                
            # otherwise, this result isn't used
            else:
                dbresult.initialdisposition = DISP_NOTUSED
                dbresult.confirmed = True
                # app.logger.debug('    DISP_NOTUSED')

        # this needs to be the same as what was already stored in the record
        return dbresult.initialdisposition
    
    #----------------------------------------------------------------------
    def update_dbresult(self, inresult, dbresult):
    #----------------------------------------------------------------------
        '''
        updates dbresult based on inresult

        :param inresult: dict-like object which has keys per mapping defined at instantiation
        :param dbresult: ManagedResult instance to be initialized or updated

        :rtype: missed - list of missed matches if not exact match
        '''

        # convert inresult keys
        thisinresult = self.map.convert(inresult)
        app.logger.debug('thisinresult={}'.format(thisinresult))

        # this makes the dbresult accessible to the dbmapping functions
        self.dbresult = dbresult

        # update dbresult - this executes dbmapping function for each dbresult attribute
        self.dte.set_dbrow(thisinresult, dbresult)

        # return missed matches for select rendering
        runner_choices = getrunnerchoices(self.club_id, self.race, self.pool, dbresult)

        return runner_choices

#----------------------------------------------------------------------
def getrunnerchoices(club_id, race, pool, result):
#----------------------------------------------------------------------
    '''
    get runner choice possibilies for rendering on editresults

    :param club_id: club id
    :param race: race entry from database
    :param pool: candidate pool
    :param result: database result
    :rtype: choices for use in Standings Name select
    '''

    membersonly = race.series[0].series.membersonly
    racedatedt = dbdate.asc2dt(race.date)
    thisdisposition = result.initialdisposition
    thisrunnerid = result.runnerid

    thisrunnerchoice = [(None,'[not included]')]

    # need to repeat logic from AjaxImportResults() because AjaxImportResults() may leave null in runnerid field of managedresult
    candidate = pool.findmember(result.name,result.age,race.date)
    
    runner = None
    runnername = ''
    if thisdisposition in [DISP_MATCH,DISP_CLOSE]:
        # found a possible runner
        if candidate:
            runnername,ascdob = candidate
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            try:
                dobdt = dbdate.asc2dt(ascdob)
                nameage = '{} ({})'.format(runner.name,timeu.age(racedatedt,dobdt))
            # possibly no date of birth
            except ValueError:
                nameage = runner.name
            thisrunnerchoice.append([runner.id,nameage])
        
        # see issue #183
        else:
            pass    # TODO: this is a bug -- that to do?

    # didn't find runner, what were other possibilities?
    elif thisdisposition == DISP_MISSED:
        # this is possible because maybe (new) member was chosen in prior use of editparticipants
        if candidate:
            runnername,ascdob = candidate
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            try:
                dobdt = dbdate.asc2dt(ascdob)
                nameage = '{} ({})'.format(runner.name,timeu.age(racedatedt,dobdt))
            # possibly no date of birth
            except ValueError:
                nameage = runner.name
            thisrunnerchoice.append([runner.id,nameage])
        
        # this handles case where age mismatch was chosen in prior use of editparticipants
        elif thisrunnerid:
            runner = Runner.query.filter_by(club_id=club_id,id=thisrunnerid).first()

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

    return thisrunnerchoice

#######################################################################
class FixupResult():
#######################################################################

    #----------------------------------------------------------------------
    def __init__(self, race, pool, result, timeprecision):
    #----------------------------------------------------------------------
        '''
        fix up result
        
        fix up the following:
          * time gets converted from seconds
          * determine member matching, set runnerid choices and initially selected choice
          * based on matching, set disposition

        :param race: race record
        :param pool: pool from which candidates come from
        :param result: record from runner table or None
        :param timeprecision: precision for time rendering
        
        :rtype: runner, time, disposition, runnerchoice, runnerid
        '''

        self.result = result
        club_id = flask.session['club_id']

        # make time renderable
        self.time = render.rendertime(result.time,timeprecision)

        # get choices for this result
        self.runnerchoice = getrunnerchoices(club_id, race, pool, result)

    #----------------------------------------------------------------------
    def renderable_result(self):
    #----------------------------------------------------------------------
        # make renderable result
        # include all the metadata for this result
        return {
            'id' : self.result.id,
            'place' : self.result.place,
            'resultname' : self.result.name,
            'gender' : self.result.gender,
            'age' : self.result.age,
            'disposition' : self.result.initialdisposition,
            'confirm' : self.result.confirmed,
            'runnerid' : self.result.runnerid,
            'hometown' : self.result.hometown,
            'club' : self.result.club,
            'time' : self.time,
        }


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
            
            # verify user can write the data, otherwise abort
            # TODO: maybe readcheck is ok, but javascript needs to be reviewed carefully
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # get all the results, and the race record
            results = []
            results = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).order_by('time').all()

            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(flask.url_for('manageraces'))

            # determine precision for rendered output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
            # active is ClubMember object for active members; if race isn't for members only nonmember is ClubMember object for nonmembers
            membersonly = race.series[0].series.membersonly
            if membersonly:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

            # convert members for page select
            memberrecs = pool.getmembers()
            membernames = []
            memberages = {}
            memberagegens = {}
            for thismembername in memberrecs:
                # get names and ages associated with each name
                for thismember in memberrecs[thismembername]:
                    racedate = tYmd.asc2dt(race.date)
                    try:
                        dob = tYmd.asc2dt(thismember['dob'])
                        age = timeu.age(racedate,dob)
                        nameage = u'{} ({})'.format(thismember['name'], age)
                    # maybe no dob
                    except ValueError:
                        nameage = thismember['name']

                    # memberages is used for picklist on missed and similar dispositions
                    memberages[thismember['id']] = nameage

                    # set up to retrieve age, gender for this member
                    memberagegens.setdefault(thismembername,[])
                    memberagegens[thismembername].append({'age': age, 'gender':thismember['gender']})

                    # note only want to save the names for use on the name select
                    # annotate for easy sort
                    # TODO: is this an issue if two with the same name have different capitalization?
                    thismemberoption = (thismember['name'].lower(), {'label':thismember['name'],'value':thismember['name']})
                    if thismemberoption not in membernames:
                        membernames.append(thismemberoption)

            # sort membernames and remove annotation
            membernames.sort()
            membernames = [m[1] for m in membernames]

            # collect data for table
            tabledata = []
            tableselects = {}

            # fix up the following:
            #   * time gets converted from seconds
            #   * determine member matching, set runnerid choices and initially selected choice
            #   * based on matching, set disposition
            for result in results:
                r = FixupResult(race, pool, result, timeprecision)
                thisresult = r.renderable_result()

                runner = Runner.query.filter_by(club_id=club_id,id=result.runnerid).first()
                thisresult['membertype'] = getmembertype(result.runnerid)

                tabledata.append(thisresult)

                # use select field unless 'definite', or membersonly and '' (means definitely didn't find)
                if writecheck.can() and ((result.initialdisposition == DISP_MISSED or result.initialdisposition == DISP_CLOSE) 
                                         or (not membersonly and result.initialdisposition != DISP_MATCH)):
                    tableselects[result.id] = r.runnerchoice

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('editparticipants.html', 
                                         race=race, 
                                         data=tabledata, 
                                         selects=tableselects,
                                         membernames=membernames, 
                                         memberages=memberages, 
                                         memberagegens=memberagegens,
                                         crudapi=flask.url_for('_editparticipants',raceid=0)[0:-1],  
                                         fieldapi=flask.url_for('_updatemanagedresult',resultid=0)[0:-1],
                                         membersonly=membersonly, 
                                         inhibityear=True,inhibitclub=True,
                                         writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/editparticipants/<int:raceid>',view_func=EditParticipants.as_view('editparticipants'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class AjaxEditParticipants(MethodView):
#######################################################################
    decorators = [login_required]
    formfields = 'age,club,confirm,disposition,gender,hometown,id,place,resultname,runnerid,time'.split(',')
    dbfields   = 'age,club,confirmed,initialdisposition,gender,hometown,id,place,name,runnerid,time'.split(',')
    #----------------------------------------------------------------------
    def post(self, raceid):
    #----------------------------------------------------------------------
        # prepare for possible errors
        error = ''
        fielderrors = []

        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                cause = 'operation not permitted for user'
                return dt_editor_response(error=cause)
            
            # handle create, edit, remove
            action = get_request_action(request.form)

            # get data from form
            data = get_request_data(request.form)
            app.logger.debug('action={}, data={}, form={}'.format(action, data, request.form))

            if action not in ['create','edit','remove']:
                db.session.rollback()
                cause = 'unknown action "{}"'.format(action)
                app.logger.warning(cause)
                return dt_editor_response(error=cause)

            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if not race:
                db.session.rollback()
                cause = 'race id={} does not exist for this club'.format(raceid)
                app.logger.warning(cause)
                return dt_editor_response(error=cause)

            if len(race.series) == 0:
                db.session.rollback()
                cause =  'Race needs to be included in at least one series to import results'
                app.logger.error(cause)
                return dt_editor_response(error=cause)
            
            # determine precision for time output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)

            # dataTables Editor helper
            dbmapping = dict(zip(self.dbfields,self.formfields))
            dbmapping['time']     = lambda inrow: raceresults.normalizeracetime(inrow['time'], race.distance)

            formmapping = dict(zip(self.formfields,self.dbfields))
            formmapping['time'] = lambda dbrow: render.rendertime(dbrow.time,timeprecision)
            formmapping['membertype'] = lambda dbrow: getmembertype(dbrow.runnerid)

            # prepare to import results to database
            importresults = ImportResults(club_id, raceid, dbmapping)

            # prepare to send database results to browser
            # dbmapping is not needed for this
            dte = DataTablesEditor({}, formmapping)
            
            # loop through data, determining best match
            responsedata = []
            runnerchoices = {}
            for resultid in data:
                thisdata = data[resultid]
                # create of update
                if action!='remove':
                    # check gender
                    if thisdata['gender'].upper() not in ['M','F']:
                        fielderrors.append({'name' : 'gender', 'status' : 'Gender must be chosen'})

                    # check for hh:mm:ss time field error
                    try:
                        dbtime = timeu.timesecs(thisdata['time'])
                    except ValueError:
                        fielderrors.append({'name' : 'time', 'status' : 'Time must be in format [hh:]mm:ss'})

                    # verify age is a number
                    try:
                        age = int(thisdata['age'])
                    except:
                        fielderrors.append({'name' : 'age', 'status' : 'Age must be a number'})

                    # get or create database entry
                    if action=='edit':
                        dbresult = ManagedResult.query.filter_by(id=resultid).first()
                    # create
                    else:
                        dbresult = ManagedResult(club_id,race.id)
                    
                    # fill in the data from the form
                    runner_choices = importresults.update_dbresult(thisdata, dbresult)

                    # save the new result to force dbresult.id assignment
                    if action=='create':
                        db.session.add(dbresult)
                        db.session.flush()  # needed to update id

                    # set up response object
                    thisrow = dte.get_response_data(dbresult)
                    responsedata.append(thisrow)
                    app.logger.debug('thisrow={}'.format(thisrow))

                    # update thisresult.runnerchoice for resultid
                    runnerchoices[dbresult.id] = runner_choices
                    app.logger.debug('resultid={} runnerchoices={}'.format(dbresult.id, runner_choices))

                # remove
                else:
                    resultid = thisdata['id']
                    dbresult = ManagedResult.query.filter_by(id=resultid).first()
                    app.logger.debug('deleting id={}, name={}'.format(resultid,dbresult.name))
                    db.session.delete(dbresult)

            # commit database updates and close transaction
            db.session.commit()
            return dt_editor_response(data=responsedata, choices=runnerchoices)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            if fielderrors:
                cause = 'please check indicated fields'
            elif error:
                cause = error
            else:
                cause = traceback.format_exc()
                app.logger.error(traceback.format_exc())
            return dt_editor_response(data=[], error=cause, fieldErrors=fielderrors)
#----------------------------------------------------------------------
app.add_url_rule('/_editparticipants/<int:raceid>',view_func=AjaxEditParticipants.as_view('_editparticipants'),methods=['POST'])
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
            
            # determine precision for rendered output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
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
                thistime = render.rendertime(result.time,timeprecision)
                thisagtime = render.rendertime(result.agtime,agtimeprecision)
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
                timeprecision,agtimeprecision = render.getprecision(result.race.distance,surface=result.race.surface)
                thisdistance = result.race.distance
                thistime = render.rendertime(result.time,timeprecision)
                thisagtime = render.rendertime(result.agtime,agtimeprecision)
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


#----------------------------------------------------------------------
def allowed_file(filename):
#----------------------------------------------------------------------
    return '.' in filename and filename.split('.')[-1] in ['xls','xlsx','txt','csv']

#----------------------------------------------------------------------
def fix_dbresult_fields(managedresult):
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

    # gender needs to be upper case
    if managedresult.gender:
        managedresult.gender = managedresult.gender.upper()


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

            if len(race.series) == 0:
                db.session.rollback()
                cause =  'Race needs to be included in at least one series to import results'
                app.logger.error(cause)
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
                        # app.logger.debug('nonmember={}/{} nonmemberresults={}'.format(nonmember.name,nonmember.id,nonmemberresults))
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
                cause = '{}'.format(e)
                app.logger.warning(cause)
                return failure_response(cause=cause)
                
            # how did this happen?  check allowed_file() for bugs
            except raceresults.dataError,e:
                db.session.rollback()
                #cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext,resultfile.filename,resultpathname)
                cause =  'Program Error: {}'.format(e)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # create importer
            importresults = ImportResults(club_id, raceid)
            
            # collect results from resultsfile
            numentries = 0
            dbresults = []
            logfirst = True
            while True:
                try:
                    fileresult = rr.next()
                    if logfirst:
                        app.logger.debug('first file result {}'.format(fileresult))
                        logfirst = False
                    dbresult   = ManagedResult(club_id,raceid)

                    # update database entry
                    runner_choices = importresults.update_dbresult(fileresult, dbresult)

                    # add to database
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
            cause = traceback.format_exc()
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
            field = flask.request.args.get('field','[not supplied]')
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
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)

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
                        timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
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

