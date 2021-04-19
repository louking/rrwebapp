###########################################################################################
#   ultrasignupresults - collect race results data from ultrasignup
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/13/13    Lou King    Create
#   11/03/16    Lou King    Copied from running/ultrasignupresults.py
#
#   Copyright 2013, 2016 Lou King
###########################################################################################
'''
ultrasignupresults - collect race results data from ultrasignup
===================================================================

'''


# standard
import csv
import datetime
import time
import traceback

# pypi

# github

# other

# home grown
from . import app
from loutilities import timeu
from loutilities import csvu
from loutilities import agegrade
from .resultsutils import CollectServiceResults, ServiceResultFile
from running import ultrasignup
from .model import db   # this is ok because this module only runs under flask
from .model import ApiCredentials, Club, Race, MAX_RACENAME_LEN, MAX_LOCATION_LEN
from .race import race_fixeddist


ag = agegrade.AgeGrade(agegradewb='config/wavacalc15.xls')
class invalidParameter(Exception): pass

# resultfilehdr needs to associate 1:1 with resultattrs
resultfilehdr = 'GivenName,FamilyName,name,DOB,Gender,race,date,loc,age,miles,km,time,timesecs,ag'.split(',')
resultattrs = 'firstname,lastname,name,dob,gender,race,date,raceloc,age,miles,km,time,timesecs,ag'.split(',')

hdrtransform = dict(list(zip(resultattrs,resultfilehdr)))
ftime = timeu.asctime('%Y-%m-%d')
hdrtransform['gender'] = lambda row: row['Gender'][0]

########################################################################
class UltraSignupResultFile(ServiceResultFile): 
########################################################################
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        super(UltraSignupResultFile, self).__init__('ultrasignup', hdrtransform)


########################################################################
class UltraSignupCollect(CollectServiceResults):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        '''
        initialize object instance

        may be overridden when ResultsCollect is instantiated, but overriding method must call
        `super(<subclass>, self).__init__(servicename, resultfilehdr, resultattrs)`

        '''
        
        super(UltraSignupCollect, self).__init__('ultrasignup', resultfilehdr, resultattrs)

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
        key = ApiCredentials.query.filter_by(name=self.servicename).first().key
        self.service = ultrasignup.UltraSignup(debug=True)


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
        :param gender: 'M' or 'F'
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

        # get results for this athlete
        allresults = self.service.listresults(fname,lname)

        # filter by date and by age
        filteredresults = []
        for result in allresults:
            e_racedate = ftime.asc2epoch(result.racedate)
            
            # skip result if outside the desired time window
            if e_racedate < begindate or e_racedate > enddate: continue
            
            # skip result if runner's age doesn't match the age within the result
            dt_racedate = timeu.epoch2dt(e_racedate)
            racedateage = timeu.age(dt_racedate,dt_dob)
            if result.age != racedateage: continue
            
            # skip result if runner's gender doesn't match gender within the result
            resultgen = result.gender
            if resultgen != gender: continue

            # if we reach here, the result is ok, and is added to filteredresults
            filteredresults.append(result)

        # back to caller
        return filteredresults


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
        racename = result.racename.strip()

        # filter out names that end in "hrs" as we don't do timed races
        if racename[-3:] == 'hrs': return None   

        # maybe truncate to FIRST part of race name
        if len(racename) > MAX_RACENAME_LEN:
            racename = racename[:MAX_RACENAME_LEN]
            
        outrec['race'] = racename
        outrec['date'] = result.racedate
        outrec['loc'] = '{}, {}'.format(result.racecity, result.racestate)
        if len(outrec['loc']) > MAX_LOCATION_LEN:
            outrec['loc'] = outrec['loc'][:MAX_LOCATION_LEN]
        
        # distance, category, time
        distmiles = result.distmiles
        distkm = result.distkm
        if distkm is None or distkm < 0.050: return None # should already be filtered within ultrasignup, but just in case

        outrec['miles'] = distmiles
        outrec['km'] = distkm
        resulttime = result.racetime

        # int resulttime means DNF, most likely -- skip this result
        if isinstance(resulttime, int): return None
        
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
        raceyear = ftime.asc2dt(result.racedate).year
        race = Race.query.filter_by(club_id=self.club_id, name=racename, year=raceyear, fixeddist=race_fixeddist(distmiles)).first()
        ### TODO: should the above be .all() then check for first race within epsilon distance?
        if not race:
            racecached = False
            race = Race(self.club_id, raceyear)
            race.name = racename
            race.distance = distmiles
            race.fixeddist = race_fixeddist(race.distance)
            race.date = result.racedate
            race.active = True
            race.external = True
            race.surface = 'trail'  # a guess here, but we really don't know
            db.session.add(race)
            db.session.flush()  # force id to be created

        # leave out age grade if exception occurs, skip results which have outliers
        try:
            # skip result if runner's age doesn't match the age within the result
            # sometimes athlinks stores the age group of the runner, not exact age,
            # so also check if this runner's age is within the age group, and indicate if so
            resultgen = result.gender[0]
            dt_racedate = ftime.asc2dt(result.racedate)
            racedateage = timeu.age(dt_racedate, self.dt_dob)
            agpercent,agresult,agfactor = ag.agegrade(racedateage, resultgen, distmiles, timeu.timesecs(resulttime))
            outrec['ag'] = agpercent
            if agpercent < 15 or agpercent >= 100: return None # skip obvious outliers
        except:
            app.logger.warning(traceback.format_exc())
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


    
