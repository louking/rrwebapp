###########################################################################################
# resultsutils - result handling utilities
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/24/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
#
###########################################################################################

# standard
import csv
from datetime import datetime
import time
import traceback
from json import loads, dumps
from datetime import timedelta
from collections import OrderedDict

# pypi
from flask import current_app
from googlemaps import Client
from googlemaps.geocoding import geocode
from haversine import haversine, Unit
import loutilities.renderrun as render
from loutilities.csvu import str2num
from loutilities.timeu import age, asctime, epoch2dt, dt2epoch
from loutilities.agegrade import AgeGrade
from loutilities.transform import Transform
from loutilities.namesplitter import split_full_name
from dominate.tags import span

# homegrown
from . import app
from .model import db, MAX_LOCATION_LEN, dbdate
from .model import insert_or_update, RaceResult, Runner, Race, ApiCredentials, RaceResultService, Location, Exclusion
from .model import ManagedResult, ClubAffiliation, CLUBAFFILIATION_ALTERNATES_SEPARATOR
from .apicommon import MapDict
from .clubmember import DbClubMember
from .datatables_utils import DataTablesEditor

ftime = asctime('%Y-%m-%d')
tYmd = asctime('%Y-%m-%d')
tmdy = asctime('%m/%d/%y')

RACEEPSILON = .01  # in miles, to allow for floating point precision error in database
ag = AgeGrade(agegradewb='config/wavacalc15.xls')
CACHE_REFRESH = timedelta(30)   # 30 days, per https://cloud.google.com/maps-platform/terms/maps-service-terms/?&sign=0 (sec 3.4)

# control behavior of import
DIFF_CUTOFF = 0.7   # ratio of matching characters for cutoff handled by 'clubmember'
NONMEMBERCUTOFF = 0.9   # insist on high cutoff for nonmember matching
AGE_DELTAMAX = 3    # +/- num years to be included in DISP_CLOSEAGE
JOIN_GRACEPERIOD = timedelta(7) # allow runner to join 1 week beyond race date

# initialdisposition values
# * match - exact name match found in runner table, with age consistent with dateofbirth
# * close - close name match found, with age consistent with dateofbirth
# * closeage - close name match found, but age is inconsistent with dateofbirth
# * missed - nonmembers allowed, and no member found
# * excluded - this name is in the exclusion table, either prior to import **or as a result of admin decision**
DISP_MATCH = 'definite'         # exact match of member (or non-member for non 'membersonly' race)
DISP_CLOSE = 'similar'          # similar match to member, matching age
DISP_CLOSEAGE = 'closeage'      # similar to some member(s), age mismatch (within window)
DISP_MISSED = 'missed'          # nonmembers allowed, and no member found
DISP_EXCLUDED = 'excluded'      # DISP_CLOSE match, but found in exclusions table
DISP_NOTUSED = ''               # not used for results


class ParameterError(Exception): pass

def race_fixeddist(distance):
    '''
    return fixeddist value for distance

    :param distance: distance of the race (miles)
    :rtype: string containing value for race.fixeddist field
    '''
    return '{:.4g}'.format(float(distance))

def get_distance(loc1, loc2, miles=True):
    '''
    retrieves distance between two Location objects
    if either location is unknown (lookuperror occurred), None is returned
    NOTE: must check for error like "if get_distance() != None" because 0 is a valid return value

    :param loc1: Location object
    :param loc2: Location object
    :rtype: distance between loc1 and loc2, or None if error
    '''
    # check for bad data
    if loc1.lookuperror or loc2.lookuperror:
        return None

    # indicate to haversine what unit to use
    if miles:
        unit = Unit.MILES
    else:
        unit = Unit.KILOMETERS
        
    # return great circle distance between points
    loc1latlon = (loc1.latitude, loc1.longitude)
    loc2latlon = (loc2.latitude, loc2.longitude)
    return haversine(loc1latlon, loc2latlon, unit=unit)

def getrunnerchoices(club_id, race, pool, result):
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
    if thisdisposition in [DISP_MATCH, DISP_CLOSE]:
        # found a possible runner
        if candidate:
            runnername,ascdob = candidate
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            try:
                dobdt = dbdate.asc2dt(ascdob)
                nameage = '{} ({})'.format(runner.name, age(racedatedt,dobdt))
            # possibly no date of birth
            except ValueError:
                nameage = runner.name
            thisrunnerchoice.append([runner.id,nameage])
        
        # see issue #183
        else:
            pass    # TODO: this is a bug -- that to do?

    # didn't find runner, what were other possibilities?
    elif thisdisposition in [DISP_MISSED, DISP_CLOSEAGE]:
        # this is possible because maybe (new) member was chosen in prior use of editparticipants
        if candidate:
            runnername,ascdob = candidate
            runner = Runner.query.filter_by(club_id=club_id,name=runnername,dateofbirth=ascdob).first()
            try:
                dobdt = dbdate.asc2dt(ascdob)
                nameage = '{} ({})'.format(runner.name, age(racedatedt,dobdt))
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
            nameage = '{} ({})'.format(missedrunner.name, age(racedatedt,dobdt))
            thisrunnerchoice.append((missedrunner.id,nameage))
        
    # for no match and excluded entries, change choice
    elif thisdisposition in [DISP_NOTUSED,DISP_EXCLUDED]:
        if membersonly:
            thisrunnerchoice = [(None,'n/a')]
        else:
            # leave default
            pass
    
    # for non membersonly race, maybe need to add new name to member database, give that option
    if not membersonly and thisdisposition not in [DISP_MATCH]:
        # it's possible that thisname == runnername if (new) member was added in prior use of editparticipants
        if thisname != runnername:
            thisrunnerchoice.append(('new','{} (new)'.format(thisname)))

    return thisrunnerchoice

def filtermissed(club_id,missed,racedate,resultage):
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
        # don't consider 'closeage matches' where age difference from result is too large
        dobdt = dbdate.asc2dt(thismissed['dob'])
        if abs(age(racedatedt,dobdt) - resultage) > AGE_DELTAMAX:
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

def get_earliestrace(runner, year=None):
    """
    get earliest race within a year for this runner, within ManagedResult table

    :param year: year in question
    :param runner: Runner record
    :rettype: ManagedResult record, or None
    """
    results = ManagedResult.query.filter_by(runnerid=runner.id).join(Race).order_by(Race.date.desc()).all()
    divdate = None
    theresult = None
    for result in results:
        resultdate = dbdate.asc2dt(result.race.date)
        if year and year < resultdate.year: continue
        if year and year > resultdate.year: break
        if not divdate or resultdate < divdate:
            divdate = resultdate
            theresult = result
    return theresult


class Record():
    pass

class ImportResults():
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
    defaultmapping = dict(list(zip(dbattrs+dbmetaattrs,dbattrs+dbmetaattrs)))

    def __init__(self, club_id, raceid, mapping=defaultmapping):

        # remember what we need later
        self.club_id = club_id

        # mapping method for each database field from input row
        self.map = MapDict(mapping)

        # get race and list of runners who should be included in this race, based on race's membersonly configuration
        self.race = Race.query.filter_by(club_id=club_id,id=raceid).first()
        self.racedatedt = dbdate.asc2dt(self.race.date)
        self.timeprecision,agtimeprecision = render.getprecision(self.race.distance,surface=self.race.surface)

        if len(self.race.series) == 0:
            raise ParameterError('Race needs to be included in at least one series to import results')

        # determine candidate pool based on membersonly
        membersonly = self.race.series[0].membersonly
        if membersonly:
            self.pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
        else:
            self.pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

        ### all the "work" is here to set up the dbmapping from input result
        # use OrderedDict because some dbattrs depend on others to have been done first (e.g., confirmed must be after initialdisposition)
        # first overwrite a few of these to make sure name, lname, fname, hometown, city, state filled in
        dbmapping = OrderedDict(list(zip(self.dbattrs,self.dbattrs)))
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

    def set_initialdisposition(self, inrow):
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
                # if we matched the date of birth exactly
                if ascdob:
                    dbresult.initialdisposition = DISP_MATCH
                    dbresult.confirmed = True
                    # current_app.logger.debug('    DISP_MATCH')
                    
                # maybe was nonmember, included from some non memberonly race
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
                            # current_app.logger.debug('    DISP_MATCH')

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
                    # current_app.logger.debug('    DISP_CLOSE')
                    
                # results name vs this runner id has been excluded
                else:
                    candidate = None
                           
        # didn't find runner on initial search, or candidate was discarded
        if not candidate:
            # clear runnerid in case we discarded candidate above
            dbresult.runnerid = None

            # favor active members, then inactive members
            # note: filtermissed() depends on DOB
            missed = self.pool.getmissedmatches()
            # current_app.logger.debug('  self.pool.getmissedmatches() = {}'.format(missed))
            
            # don't consider 'missed matches' where age difference from result is too large, or excluded
            # current_app.logger.debug('  missed before filter = {}'.format(missed))
            missed = filtermissed(club_id,missed,race.date,dbresult.age)
            # current_app.logger.debug('  missed after filter = {}'.format(missed))

            # if there remain are any missed results, indicate close age
            if len(missed) > 0:
                dbresult.initialdisposition = DISP_CLOSEAGE
                dbresult.confirmed = False

            # if not members only the admin can add them to the runner table
            elif not membersonly:
                dbresult.initialdisposition = DISP_MISSED
                dbresult.confirmed = False
                # current_app.logger.debug('    DISP_MISSED')
                
            # otherwise, this result isn't used
            else:
                dbresult.initialdisposition = DISP_NOTUSED
                dbresult.confirmed = True
                # current_app.logger.debug('    DISP_NOTUSED')

        # this needs to be the same as what was already stored in the record
        return dbresult.initialdisposition
    
    def update_dbresult(self, inresult, dbresult):
        '''
        updates dbresult based on inresult

        :param inresult: dict-like object which has keys per mapping defined at instantiation
        :param dbresult: ManagedResult instance to be initialized or updated

        :rtype: missed - list of missed matches if not exact match
        '''

        # convert inresult keys
        thisinresult = self.map.convert(inresult)
        current_app.logger.debug('thisinresult={}'.format(thisinresult))

        # this makes the dbresult accessible to the dbmapping functions
        self.dbresult = dbresult

        # update dbresult - this executes dbmapping function for each dbresult attribute
        self.dte.set_dbrow(thisinresult, dbresult)

        # return missed matches for select rendering
        runner_choices = getrunnerchoices(self.club_id, self.race, self.pool, dbresult)

        return runner_choices

class StoreServiceResults():
    '''
    store results retrieved from a service, using service's file access class

    note serviceentryid should be set only if this id increases with newer results

    xservice2norm: mapping from service access attribute to a normalized data structure
        must include all RaceResult attributes except 
            club_id, runnerid, raceid, seriesid
            place and points attributes may also be omitted
        must include additional keys used for Runner, Race lookup: 
            runnername, dob, gender, racename, raceloc, date, distmiles, serviceentryid

    :param servicename: name of service
    :param serviceaccessor: instance of ServiceResultFile
    :param xservice2norm: {'normattr_n':'serviceattr_n', 'normattr_m':f(servicerow), ...}
    '''

    def __init__(self, servicename, serviceaccessor, xservice2norm):
        self.servicename = servicename
        self.serviceaccessor = serviceaccessor
        self.service2norm = Transform(xservice2norm, sourceattr=True, targetattr=True)

    def get_count(self, filename):
        '''
        return the length of the service accessor file

        :param filename: name of the file
        :rtype: number of lines in the file
        '''
        self.serviceaccessor.open(filename)
        numlines = self.serviceaccessor.count()
        self.serviceaccessor.close()

        return numlines

    def storeresults(self, thistask, status, club_id, filename):
        '''
        create service accessor and open file
        get location if known
        loop through all results in accessor file, and store in database
        close file

        caller needs to `db.session.commit()` the changes

        :param thistask: this is required for task thistask.update_state()
        :param status: status for updating front end
        :param club_id: identifies club for which results are to be stored
        :param filename: name of csv file which contains service result records
        '''

        # create service accessor and open file
        self.serviceaccessor.open(filename)

        status[self.servicename]['total'] = self.serviceaccessor.count()
        status[self.servicename]['processed'] = 0

        # loop through all results and store in database
        while True:
            filerecord = next(self.serviceaccessor)
            if not filerecord: break

            # transform to result attributes
            result = Record()
            result.source = self.servicename
            # app.logger.debug('filerecord = {}'.format(filerecord.__dict__))
            self.service2norm.transform(filerecord, result)
            # app.logger.debug('result = {}'.format(result.__dict__))

            # maybe we have a record in the database which matches this one, if so update the record
            # otherwise create a new database record
            ## first get runner
            runner = Runner.query.filter_by(club_id=club_id, name=result.runnername, dateofbirth=result.dob, gender=result.gender).first()
            if not runner:
                raise ParameterError("could not find runner in database: {} line {} {} {} {}".format(filename, status[self.servicename]['processed']+2, result.runnername, result.dob, result.gender))

            ## next get race
            ### Race has uniqueconstraint for club_id/name/year/fixeddist. It's been seen that there are additional races in athlinks, 
            ### but just assume the first is the correct one.
            raceyear = ftime.asc2dt(result.date).year
            race = Race.query.filter_by(club_id=club_id, name=result.racename, year=raceyear, fixeddist=race_fixeddist(result.distmiles)).first()
            # races = Race.query.filter_by(club_id=club_id, name=result.racename, date=result.date, fixeddist=race_fixeddist(result.distmiles)).all()
            # race = None
            # for thisrace in races:
            #     if abs(thisrace.distance - result.distmiles) < RACEEPSILON:
            #         race = thisrace
            #         break
            if not race:
                raise ParameterError("could not find race in database: {} line {} {} {} {}".format(filename, status[self.servicename]['processed']+2, result.racename, result.date, result.distmiles))

            ## update or create result in database
            try:
                agage = age(ftime.asc2dt(race.date), ftime.asc2dt(runner.dateofbirth))
                result.agpercent, result.agtime, result.agfactor = ag.agegrade(agage, runner.gender, result.distmiles, result.timesecs)

                dbresult = RaceResult(club_id, runner.id, race.id, None, result.timesecs, runner.gender, agage, instandings=False)
                for attr in ['agfactor', 'agtime', 'agpercent', 'source', 'sourceid', 'sourceresultid', 'fuzzyage']:
                    setattr(dbresult,attr,getattr(result,attr))

                insert_or_update(db.session, RaceResult, dbresult, skipcolumns=['id'], 
                                 club_id=club_id, source=self.servicename, runnerid=runner.id, raceid=race.id)

            # maybe user is trying to cancel
            except SystemExit:
                raise

            # otherwise just log and ignore result
            except: 
                current_app.logger.warning('exception for "{}", result ignored, processing {} result {}\n{}'.format(runner.name, self.servicename, result.__dict__, traceback.format_exc()))

            # update the number of results processed and pass back the status
            status[self.servicename]['lastname'] = result.runnername
            status[self.servicename]['processed'] += 1
            thistask.update_state(state='PROGRESS', meta={'progress':status})

        # finished reading results, close input file
        self.serviceaccessor.close()


class CollectServiceResults(object):

    def __init__(self, servicename, resultfilehdr, resultattrs):
        '''
        initialize object instance

        may be overridden when CollectServiceResults is instantiated, but overriding method must call
        `super(<subclass>, self).__init__(servicename, resultfilehdr, resultattrs)`

        :param servicename: name of service
        :param resultfilehdr: list of keys for file header of result file
        :param resultattrs: list of attributes for ServiceResult record
        '''
        
        self.servicename = servicename
        self.resultfilehdr = resultfilehdr
        self.resultattrs = resultattrs

    def openservice(self, club_id):
        '''
        initialize service
        recommended that the overriding method save service instance in `self.service`

        must be overridden when ResultsCollect is instantiated

        :param club_id: club.id for club this service is operating on
        '''
        pass

    def getresults(self, name, fname, lname, gender, dt_dob, begindate, enddate):
        '''
        retrieves a list of results for a single name

        must be overridden when ResultsCollect is instantiated

        use gender, dt_dob to filter errant race results, based on age of runner on race day

        :param name: name of participant for which results are to be returned
        :param fname: first name of participant
        :param lname: last name of participant
        :param gender: 'M', 'F', or 'X'
        :param dt_dob: participant's date of birth, as datetime 
        :param begindate: epoch time for start of results, 00:00:00 on date to begin
        :param end: epoch time for end of results, 23:59:59 on date to finish
        :rtype: list of serviceresults, each of which can be processed by convertresult
        '''
        pass

    def convertserviceresult(self, result):
        '''
        converts a single service result to dict suitable to be saved in resultfile

        result must be converted to dict with keys in `resultfilehdr` provided at instance creation

        must be overridden when ResultsCollect is instantiated

        use return value of None for cases when results could not be filtered by `:meth:getresults`

        :param result: single service result, from list retrieved through `getresults`
        :rtype: dict with keys matching `resultfilehdr`, or None if result is not to be saved
        '''
        pass

    def closeservice(self):
        '''
        closes service, if necessary

        may be overridden when ResultsCollect is instantiated
        '''
        pass


    def collect(self, thistask, club_id, searchfile, resultfile, status, begindate=ftime.asc2epoch('1970-01-01'), enddate=ftime.asc2epoch('2999-12-31')):
        '''
        collect race results from a service
        
        :param thistask: this is required for task thistask.update_state()
        :param club_id: club id for club being operated on
        :param searchfile: path to file containing names, genders, birth dates to search for
        :param resultfile: output file path (csv) for detailed results from this service
        :param status: dict containing current status
        :param begindate: epoch time - choose races between begindate and enddate
        :param enddate: epoch time - choose races between begindate and enddate
        :param key: key for access to athlinks
        '''
        
        # save some parameters as class attributes
        self.thistask = thistask
        self.status = status

        # open files
        if isinstance(searchfile, list):
            _IN = searchfile
        else:
            _IN = open(searchfile, 'r', newline='')
        IN = csv.DictReader(_IN)

        _OUT = open(resultfile, 'w', newline='')
        OUT = csv.DictWriter(_OUT, self.resultfilehdr)
        OUT.writeheader()

        try:

            # create service
            self.openservice(club_id)

            # reset begindate to beginning of day, enddate to end of day
            dt_begindate = epoch2dt(begindate)
            adj_begindate = datetime(dt_begindate.year,dt_begindate.month,dt_begindate.day,0,0,0)
            begindate = dt2epoch(adj_begindate)
            dt_enddate = epoch2dt(enddate)
            adj_enddate = datetime(dt_enddate.year,dt_enddate.month,dt_enddate.day,23,59,59)
            enddate = dt2epoch(adj_enddate)

            # only update state max 100 times over course of file, but don't make it too small
            statemod = status[self.servicename]['total'] // 100;
            if statemod == 0:
                statemod = 1;

            # get start time for debug messaging
            start = time.time()
            
            # loop through runners in the input file
            for runner in IN:
                name = ' '.join([runner['GivenName'],runner['FamilyName']])

                dt_dob = ftime.asc2dt(runner['DOB'])
                
                # get results for this athlete
                results = self.getresults(name, runner['GivenName'], runner['FamilyName'], runner['Gender'][0], dt_dob, begindate, enddate)
                
                # loop through each result
                for result in results:
                    # protect against bad data, just ignore the result and log the error
                    try:
                        outrec = self.convertserviceresult(result)

                    # maybe user is trying to cancel
                    except SystemExit:
                        raise

                    # otherwise just log and ignore result
                    except:
                        current_app.logger.warning('exception for "{}", result ignored, processing {} result {}\n{}'.format(name, self.servicename, result, traceback.format_exc()))
                        outrec = None

                    # only save if service wanted to save
                    if outrec:
                        OUT.writerow(outrec)
        
                # update status, careful not to do it too often
                status[self.servicename]['lastname'] = name
                status[self.servicename]['processed'] += 1
                if status[self.servicename]['processed'] % statemod == 0:
                    thistask.update_state(state='PROGRESS', meta={'progress':status})

        finally:
            self.closeservice()
            _OUT.close()
            if not isinstance(searchfile, list):
                _IN.close()

        # final state update
        thistask.update_state(state='PROGRESS', meta={'progress': status})

        finish = time.time()
        current_app.logger.debug('elapsed time (min) = {}'.format((finish-start)/60))
    

class ServiceResult():
    '''
    represents single result from service
    '''

    pass
    

class ServiceResultFile(object):
    '''
    represents file of athlinks results collected from athlinks
    
    TODO:: add write methods, and update :func:`collect` to use :class:`ServiceResult` class
    '''
   
    def __init__(self, servicename, mapping):
        self.servicename = servicename
        self.mapping = mapping
        self.transform = Transform(mapping, sourceattr=False, targetattr=True).transform
        
    def open(self, filename, mode='r'):
        '''
        open athlinks result file
        
        :param mode: 'r' or 'w' -- TODO: support 'w'
        '''
        if mode[0] not in ['r']:
            raise ParameterError('mode {} not currently supported'.format(mode))
    
        self._fh = open(filename, mode, newline='')

        # count the number of lines then reset the file pointer -- don't count header
        self._numlines = sum(1 for line in self._fh) - 1
        self._fh.seek(0)

        # create the DictReader object
        self._csv = csv.DictReader(self._fh)
        
    def close(self):
        '''
        close athlinks result file
        '''
        if hasattr(self,'_fh'):
            self._fh.close()
            delattr(self,'_fh')
            delattr(self,'_csv')
            delattr(self,'_numlines')
        
    def count(self):
        return self._numlines
    
    def __next__(self):
        '''
        get next :class:`AthlinksResult`
        
        :rtype: :class:`AthlinksResult`, or None when end of file reached
        '''
        try:
            fresult = next(self._csv)
            
        except StopIteration:
            return None
        
        serviceresult = ServiceResult()
        self.transform(fresult, serviceresult)
                
        return serviceresult
    

class ServiceAttributes(object):
    '''
    access for service attributes in RaceResultService

    :param servicename: name of service
    '''

    def _getconfigattrs(self):
        apicredentials = ApiCredentials.query.filter_by(name=self.servicename).first()
        if not apicredentials:
            return {}

        self.rrs = RaceResultService.query.filter_by(club_id=self.club_id, apicredentials_id=apicredentials.id).first()
        if not self.rrs or not self.rrs.attrs:
            return {}

        # current_app.logger.debug('self.rrs.attrs {}'.format(self.rrs.attrs))
        return loads(self.rrs.attrs)

    def __init__(self, club_id, servicename):
        self.club_id = club_id
        self.servicename = servicename
        
        # update defaults here
        self.attrs = dict(
                         maxdistance = None,
                        )

        # get configured attributes
        configattrs = self._getconfigattrs()

        # bring in configuration, if any
        self.attrs.update(configattrs)
        # current_app.logger.debug('service {} configattrs {} self.attrs {}'.format(servicename, configattrs, self.attrs))

        # attrs become attributes of this object
        for attr in self.attrs:
            setattr(self, attr, self.attrs[attr])

    #----------------------------------------------------------------------
    def set_attr(self, name, value):
    #----------------------------------------------------------------------
        configattrs = self._getconfigattrs()
        configattrs[name] = value
        
        # update database
        self.rrs.attrs = dumps(configattrs)
        insert_or_update(db.session, RaceResultService, self.rrs, skipcolumns=['id'], name=self.service)


class LocationServer(object):

    def __init__(self):

        googlekey = ApiCredentials.query.filter_by(name='googlemaps').first().key
        self.client = Client(key=googlekey)

    def getlocation(self, address):
        '''
        retrieve location from database, if available, else get from googlemaps api

        :param address: address for lookup
        :rtype: Location instance
        '''

        dbaddress = address
        if len(dbaddress) > MAX_LOCATION_LEN:
            dbaddress = dbaddress[0:MAX_LOCATION_LEN]

        loc = Location.query.filter_by(name=dbaddress).first()

        now = epoch2dt(time.time())
        if not loc or (now - loc.cached_at > CACHE_REFRESH):
            # new location
            loc = Location(name=dbaddress)

            # get geocode from google
            # use the full address, not dbaddress which gets s
            gc = geocode(self.client, address=address)

            # if we got good data, fill in the particulars
            # assume first in list is good, give warning if multiple entries received back
            if gc:
                # notify if multiple values returned
                if len(gc) > 1:
                    current_app.logger.warning('geocode: multiple locations ({}) received from googlemaps for {}'.format(len(gc), address))

                # save lat/long from first value returned
                loc.latitude  = gc[0]['geometry']['location']['lat']
                loc.longitude = gc[0]['geometry']['location']['lng']

            # if no response, still store in database, but flag as error
            else:
                loc.lookuperror = True

            # remember when last retrieved
            loc.cached_at = now

            # insert or update -- flush is done within, so id should be set after this
            insert_or_update(db.session, Location, loc, skipcolumns=['id'], name=dbaddress)

        # and back to caller
        return loc


class ClubAffiliationLookup():
    """
    lookup access by club name for club affiliations
    """
    def __init__(self, club_id, year):
        # make hashed lookup for known clubs
        allclubaffs = ClubAffiliation.query.filter_by(club_id=club_id, year=year).all()
        self.clubaff = {}
        for thisclubaff in allclubaffs:
            if thisclubaff.alternates:
                knownclubs = thisclubaff.alternates.split(CLUBAFFILIATION_ALTERNATES_SEPARATOR)
                for knownclub in knownclubs:
                    self.clubaff[knownclub] = thisclubaff
    
    def clubaffiliation(self, clubname):
        """
        returns ClubAffiliation 
        """
        if clubname in self.clubaff:
            return self.clubaff[clubname]
        else:
            return None
    
    def knownclub(self, clubname):
        """
        returns True if club is a known club
        """
        return clubname in self.clubaff

def clubaffiliationelement(result):
    """
    return dom element associated with clubaffiliation for a result
    """
    if result.clubaffiliation and result.clubaffiliation.shortname:
        domel = span(result.clubaffiliation.shortname, title=result.clubaffiliation.title)
    else:
        domel = None
    return domel
