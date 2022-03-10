###########################################################################################
#   runningaheadresults - collect race results data from runningahead
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/13/13    Lou King    Create
#   11/05/16    Lou King    Copied from running/runningaheadresults.py
#
#   Copyright 2013, 2016 Lou King
###########################################################################################
'''
runningaheadresults - collect race results data from runningahead
===================================================================

'''


# standard
import csv
import datetime
import time
import traceback

# pypi
from flask import current_app

# github

# other

# home grown
from .resultsutils import CollectServiceResults, ServiceResultFile, race_fixeddist
from .model import db   # this is ok because this module only runs under flask
from .model import ApiCredentials, Club, Race, MAX_RACENAME_LEN, MAX_LOCATION_LEN

from loutilities import timeu
from loutilities import csvu
from loutilities import agegrade
from loutilities import renderrun as render
from running import runningahead
from running.runningahead import FIELD


ag = agegrade.AgeGrade(agegradewb='config/wavacalc15.xls')
class invalidParameter(Exception): pass

# resultfilehdr needs to associate 1:1 with resultattrs
resultfilehdr = 'GivenName,FamilyName,name,DOB,Gender,race,date,loc,age,miles,km,time,timesecs,ag'.split(',')
resultattrs = 'firstname,lastname,name,dob,gender,race,date,loc,age,miles,km,time,timesecs,ag'.split(',')

hdrtransform = dict(list(zip(resultattrs,resultfilehdr)))
ftime = timeu.asctime('%Y-%m-%d')
hdrtransform['gender'] = lambda row: row['Gender'][0].upper()
hdrtransform['loc'] = lambda row: None                  # loc not available from runningahead

METERSPERMILE = 1609.344


########################################################################
class RunningAHEADResultFile(ServiceResultFile): 
########################################################################
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        super(RunningAHEADResultFile, self).__init__('runningahead', hdrtransform)


########################################################################
class RunningAHEADCollect(CollectServiceResults):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        '''
        initialize object instance

        may be overridden when ResultsCollect is instantiated, but overriding method must call
        `super(<subclass>, self).__init__(servicename, resultfilehdr, resultattrs)`

        '''
        super(RunningAHEADCollect, self).__init__('runningahead', resultfilehdr, resultattrs)

    #----------------------------------------------------------------------
    def openservice(self, club_id):
    #----------------------------------------------------------------------
        '''
        initialize service
        recommended that the overriding method save service instance in `self.service`

        must be overridden when ResultsCollect is instantiated

        :param club_id: club.id for club this service is operating on
        '''
        # remember club
        self.club_id = club_id

        # open service
        # TODO: use proper oauth to get runningahead auth key
        racredentials = ApiCredentials.query.filter_by(name='runningahead').first()
        key = racredentials.key
        secret = racredentials.secret
        self.service = runningahead.RunningAhead(debug=True, key=key, secret=secret)

        # collect runningahead users who have given access
        users = self.service.listusers()
        self.rausers = []
        for user in users:
            rauser = self.service.getuser(user['token'])
            self.rausers.append((user, rauser))


    #----------------------------------------------------------------------
    def getresults(self, name, fname, lname, gender, dt_dob, begindate, enddate):
    #----------------------------------------------------------------------
        '''
        retrieves a list of results for a single name

        must be overridden when ResultsCollect is instantiated

        use dt_dob to filter errant race results, based on age of runner on race day

        :param name: name of participant for which results are to be returned
        :param fname: first name of participant
        :param lname: last name of participant
        :param gender: 'M', 'F', or 'X'
        :param dt_dob: participant's date of birth, as datetime 
        :param begindate: epoch time for start of results, 00:00:00 on date to begin
        :param end: epoch time for end of results, 23:59:59 on date to finish
        :rtype: list of serviceresults, each of which can be processed by convertresult
        '''
        
        # remember participant data
        self.name = name
        self.fname = fname
        self.lname = lname
        self.gender = gender
        self.dt_dob = dt_dob
        self.dob = ftime.dt2asc(dt_dob)

        # find this user
        foundmember = False
        for user,rauser in self.rausers:
            if 'givenName' not in rauser or 'birthDate' not in rauser: continue    # we need to know the name and birth date
            givenName = rauser['givenName'] if 'givenName' in rauser else ''
            familyName = rauser['familyName'] if 'familyName' in rauser else ''
            rausername = '{} {}'.format(givenName,familyName)
            if rausername == name and dt_dob == ftime.asc2dt(rauser['birthDate']):
                foundmember = True
                current_app.logger.debug('found {}'.format(name))
                break
        if not foundmember: return []

        # if we're here, found the right user, now let's look at the workouts
        a_begindate = ftime.epoch2asc(begindate)
        a_enddate = ftime.epoch2asc(enddate)
        workouts = self.service.listworkouts(user['token'],begindate=a_begindate,enddate=a_enddate,getfields=list(FIELD['workout'].keys()))

        # get race results for this athlete
        results = []
        if workouts:
            for wo in workouts:
                if wo['workoutName'].lower() != 'race': continue
                if 'duration' not in wo['details']: continue        # seen once, not sure why
                thisdate = wo['date']
                dt_thisdate = ftime.asc2dt(thisdate)
                thisdist = runningahead.dist2meters(wo['details']['distance'])
                thistime = wo['details']['duration']
                thisrace = wo['course']['name'] if 'course' in wo else 'unknown'
                if thistime == 0:
                    current_app.logger.warning('{} has 0 time for {} {}'.format(name,thisrace,thisdate))
                    continue
                stat = {'GivenName':fname,'FamilyName':lname,'name':name,
                        'DOB':self.dob,'Gender':gender,'race':thisrace,'date':thisdate,'age':timeu.age(dt_thisdate,dt_dob),
                        'miles':thisdist/METERSPERMILE,'km':thisdist/1000.0,'time':render.rendertime(thistime,0)}
                results.append(stat)

        # already filtered by date and by age
        # send results back to caller
        return results


    #----------------------------------------------------------------------
    def convertserviceresult(self, result):
    #----------------------------------------------------------------------
        '''
        converts a single service result to dict suitable to be saved in resultfile

        result must be converted to dict with keys in `resultfilehdr` provided at instance creation

        must be overridden when ResultsCollect is instantiated

        use return value of None for cases when results could not be filtered by `:meth:getresults`

        :param fname: participant's first name
        :param lname: participant's last name
        :param result: single service result, from list retrieved through `getresults`
        :rtype: dict with keys matching `resultfilehdr`, or None if result is not to be saved
        '''

        # create output record and copy common fields
        outrec = {}

        # copy participant information
        outrec['name'] = self.name
        outrec['GivenName'] = self.fname
        outrec['FamilyName'] = self.lname
        outrec['DOB'] = self.dob
        outrec['Gender'] = self.gender

        # get race name, strip white space
        racename = result['race'].strip()
        # maybe truncate to FIRST part of race name
        if len(racename) > MAX_RACENAME_LEN:
            racename = racename[:MAX_RACENAME_LEN]
            
        outrec['race'] = racename
        outrec['date'] = result['date']
        outrec['loc'] = ''
        if len(outrec['loc']) > MAX_LOCATION_LEN:
            outrec['loc'] = outrec['loc'][:MAX_LOCATION_LEN]
        
        # distance, category, time
        distmiles = result['miles']
        distkm = result['km']
        if distkm is None or distkm < 0.050: return None # should already be filtered within runningahead, but just in case

        outrec['miles'] = distmiles
        outrec['km'] = distkm
        resulttime = result['time']

        # what about surface? would require retrieving course and who knows if asphalt is set correctly?

        # strange case of TicksString = ':00'
        if resulttime[0] == ':':
            resulttime = '0'+resulttime
        while resulttime.count(':') < 2:
            resulttime = '0:'+resulttime
        outrec['time'] = resulttime
        outrec['timesecs'] = timeu.timesecs(resulttime)

        # retrieve or add race
        # flush should allow subsequent query per http://stackoverflow.com/questions/4201455/sqlalchemy-whats-the-difference-between-flush-and-commit
        # Race has uniqueconstraint for club_id/name/year/fixeddist. 
        racecached = True
        raceyear = ftime.asc2dt(result['date']).year
        race = Race.query.filter_by(club_id=self.club_id, name=racename, year=raceyear, fixeddist=race_fixeddist(distmiles)).first()
        ### TODO: should the above be .all() then check for first race within epsilon distance?
        if not race:
            racecached = False
            race = Race(club_id=self.club_id, year=raceyear)
            race.name = racename
            race.distance = distmiles
            race.fixeddist = race_fixeddist(race.distance)
            race.date = result['date']
            race.active = True
            race.external = True
            race.surface = 'trail'  # a guess here, but we really don't know
            db.session.add(race)
            db.session.flush()  # force id to be created

        # age is on date of race
        dt_racedate = ftime.asc2dt(race.date)
        racedateage = timeu.age(dt_racedate, self.dt_dob)
        outrec['age'] = racedateage

        # leave out age grade if exception occurs, skip results which have outliers
        try:
            resultgen = result['Gender'][0].upper()
            agpercent,agresult,agfactor = ag.agegrade(racedateage, resultgen, distmiles, timeu.timesecs(resulttime))
            outrec['ag'] = agpercent
            if agpercent < 15 or agpercent >= 100: return None # skip obvious outliers
        except:
            current_app.logger.warning(traceback.format_exc())
            pass

        # and we're done
        return outrec

    #----------------------------------------------------------------------
    def closeservice(self):
    #----------------------------------------------------------------------
        '''
        closes service, if necessary

        may be overridden when ResultsCollect is instantiated
        '''
        pass


    
