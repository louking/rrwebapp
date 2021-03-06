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
import os
from datetime import timedelta
from time import time
import traceback
from collections import OrderedDict
from urllib import urlencode
from copy import copy
import xml.etree.ElementTree as ET

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask_login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename
from sqlalchemy import func, cast
from attrdict import AttrDict

# home grown
from . import app
from . import celery
import racedb
from loutilities.tables import DataTables, ColumnDT
from accesscontrol import UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response
from request import addscripts, crossdomain
from appldirs import UPLOAD_TEMP_DIR
from apicommon import MapDict
from nav import productname

# module specific needs
import raceresults
import clubmember
from crudapi import CrudApi
from request import annotatescripts
from racedb import Runner, ManagedResult, RaceResult, Race, Exclusion, Series, Divisions, Club, dbdate
from racedb import rendertime, renderfloat, rendermember, renderlocation, renderseries
from services import ServiceAttributes
from racedb import RaceResultService, ApiCredentials
from location import LocationServer, get_distance
from datatables_utils import DataTablesEditor, dt_editor_response, get_request_action, get_request_data
from forms import SeriesResultForm
from loutilities.namesplitter import split_full_name
import loutilities.renderrun as render
from loutilities import timeu, agegrade

tYmd = timeu.asctime('%Y-%m-%d')
tmdy = timeu.asctime('%m/%d/%y')

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
        membersonly = self.race.series[0].membersonly
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
        membersonly = race.series[0].membersonly

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

    membersonly = race.series[0].membersonly
    racedatedt = dbdate.asc2dt(race.date)

    # object should have either disposition or initialdisposition
    # see http://stackoverflow.com/questions/610883/how-to-know-if-an-object-has-an-attribute-in-python
    try:
        thisdisposition = result.disposition
    except AttributeError:
        thisdisposition = result.initialdisposition

    # object should have either name or resultname
    try:
        thisname = result.name
    except AttributeError:
        thisname = result.resultname

    # current runnerid may change later depending on choice
    thisrunnerid = result.runnerid
    thisrunnerchoice = [(None,'[not included]')]

    # need to repeat logic from AjaxImportResults() because AjaxImportResults() may leave null in runnerid field of managedresult
    candidate = pool.findmember(thisname,result.age,race.date)
    
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
        # it's possible that thisname == runnername if (new) member was added in prior use of editparticipants
        if thisname != runnername:
            thisrunnerchoice.append(('new','{} (new)'.format(thisname)))

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
                
            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' not found for this club".format(race.name)
                app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(url_for('manageraces'))

            # active is ClubMember object for active members; if race isn't for members only nonmember is ClubMember object for nonmembers
            membersonly = race.series[0].membersonly
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
                        age = ''    
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

            # start with empty data
            tabledata = []
            tableselects = {}

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('editparticipants.html', 
                                         race=race, 
                                         data=url_for('_editparticipants',raceid=raceid), 
                                         selects=tableselects,
                                         membernames=membernames, 
                                         memberages=memberages, 
                                         memberagegens=memberagegens,
                                         crudapi=url_for('_editparticipantscrud',raceid=0)[0:-1],  
                                         fieldapi=url_for('_updatemanagedresult',resultid=0)[0:-1],
                                         membersonly=membersonly, 
                                         inhibityear=True,inhibitclub=True,
                                         pagejsfiles=annotatescripts(['editparticipants.js']),
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
                
            # determine precision for rendered output, race is needed to fix up result as well
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
            # mData must match columns in RaceResults[.js].editparticipants
            columns = [
                ColumnDT(ManagedResult.id,                 mData='id',          search_method='none'),
                ColumnDT(ManagedResult.place,              mData='place'),
                ColumnDT(ManagedResult.name,               mData='resultname'),
                ColumnDT(ManagedResult.gender,             mData='gender',      search_method='none'),
                ColumnDT(ManagedResult.age,                mData='age',         search_method='none'),
                ColumnDT(ManagedResult.initialdisposition, mData='disposition', search_method='yadcf_multi_select'),

                # ColumnDT(rendermember(Runner.member), mData='membertype', search_method='none'),
                ColumnDT(rendermember(ManagedResult.runnerid), mData='membertype', search_method='none'),

                # the odd confirmed lambda filter prevents a string 'True' or 'False' from being sent
                ColumnDT(ManagedResult.confirmed,           mData='confirm',            search_method='none'),
                ColumnDT(ManagedResult.runnerid,            mData='runnerid'),
                # next two, suppress 'None' rendering
                ColumnDT(ManagedResult.hometown,            mData='hometown'),
                ColumnDT(ManagedResult.club,                mData='club'),
                ColumnDT(rendertime(ManagedResult.time), mData='time'),
            ]

            def set_yadcf_data():
                getcol = lambda colname: [col.mData for col in columns].index(colname)

                # add yadcf filter
                matches = [row.initialdisposition for row in db.session.query(ManagedResult.initialdisposition)
                    .filter_by(club_id=club_id, raceid=raceid).distinct().all()]
                yadcf_data = [('yadcf_data_{}'.format(getcol('disposition')), matches)]

                return yadcf_data

            params = request.args.to_dict()
            query = db.session.query().select_from(ManagedResult).filter_by(club_id=club_id,raceid=raceid)
            rowTable = DataTables(params, query, columns, set_yadcf_data=set_yadcf_data)

            # prepare for match filter
            # need to use db.session to access query function
            # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
            # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
            # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
            # format depends on type of select

            # add to returned output
            output_result = rowTable.output_result()

            # determine if race is for members only
            # then get appropriate pool of runners for possible inclusion in tableselects
            membersonly = race.series[0].membersonly
            if membersonly:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = clubmember.DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

            # determine possible choices for this runner if not definite
            tableselects = {}
            for result in output_result['data']:
                # use select field unless 'definite', or membersonly and '' (means definitely didn't find)
                r = AttrDict(result)    # for convenience because getrunnerchoices assumes object not dict
                if writecheck.can() and ((r.disposition == DISP_MISSED or r.disposition == DISP_CLOSE) 
                                         or (not membersonly and r.disposition != DISP_MATCH)):
                    tableselects[r.id] = getrunnerchoices(club_id, race, pool, r)

            # add standings name selects and names
            output_result['tableselects'] = tableselects

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_editparticipants/<int:raceid>',view_func=AjaxEditParticipants.as_view('_editparticipants'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class AjaxEditParticipantsCRUD(MethodView):
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
app.add_url_rule('/_editparticipantscrud/<int:raceid>',view_func=AjaxEditParticipantsCRUD.as_view('_editparticipantscrud'),methods=['POST'])
#----------------------------------------------------------------------

###########################################################################################
# editexclusions endpoint
###########################################################################################

editexclusions_dbattrs = 'id,club_id,foundname,runner'.split(',')
editexclusions_formfields = 'rowid,club_id,foundname,runner'.split(',')
editexclusions_dbmapping = dict(zip(editexclusions_dbattrs, editexclusions_formfields))
editexclusions_formmapping = dict(zip(editexclusions_formfields, editexclusions_dbattrs))

editexclusions = CrudApi(pagename='edit exclusions',
                endpoint='editexclusions',
                dbmapping=editexclusions_dbmapping,
                formmapping=editexclusions_formmapping,
                permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
                dbtable=Exclusion,
                clientcolumns=[
                    {'data': 'foundname', 'name': 'foundname', 'label': 'Result Name',
                     },
                    {'data': 'runner', 'name': 'runner', 'label': 'Member Name', 'type': 'select2',
                     '_treatment': {'relationship':
                         {
                             'dbfield': 'runner',
                             'fieldmodel': Runner,
                             'labelfield': 'name',
                             'formfield': 'runner',
                             'uselist': False,
                             'queryparams': lambda: {'club_id': flask.session['club_id']}
                         }
                     },
                     },
                ],
                serverside=False,
                byclub=True,
                addltemplateargs={'inhibityear': True},
                idSrc='rowid',
                buttons=['remove', 'csv',
                         ],
                )
editexclusions.register()


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
                return flask.redirect(url_for('manageraces'))
            
            # determine precision for rendered output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
            # get all the results, and the race record
            results = []
            for series in race.series:
                seriesid = series.id
                seriesresults = RaceResult.query.filter_by(raceid=raceid,seriesid=seriesid).order_by(series.orderby).all()
                # this is easier, code-wise, than using sqlalchemy desc() function
                if series.hightolow:
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
# following functions used to set up pretablehtml
#######################################################################

#----------------------------------------------------------------------
def indent(elem, level=0):
#----------------------------------------------------------------------
# in-place prettyprint formatter
# see http://effbot.org/zone/element-lib.htm#prettyprint
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

#----------------------------------------------------------------------
def addfilters(filters, filterlines):
#----------------------------------------------------------------------
    '''
    add filters and other elements to an html element

    filterlines = [line_n_elements, ...]

        where line_n_elements = [element_i, ...]

            where element_i =
                {'id':filter_j_id, 'text':filter_j_text}
                        OR
                ET.Element

    :param filters: html element to add filters and other elements
    :param filterlines: list of lines, each a list of elements as above
    '''

    # loop once for each line, use i as index so we can detect last one
    for i in range(len(filterlines)):
        line = filterlines[i]

        # loop once for each element on the line
        for el in line:
            if type(el) == dict:
                thisel = ET.SubElement(filters, 'label', attrib={'class' : 'Label'})
                thisel.text = el['text']
                spanel = ET.SubElement(filters, 'span', attrib={'id' : el['id'], 'class' : '_rrwebapp-filter'})
            else:
                filters.append(el)
        
        # add two breaks to each line except for last line
        if i < len(filterlines)-1:
            ET.SubElement(filters, 'br')
            ET.SubElement(filters, 'br')

#######################################################################
class RunnerResults(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)
            # NOTE: session variables are updated in nav.py

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

            # limit results to those recorded by rrwebapp
            resultfilter['source'] = productname

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [
                    { 'data': 'name',           'name': 'name',             'label': 'Name' },
                    { 'data': 'series',         'name': 'series',           'label': 'Series' }, 
                    { 'data': 'date',           'name': 'date',             'label': 'Date',        'className': 'dt-body-center' },
                    { 'data': 'race',           'name': 'race',             'label': 'Race'},
                    { 'data': 'miles',          'name': 'miles',            'label': 'Miles',       'className': 'dt-body-center' },
                    { 'data': 'gender',         'name': 'gender',           'label': 'Gen',         'className': 'dt-body-center' },
                    { 'data': 'age',            'name': 'age',              'label': 'Age',         'className': 'dt-body-center' },
                    { 'data': 'genderplace',    'name': 'genderplace',      'label': 'Gen Place',   'className': 'dt-body-center' },
                    { 'data': 'division',       'name': 'division',         'label': 'Div',         'className': 'dt-body-center' },
                    { 'data': 'divisionplace',  'name': 'divisionplace',    'label': 'Div Place',   'className': 'dt-body-center' },
                    { 'data': 'time',           'name': 'time',             'label': 'Time',        'className': 'dt-body-center' },
                    { 'data': 'pace',           'name': 'pace',             'label': 'Pace',        'className': 'dt-body-center' },
                    { 'data': 'agtime',         'name': 'agtime',           'label': 'AG Time',     'className': 'dt-body-center' },
                    { 'data': 'agpercent',      'name': 'agpercent',        'label': 'AG %age',     'className': 'dt-body-center' },
                ],
                'ordering': True,
                'serverSide': True,
                'order': [0,'asc'],
                # 'search' : { 'regex' : True },   # to test sqlalchemy-datatables global search feature
            }

            buttons = [ 'csv' ]

            # no external filters if a runner was specified
            if runnerid:
                pretablehtml = ''
                options = {'dtopts': dt_options}

            # no runner was specified, yes we should be filtering
            else:
                pretablehtml = '''
                    <div class="TextLeft W7emLabel">
                      <div>
                        <label class="Label">Name:</label><span id="_rrwebapp_filtername" class="_rrwebapp-filter"></span>
                        <label class="Label">Series:</label><span id="_rrwebapp_filterseries" class="_rrwebapp-filter"></span>
                        <label class="Label">Gender:</label><span id="_rrwebapp_filtergender" class="_rrwebapp-filter"></span>
                      </div>
                    </div>
                '''
                # set up yadcf
                getcol = lambda name: [col['name'] for col in dt_options['columns']].index(name)
                yadcf_options = [
                    {
                        'column_number':getcol('name'),
                        'filter_container_id':"_rrwebapp_filtername",
                        'filter_type':"multi_select",
                        'select_type': 'select2',
                        'select_type_options': {
                            'width': '30em',
                        },
                        'filter_reset_button_text': 'all',
                    },{
                        'column_number':getcol('series'),
                        'filter_container_id':"_rrwebapp_filterseries",
                        'filter_reset_button_text': 'all',
                    },{
                        'column_number':getcol('gender'),
                        'filter_container_id':"_rrwebapp_filtergender",
                        'filter_reset_button_text': 'all',
                    }
                ]
                options = {'dtopts': dt_options, 'yadcfopts': yadcf_options}

          
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html',
                                         pagename=pagename,
                                         pretablehtml=pretablehtml,
                                         # serverSide must be True to pass url
                                         # add the request args to the ajax function
                                         tabledata=url_for('_results')+'?'+urlencode(request.args),
                                         tablebuttons= buttons,
                                         tablefiles=None,
                                         options = options,
                                         inhibityear=True,inhibitclub=True,
                                         )

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/results',view_func=RunnerResults.as_view('results'),methods=['GET'])
#----------------------------------------------------------------------


#----------------------------------------------------------------------
def renderage(result):
#----------------------------------------------------------------------
    '''
    render age string for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
    except:
        thisage = ''

    return thisage

#----------------------------------------------------------------------
def renderagtime(result):
#----------------------------------------------------------------------
    '''
    render age grade time for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
        agpercent, agtime, agfactor = ag.agegrade(thisage, result.runner.gender, result.race.distance, result.time)
        agtime = render.rendertime(agtime,0)
    except:
        agtime = ''

    return agtime

#----------------------------------------------------------------------
def renderagpercent(result):
#----------------------------------------------------------------------
    '''
    render age grade percentage for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
        agpercent, agtime, agfactor = ag.agegrade(thisage, result.runner.gender, result.race.distance, result.time)
        agpercent = '{:.2f}%'.format(agpercent)
    except:
        agpercent = ''

    return agpercent

#----------------------------------------------------------------------
def renderintstr(cell):
#----------------------------------------------------------------------
    '''
    render int string for cell
    any exceptions returns 0

    :param cell: cell with int probably
    :rtype: int (hopefully)
    '''

    try:
        this = int(cell)
    except:
        this = 0

    return this

#----------------------------------------------------------------------
def rendermembertype(result):
#----------------------------------------------------------------------
    '''
    render membertype

    :param result: result from ManagedResult
    :rtype: string for rendering
    '''

    # if runner is indicated, find out whether runner is a member
    if result.runnerid:
        runner = Runner.query.filter_by(id=result.runnerid).first()
        if runner.member:
            this = 'member'
        else:
            this = 'nonmember'
    else:
        this = ''

    return this

#######################################################################
class AjaxRunnerResults(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    @crossdomain(origin='*')
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)

            # filter on valid runnerid, if present
            resultfilter = {}
            runnerfilter = {}
            seriesfilter = {}
            name = None
            pagename = 'Results'
            if runnerid:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    resultfilter['runnerid'] = runnerid
                    runnerfilter['id'] = runnerid
                    name = runner.name
                    pagename = '{} Results'.format(name)

            # filter on club, if present
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    resultfilter['club_id'] = club.id
                    runnerfilter['club_id'] = club.id
                    seriesfilter['club_id'] = club.id

            # need to filter after the fact for series, because the seriesid is different for different years
            if seriesarg:
                series = Series.query.filter_by(name=seriesarg).first()
                if series:
                    seriesfilter['name'] = series.name
                    app.logger.debug('filter by series {}'.format(seriesarg))

            # limit results to that recorded by rrwebapp
            resultfilter['source'] = productname

            columns = [
                ColumnDT(Runner.name,                mData='name'),
                ColumnDT(Series.name,                mData='series'),
                ColumnDT(Race.date,                  mData='date'),
                ColumnDT(Race.name,                  mData='race'),
                ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='none'),
                ColumnDT(Runner.gender,              mData='gender',             search_method='none'),
                ColumnDT(RaceResult.agage,           mData='age',                search_method='none'),
                ColumnDT(RaceResult.genderplace,     mData='genderplace',        search_method='none'),
                ColumnDT(func.concat(RaceResult.divisionlow, '-', RaceResult.divisionhigh), mData='division', search_method='none'),
                ColumnDT(RaceResult.divisionplace, mData='divisionplace', search_method='none'),
                ColumnDT(rendertime(RaceResult.time), mData='time', search_method='none'),
                ColumnDT(rendertime(RaceResult.time / Race.distance), mData='pace', search_method='none'),
                ColumnDT(rendertime(RaceResult.agtime), mData='agtime', search_method='none'),
                ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 1), '%'), mData='agpercent', search_method='none'),
            ]

            params = request.args.to_dict()
            query = db.session.query().select_from(RaceResult).filter_by(**resultfilter).join("runner").join("series").filter_by(**seriesfilter).join("race")
            rowTable = DataTables(params, query, columns)

            # prepare for name, series and gender filter
            # need to use db.session to access query function
            # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
            # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
            # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
            # format depends on type of select
            names = [row.name for row in db.session.query(Runner.name).filter_by(**runnerfilter).distinct().all()]
            series = [row.name for row in db.session.query(Series.name).filter_by(**seriesfilter).distinct().all()]
            genders = ['M','F']

            # add yadcf filter
            getcol = lambda name: [col.mData for col in columns].index(name)
            output_result = rowTable.output_result()
            output_result['yadcf_data_{}'.format(getcol('name'))] = names
            output_result['yadcf_data_{}'.format(getcol('series'))] = series
            output_result['yadcf_data_{}'.format(getcol('gender'))] = genders

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_results',view_func=AjaxRunnerResults.as_view('_results'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class RunnerResultsChart(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)

            # filter on club, if present
            club_id = None
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    club_id = club.id

            elif 'club_id' in flask.session:
                club_id = flask.session['club_id']

            if club_id is not None:
                readcheck = ViewClubDataPermission(club_id)
                adminuser = readcheck.can()

            else:
                adminuser = False

            # filter on valid runnerid, if present
            resultfilter = {}
            name = None
            pagename = 'Results Analysis'

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"dt-chart-table dt-chart-tabledisplay dt-hide"<"H"lBpr>t<"F"i>>',
                'columns': [
                    { 'data': 'date',           'name': 'date',             'label': 'Date',        'className': 'dt-body-center dt-chart-nowrap'},
                    { 'data': 'runnerid',       'name': 'runnerid',         'label': 'Runner ID',   'visible': False },
                    { 'data': 'name',           'name': 'name',             'label': 'Name',        'visible': False },
                    { 'data': 'series',         'name': 'series',           'label': 'Series',      'className': 'dt-chart-nowrap' }, 
                    { 'data': 'race',           'name': 'race',             'label': 'Race',        'className': 'dt-chart-nowrap'},
                    { 'data': 'miles',          'name': 'miles',            'label': 'Miles',       'className': 'dt-body-center' },
                    { 'data': 'age',            'name': 'age',              'label': 'Age',         'className': 'dt-body-center' },
                    { 'data': 'time',           'name': 'time',             'label': 'Time',        'className': 'dt-body-center' },
                    { 'data': 'pace',           'name': 'pace',             'label': 'Pace',        'className': 'dt-body-center' },
                    { 'data': 'agtime',         'name': 'agtime',           'label': 'AG Time',     'className': 'dt-body-center' },
                    { 'data': 'agpercent',      'name': 'agpercent',        'label': 'AG %age',     'className': 'dt-body-center' },
                ],
                'language' : {
                    'emptyTable': 'no results found for current selection',
                    'zeroRecords': 'no results found for current selection',
                },
                'ordering': True,
                'serverSide': True,
                'order': [0,'asc'],
                # NOTE: cannot use paging because we need to display all points on the chart
                'paging': False,
            }

            # some columns only available if user is logged in and has visibility to this club
            if adminuser:
                dt_options['columns'] += [
                            { 'data': 'location',    'name': 'location',      'label': 'Location'},
                            { 'data': 'source',      'name': 'source',        'label': 'Source',     'className': 'dt-body-center' },
                            { 'data': 'sourceid',    'name': 'sourceid',      'label': 'Source ID',  'className': 'dt-body-center' },
                        ]

            # set up pretablehtml
            ## set up some html elements to be used pretable
            aglink = ET.Element('a', attrib={'class' : "dt-chart-age-grade-link", 'href' : "https://usatfmasters.org/wp/2018/08/age-grading/",
                                'target' : '_blank'})
            aglink.text = 'learn about age grading'
            charttablebutton = ET.Element('button', attrib={'class' : 'dt-chart-display-button', 'type' : 'button'})
            charttablebutton.text = 'table'
            progressbar = ET.Element('div', attrib={'id' : 'progressbar'})

            ## list of lines for filters, each are represented with list of dicts having id, text;
            ## or ET.ElementTree instances to be placed on line
            filterlines = []
            filterlines.append([
                {'id' : "_rrwebapp_filtername", 'text' : 'Name (age):'},
                {'id' : "_rrwebapp_filterseries", 'text' : 'Series:'},
                aglink,
            ])
            filterlines.append([
                {'id' : "_rrwebapp_filterdate", 'text' : 'Date (yyyy-mm-dd):'},
                {'id' : "_rrwebapp_filterdistance", 'text' : 'Dist (miles):'},
                {'id' : "_rrwebapp_filteragpercent", 'text' : 'Age Grade %age:'},
            ])
            if adminuser:
                filterlines.append([
                    {'id' : "_rrwebapp_filtersource", 'text' : 'Source:'},
                    {'id' : "_rrwebapp_filtersourceid", 'text' : 'Source ID:'},
                ])
            filterlines.append([
                charttablebutton,
                progressbar,
            ])

            ## use ElementTree to set up html, based on filterlines configured above
            pretable = ET.Element('div', attrib={'class' : 'TextLeft PL20pxLabel'})
            filters = ET.SubElement(pretable, 'div', attrib={'class' : "dt-chart-filters"})
            addfilters(filters, filterlines)

            ## render the html nicely
            indent(pretable)
            pretablehtml = ET.tostring(pretable, method='html')

            # set up yadcf
            getcol = lambda name: [col['name'] for col in dt_options['columns']].index(name)
            filterdelay = 500
            yadcf_options = [
                {
                    'column_number':getcol('runnerid'),
                    'filter_container_id':"_rrwebapp_filtername",
                    'filter_type':"select",
                    'select_type': 'select2',
                    'filter_reset_button_text': 'clear',
                    'sort_as': 'none',
                    'select_type_options': {
                        'width': '200px',
                    },
                },{
                    'column_number':getcol('date'),
                    'filter_container_id':"_rrwebapp_filterdate",
                    'filter_type':'range_date',
                    'date_format':'yyyy-mm-dd',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_number':getcol('miles'),
                    'filter_container_id':"_rrwebapp_filterdistance",
                    'filter_type': 'range_number',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_number':getcol('agpercent'),
                    'filter_container_id':"_rrwebapp_filteragpercent",
                    'filter_type': 'range_number',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_number':getcol('series'),
                    'filter_container_id':"_rrwebapp_filterseries",
                    'filter_reset_button_text': 'all',
                    'filter_type': "select",
                    'select_type': 'select2',
                    'select_type_options': {
                        'width': '150px',
                    },
                }
            ]

            # add admin columns
            if adminuser:
                yadcf_options += [
                    {
                        'column_number':getcol('source'),
                        'filter_container_id':"_rrwebapp_filtersource",
                        'filter_type':"select",
                        'select_type': 'select2',
                        'filter_reset_button_text': 'all',
                    },{
                        'column_number':getcol('sourceid'),
                        'filter_container_id':"_rrwebapp_filtersourceid",
                        'filter_type':'select',
                        'select_type': 'select2',
                        'filter_reset_button_text': 'all',
                    },
                ]
            options = {'dtopts': dt_options, 'yadcfopts': yadcf_options}

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html',
                                         pagename=pagename,
                                         pretablehtml=pretablehtml,
                                         chartloc='beforetable',
                                         pagejsfiles=addscripts(['dt_chart.js', 'd3.legend.js', 'results_scatterplot.js']),
                                         pagecssfiles=addscripts(['d3.legend.css', 'dt_chart.css']),
                                         # serverSide must be True to pass url
                                         # add the request args to the ajax function
                                         tabledata=url_for('_resultschart')+'?'+urlencode(request.args),
                                         tablebuttons= ['csv'],
                                         tablefiles=None,
                                         options = options,
                                         inhibityear=True,inhibitclub=True,
                                         )

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/resultschart',view_func=RunnerResultsChart.as_view('resultschart'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class AjaxRunnerResultsChart(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('runnerid',None)
            seriesarg = request.args.get('series',None)
            datefromarg = request.args.get('begindate','')
            datetoarg = request.args.get('enddate','')

            # filter on valid runnerid, if present
            namesfilter = {'member':True, 'active':True}   # only support active members because this means dateofbirth is known
            resultfilter = {}
            seriesfilter = {}
            name = None
            pagename = 'Results'

            # filter on club, if present
            club_id =None
            club = None         # should fix #344
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    namesfilter['club_id'] = club.id
                    resultfilter['club_id'] = club.id
                    club_id = club.id

            elif 'club_id' in flask.session:
                club_id = flask.session['club_id']
                club = Club.query.filter_by(id=club_id).first()

            if club_id is not None:
                readcheck = ViewClubDataPermission(club_id)
                adminuser = readcheck.can()

            else:
                adminuser = False


            # if not admin, limit source to rrwebapp product name
            if not adminuser:
                resultfilter['source'] = productname

            getcol = lambda name: [col.mData for col in columns].index(name)

            # create columns dynamically because full results have seriesid = None, and this returns empty list
            ## trick here is to to the following when series is not filtered
            ##    retrieve seriesid and do not join('series') [filter disabled]
            ## otherwise
            ##    retrieve series.name and join('series') [filter enabled]
            columns = [
                ColumnDT(Race.date, mData='date', search_method='yadcf_range_date'),
                ColumnDT(RaceResult.runnerid, mData='runnerid', search_method='numeric'),
                ColumnDT(Runner.name, mData='name'),
                ColumnDT(renderseries(RaceResult.seriesid), mData='series', search_method='none'),
            ]

            # set up columns differently if series is being searched for, as if so it's ok to join('series') in query
            seriesfield = 'columns[{}][search][value]'.format(getcol('series'))
            seriessearch = request.args.get(seriesfield, None)
            if seriesarg or seriessearch:
                # give preference to seriesarg
                seriesname = seriesarg or seriessearch

                if club_shname:
                    seriesfilter['club_id'] = club.id

                # pop the last element (mData='series') off the end, as we're replacing it
                columns.pop()
                columns += [
                    ColumnDT(Series.name,        mData='series'),
                ]

            columns += [
                ColumnDT(Race.name, mData='race', search_method='none'),
                ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='yadcf_range_number'),
                # ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='none'),
                ColumnDT(RaceResult.agage, mData='age', search_method='none'),
                ColumnDT(rendertime(RaceResult.time), mData='time', search_method='none'),
                ColumnDT(rendertime(RaceResult.time / Race.distance), mData='pace', search_method='none'),
                ColumnDT(rendertime(RaceResult.agtime), mData='agtime', search_method='none'),
                ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 2), '%'), mData='agpercent', search_method='yadcf_range_number'),
                # ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 2), '%'), mData='agpercent', search_method='none'),
            ]

            # give extra columns to the admin
            if adminuser:
                columns += [
                        # ColumnDT('race.location.name',   mData='location',        search_method='none',   filter=lambda c: c if c else ' '),
                        ColumnDT(renderlocation(Race.locationid),   mData='location', search_method='none'),
                        ColumnDT(RaceResult.source,          mData='source'),
                        ColumnDT(RaceResult.sourceid,        mData='sourceid'),
                    ]

            # make copy of args as request.args is immutable and we might want to update
            args = request.args.to_dict()

            # if no search for runnerid, we return no records, expecting user to make a selection later
            # kludge this by setting resultsfilter to -1
            runneridfield = 'columns[{}][search][value]'.format(getcol('runnerid'))
            runneridsearch = args[runneridfield]
            if not runneridsearch:
                resultfilter['runnerid'] = -1

            # delimiter for string operations 
            delim = '-yadcf_delim-'

            # preprocess date range to assure proper format
            datefield = 'columns[{}][search][value]'.format(getcol('date'))
            # if min or max is missing, prepare to fill in
            nulldate = [tYmd.epoch2asc(0),tYmd.epoch2asc(time())]
            datesearch = args[datefield]
            if datesearch:
                daterange = datesearch.split(delim)
                # sure hope len(daterange) == 2
                for i in range(2):
                    if daterange[i] == '':
                        daterange[i] = nulldate[i]
                    try:
                        daterange[i] = tYmd.epoch2asc(tYmd.asc2epoch(daterange[i]))
                    # if incorrect format, act as if null
                    except ValueError:
                        daterange[i] = nulldate[i]
                args[datefield] = delim.join(daterange)

            def set_yadcf_data():
                # preprocess range for some fields to allow min only or max only
                statranges = {'miles': [0,100], 'agpercent': [0,100]}

                # prepare for page filters
                # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
                # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
                # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
                # format depends on type of select
                namesq = Runner.query.filter_by(**namesfilter)
                resultnames = [{'value': row.id, 'label': '{} ({})'.format(row.name, timeu.age(timeu.epoch2dt(time()),
                                                                                               tYmd.asc2dt(
                                                                                                   row.dateofbirth)))}
                               for row in namesq.all()]

                # only return distinct names, sorted
                names = []
                for name in resultnames:
                    if name not in names:
                        names.append(name)
                names.sort(key=lambda item: item['label'].lower())
                # app.logger.debug('after names sort')

                # avoid exception if club not specified in query
                if club:
                    series = [row.name for row in db.session.query(Series.name).filter_by(club_id=club.id).distinct().all()]
                else:
                    series = []

                # add yadcf filters
                yadcf_data = []
                yadcf_data.append(('yadcf_data_{}'.format(getcol('runnerid')), names))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('series')), series))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('miles')), statranges['miles']))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('agpercent')), statranges['agpercent']))

                # send back yadcf_data
                return yadcf_data

            # add series filters to query
            q = db.session.query().select_from(RaceResult).filter_by(**resultfilter).join(Runner).join(Race)
            if seriesfilter:
                # q = q.join(Series).filter_by(**seriesfilter)
                q = q.join(RaceResult.series).filter_by(**seriesfilter)
            # q = q.join(Race).join(Location)
            # app.logger.debug('resultfilter = {}, seriesfilter = {}'.format(resultfilter, seriesfilter))
            # app.logger.debug('query = \n{}'.format(q))

            # note there's no paging (see RunnerResultsChart) so can do some filtering after retrieval of all results from database
            rowTable = DataTables(args, q, columns, set_yadcf_data=set_yadcf_data)
            output_result = rowTable.output_result()

            # app.logger.debug('after race results filtered query')

            # filter by service / maxdistance
            ## get maxdistance by service
            if adminuser:
                services = RaceResultService.query.filter_by(club_id=club_id).join(ApiCredentials).all()
                maxdistance = {}
                for service in services:
                    attrs = ServiceAttributes(club_id, service.apicredentials.name)
                    if attrs.maxdistance:
                        maxdistance[service.apicredentials.name] = attrs.maxdistance
                    else:
                        maxdistance[service.apicredentials.name] = None
                maxdistance[productname] = None

                ## update data
                locsvr = LocationServer()
                clublocation = locsvr.getlocation(club.location)
                if 'data' in output_result:
                    rows = copy(output_result['data'])
                    output_result['data'] = []
                    for row in rows:
                        if maxdistance[row['source']]:
                            distance = get_distance(clublocation, locsvr.getlocation(row['location']))
                            if distance == None or distance > maxdistance[row['source']]: continue
                        output_result['data'].append(row)

            # add select options to admin fields source and sourceid, from runner's data
            if adminuser:
                # only fill in these selects if runner is being shown, from runner's results
                if runneridsearch:
                    sources = [row.source for row in db.session.query(RaceResult.source).filter_by(club_id=club.id, runnerid=runneridsearch).distinct().all()]
                    sourceids = [row.sourceid for row in db.session.query(RaceResult.sourceid).filter_by(club_id=club.id, runnerid=runneridsearch).distinct().all()]
                    # app.logger.debug('after source and source id queries')
                    output_result['yadcf_data_{}'.format(getcol('source'))] = sources
                    # output_result['yadcf_data_{}'.format(getcol('sourceid'))] = sourceids
                else:
                    output_result['yadcf_data_{}'.format(getcol('source'))] = []
                    # output_result['yadcf_data_{}'.format(getcol('sourceid'))] = []



            # initialize filters from server side, 
            # but only if we don't already have the filter
            # else there will be infinite loop
            ## for runnerid
            if runnerid and not runneridsearch:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    output_result['yadcf_default_{}'.format(getcol('runnerid'))] = runnerid
                else:
                    app.logger.warning('runnerid {} not found'.format(runnerid))

            ## for date
            if (datefromarg or datetoarg) and not datesearch:
                output_result['yadcf_default_{}'.format(getcol('date'))] = {'from':datefromarg, 'to':datetoarg}

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_resultschart',view_func=AjaxRunnerResultsChart.as_view('_resultschart'),methods=['GET'])
#----------------------------------------------------------------------

#----------------------------------------------------------------------
def allowed_file(filename):
#----------------------------------------------------------------------
    return '.' in filename and filename.split('.')[-1] in ['xls','xlsx','txt','csv']


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
            
            # see http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
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
            tempdir = UPLOAD_TEMP_DIR
            resultfilename = secure_filename(resultfile.filename)
            resultpathname = os.path.join(tempdir,resultfilename)
            if os.path.exists(resultpathname): os.remove(resultpathname)
            resultfile.save(resultpathname)            

            try:
                rr = raceresults.RaceResults(resultpathname,race.distance)
                rr.close()
            
            # format not good enough
            except raceresults.headerError, e:
                db.session.rollback()
                cause = '{}'.format(e)
                app.logger.warning(cause)
                return failure_response(cause=cause)
                
            # how did this happen?  check allowed_file() for bugs
            except raceresults.dataError, e:
                db.session.rollback()
                cause =  'Program Error: {}'.format(e)
                app.logger.error(cause)
                return failure_response(cause=cause)

            # start task to import results
            task = importresultstask.apply_async((club_id, raceid, resultpathname))
            
            # commit database updates and close transaction
            db.session.commit()
            return jsonify({'success': True, 'current': 0, 'total':100, 'location': url_for('importresultsstatus', task_id=task.id)}), 202, {}
            #return success_response(redirect=url_for('editparticipants',raceid=raceid))
        
        except Exception, e:
            # close rr if created, otherwise NOP
            try:
                rr.close()
            except UnboundLocalError:
                pass
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_importresults/<int:raceid>',view_func=AjaxImportResults.as_view('_importresults'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class ImportResultsStatus(MethodView):
#######################################################################
    def get(self, task_id):
        task = importresultstask.AsyncResult(task_id)

        if task.state == 'PENDING':
            # job did not start yet
            response = {
                'state': task.state,
                'current': 0,
                'total': 100,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }

            # task is finished, check for traceback, which indicates an error occurred
            if task.state == 'SUCCESS':
                # check for traceback, which indicates an error occurred
                response['cause'] = task.info.get('traceback','')
                if response['cause'] == '':
                    response['redirect'] = url_for('editparticipants',raceid=task.info.get('raceid'))

        # doesn't seem like this can happen, but just in case
        else:
            # something went wrong in the background job
            response = {
                'state': task.state,
                'current': 100,
                'total': 100,
                'cause': str(task.info),  # this is the exception raised
            }
        return jsonify(response)
#----------------------------------------------------------------------
app.add_url_rule('/importresultsstatus/<task_id>',view_func=ImportResultsStatus.as_view('importresultsstatus'), methods=['GET',])
#----------------------------------------------------------------------

#----------------------------------------------------------------------
@celery.task(bind=True)
def importresultstask(self, club_id, raceid, resultpathname):
#----------------------------------------------------------------------
    '''
    background task to import results

    :param club_id: club identifier
    :param raceid: race identifier
    :param resultpathname: full pathname of results file
    '''
    try:
        # create race results iterator
        race = Race.query.filter_by(club_id=club_id,id=raceid).first()
        rr = raceresults.RaceResults(resultpathname,race.distance)

        # count rows, inefficiently. TODO: add count() method to raceresults.RaceResults class
        try:
            total = 0
            while True:
                rr.next()
                total += 1
        except StopIteration:
            pass

        # only update state max 100 times over course of file, but don't make it too small
        statemod = total / 100
        if statemod == 0:
            statemod = 1

        # start over
        rr.close()
        rr = raceresults.RaceResults(resultpathname,race.distance)

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
            if numentries % statemod == 0:
                self.update_state(state='PROGRESS', meta={'current': numentries, 'total': total})

        # not sure this is necessary, but final state update
        self.update_state(state='PROGRESS', meta={'current': numentries, 'total': total})

        # remove file and temporary directory
        rr.close()
        os.remove(resultpathname)

        # we're done
        db.session.commit()
        return {'current': total, 'total': total, 'raceid': raceid}

    except:
        # close database session and roll back
        # see http://stackoverflow.com/questions/7672327/how-to-make-a-celery-task-fail-from-within-the-task
        db.session.rollback()

        # tell the admins that this happened
        celery.mail_admins('[scoretility] importtaskresults: exception occurred', traceback.format_exc())

        # report this as success, but since traceback is present, server will tell user
        return {'current': 100, 'total': 100, 'traceback': traceback.format_exc()}

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
                            newexclusion = Exclusion(
                                club_id=club_id,
                                foundname=result.name,
                                runnerid=thisexcludeid
                            )
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
    
            # # get all the results, and the race record
            # results = []
            # results = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).order_by('overallplace').all()

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
            theseseries = race.series
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
                    # save overallplace for possible sort later (series.orderby)
                    resulttime = thisresult.time
                    raceresult = RaceResult(club_id, runnerid, race.id, series.id, resulttime, gender, agegradeage, overallplace=thisresult.place)

                    # set source fields
                    raceresult.source = productname
                    raceresult.sourceid = runnerid
            
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
                
                # process bygender and division results, sorted by time or overallplace
                # TODO: is series.overall vs. series.orderby=='time' redundant?  same question for series.agegrade vs. series.orderby=='agtime'
                if series.orderby in ['time', 'overallplace']:
                    # get all the results which have been stored in the database for this race/series
                    dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id).order_by(series.orderby).all()
                    # this is easier, code-wise, than using sqlalchemy desc() function
                    if series.hightolow:
                        dbresults.reverse()
                    numresults = len(dbresults)

                    ### code below deleted because overallplace is definitely set in loop through ManagedResults above, 
                    ### and no ties are rendered in standings for overallplace anyway
                    # for rrndx in range(numresults):
                    #     raceresult = dbresults[rrndx]
                        
                    #     # set place if it has not been set before
                    #     # place may have been determined at previous iteration, if a tie was detected
                    #     if not raceresult.overallplace:
                    #         thisplace = rrndx+1
                    #         tieindeces = [rrndx]
                            
                    #         # detect tie in subsequent results based on rendering,
                    #         # which rounds to a specific precision based on distance
                    #         # but do this only if averaging ties
                    #         if series.averagetie:
                    #             # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
                    #             time = render.rendertime(raceresult.time,timeprecision)
                    #             for tiendx in range(rrndx+1,numresults):
                    #                 if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                    #                     break
                    #                 tieindeces.append(tiendx)
                    #             lasttie = tieindeces[-1] + 1
                    #         for tiendx in tieindeces:
                    #             numsametime = len(tieindeces)
                    #             if numsametime > 1 and series.averagetie:
                    #                 dbresults[tiendx].overallplace = (thisplace+lasttie) / 2.0
                    #             else:
                    #                 dbresults[tiendx].overallplace = thisplace
            
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
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
                                # but do this only if averaging ties
                                if series.averagetie:
                                    # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
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
                                              .order_by(series.orderby).all()
                                # this is easier, code-wise, than using sqlalchemy desc() function
                                if series.hightolow:
                                    dbresults.reverse()
                    
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
                                        # but do this only if averaging ties
                                        if series.averagetie:
                                            # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
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
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
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
                                # but do this only if averaging ties
                                if series.averagetie:
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
                                    else:
                                        dbresults[tiendx].agtimeplace = thisplace

                # process age grade results, ordered by agpercent
                elif series.orderby == 'agpercent':
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
                        numresults = len(dbresults)
                        #app.logger.debug('orderby=agpercent, club_id={}, race.id={}, series.id={}, gender={}, numresults={}'.format(club_id,race.id,series.id,gender,numresults))
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                            thisplace = rrndx+1                                
                            dbresults[rrndx].agtimeplace = thisplace

            # commit database updates and close transaction
            db.session.commit()
            return success_response(redirect=url_for('seriesresults',raceid=raceid))
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_tabulateresults/<int:raceid>',view_func=AjaxTabulateResults.as_view('_tabulateresults'),methods=['POST'])
#----------------------------------------------------------------------

