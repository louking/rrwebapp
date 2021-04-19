###########################################################################################
#   athlinksresults - collect race results data from athlinks
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/13/13    Lou King    Create
#   10/22/16    Lou King    Copied from running/athlinksresults.py
#
#   Copyright 2013, 2016 Lou King
###########################################################################################
'''
athlinksresults - collect race results data from athlinks
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
from .location import LocationServer
from loutilities import timeu
from loutilities import csvu
from loutilities import agegrade
from .resultsutils import CollectServiceResults, ServiceResultFile
from running import athlinks
from .model import db   # this is ok because this module only runs under flask
from .model import ApiCredentials, Club, Course, Race, MAX_RACENAME_LEN, MAX_LOCATION_LEN, insert_or_update
from .race import race_fixeddist


# see http://api.athlinks.com/Enums/RaceCategories
CAT_RUNNING = 2
CAT_TRAILS = 15
race_category = {CAT_RUNNING:'road',CAT_TRAILS:'trail'}
ag = agegrade.AgeGrade(agegradewb='config/wavacalc15.xls')
class invalidParameter(Exception): pass

# resultfilehdr needs to associate 1:1 with resultattrs
resultfilehdr = 'GivenName,FamilyName,name,DOB,Gender,athlid,race,date,loc,age,fuzzyage,miles,km,category,time,ag,entryid'.split(',')
resultattrs = 'firstname,lastname,name,dob,gender,id,racename,racedate,raceloc,age,fuzzyage,distmiles,distkm,racecategory,resulttime,resultagegrade,entryid'.split(',')
hdrtransform = dict(list(zip(resultattrs, resultfilehdr)))
ftime = timeu.asctime('%Y-%m-%d')


########################################################################
class AthlinksResultFile(ServiceResultFile): 
########################################################################
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        super(AthlinksResultFile, self).__init__('athlinks', hdrtransform)



########################################################################
class AthlinksCollect(CollectServiceResults):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        '''
        initialize object instance

        may be overridden when ResultsCollect is instantiated, but overriding method must call
        `super(<subclass>, self).__init__(servicename, resultfilehdr, resultattrs)`

        '''
        
        super(AthlinksCollect, self).__init__('athlinks', resultfilehdr, resultattrs)


    #----------------------------------------------------------------------
    def openservice(self, club_id):
    #----------------------------------------------------------------------
        '''
        initialize service
        recommended that the overriding method save service instance in `self.service`

        must be overridden when ResultsCollect is instantiated

        :param club_id: club.id for club this service is operating on
        '''
        # create location server
        self.locsvr = LocationServer()

        # remember club id we're working on
        self.club_id = club_id

        # debug file for races saved
        # set debugrace to False if not debugging
        debugrace = True
        if debugrace:
            clubslug = Club.query.filter_by(id=club_id).first().shname
            self.racefile = '{}/{}-athlinks-race.csv'.format(app.config['MEMBERSHIP_DIR'], clubslug)
        else:
            self.racefile = None

        if self.racefile:
            self._RACE = open(self.racefile, 'w', newline='')
            self.racefields = 'id,name,date,distmiles,status,runner'.split(',')
            self.RACE = csv.DictWriter(self._RACE, self.racefields)
            self.RACE.writeheader()

        # open service
        key = ApiCredentials.query.filter_by(name=self.servicename).first().key
        self.service = athlinks.Athlinks(debug=True, key=key)


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
        allresults = self.service.listathleteresults(name)

        # filter by date and by age
        filteredresults = []
        for result in allresults:
            e_racedate = athlinks.gettime(result['Race']['RaceDate'])
            
            # skip result if outside the desired time window
            if e_racedate < begindate or e_racedate > enddate: continue

            # skip result if wrong gender
            resultgen = result['Gender'][0]
            if resultgen != gender: continue

            # skip result if runner's age doesn't match the age within the result
            # sometimes athlinks stores the age group of the runner, not exact age,
            # so also check if this runner's age is within the age group, and indicate if so
            dt_racedate = timeu.epoch2dt(e_racedate)
            racedateage = timeu.age(dt_racedate,dt_dob)
            resultage = int(result['Age'])
            result['fuzzyage'] = False
            if resultage != racedateage:
                # if results are not stored as age group, skip this result
                if (resultage/5)*5 != resultage:
                    continue
                # result's age might be age group, not exact age
                else:
                    # if runner's age consistent with race age, use result, but mark "fuzzy"
                    if (racedateage/5)*5 == resultage:
                        result['fuzzyage'] = True
                    # otherwise skip result
                    else:
                        continue

            # if we reach here, the result is ok, and is added to filteredresults
            filteredresults.append(result)

        # back to caller
        return filteredresults


    #----------------------------------------------------------------------
    def get_race(self, course):
    #----------------------------------------------------------------------
        '''
        gets the associated race from the database, creating it if necessary
        :param course: course database object
        :return: race database object
        '''

        raceyear = ftime.asc2dt(course.date).year
        race = Race.query.filter_by(club_id=self.club_id, name=course.name, year=raceyear,
                                    fixeddist=race_fixeddist(course.distmiles)).first()
        ### TODO: should the above be .all() then check for first race within epsilon distance?
        if not race:
            racecached = False
            race = Race()
            race.club_id = self.club_id
            race.year = raceyear
            race.name = course.name
            race.distance = course.distmiles
            race.fixeddist = race_fixeddist(race.distance)
            race.date = course.date
            race.active = True
            race.external = True
            race.surface = course.surface
            loc = self.locsvr.getlocation(course.location)
            race.locationid = loc.id
            db.session.add(race)
            db.session.flush()  # force id to be created

        return race

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


        # some debug items - assume everything is cached
        coursecached = True
        racecached = True

        # get course used for this result
        courseid = '{}/{}'.format(result['Race']['RaceID'], result['CourseID'])
        course = Course.query.filter_by(club_id=self.club_id, source='athlinks', sourceid=courseid).first()

        # cache course if not done already
        race = None
        if not course:
            coursecached = False

            coursedata = self.service.getcourse(result['Race']['RaceID'], result['CourseID'])

            distmiles = athlinks.dist2miles(coursedata['Courses'][0]['DistUnit'],coursedata['Courses'][0]['DistTypeID'])
            distkm = athlinks.dist2km(coursedata['Courses'][0]['DistUnit'],coursedata['Courses'][0]['DistTypeID'])
            if distkm < 0.050: return None # skip timed events, which seem to be recorded with 0 distance

            # skip result if not Running or Trail Running race
            thiscategory = coursedata['Courses'][0]['RaceCatID']
            if thiscategory not in race_category: return None
        
            course = Course()
            course.club_id = self.club_id
            course.source = 'athlinks'
            course.sourceid = courseid

            # strip racename and coursename here to make sure detail file matches what is stored in database
            racename = csvu.unicode2ascii(coursedata['RaceName']).strip()
            coursename = csvu.unicode2ascii(coursedata['Courses'][0]['CourseName']).strip()
            course.name = '{} / {}'.format(racename,coursename)

            # maybe truncate to FIRST part of race name
            if len(course.name) > MAX_RACENAME_LEN:
                course.name = course.name[:MAX_RACENAME_LEN]
            
            course.date = ftime.epoch2asc(athlinks.gettime(coursedata['RaceDate']))
            course.location = csvu.unicode2ascii(coursedata['Home'])
            # maybe truncate to LAST part of location name, to keep most relevant information (state, country)
            if len(course.location) > MAX_LOCATION_LEN:
                course.location = course.location[-MAX_LOCATION_LEN:]

            # TODO: adjust marathon and half marathon distances?
            course.distkm =distkm
            course.distmiles = distmiles

            course.surface = race_category[thiscategory]

            # retrieve or add race
            # flush should allow subsequent query per http://stackoverflow.com/questions/4201455/sqlalchemy-whats-the-difference-between-flush-and-commit
            # Race has uniqueconstraint for club_id/name/year/fixeddist. It's been seen that there are additional races in athlinks, 
            # but just assume the first is the correct one.
            race = self.get_race(course)

            course.raceid = race.id
            db.session.add(course)
            db.session.flush()      # force id to be created

        # maybe course was cached but location of race wasn't
        # update location of result race, if needed, and if supplied
        # this is here to clean up old database data
        if not race:
            # may need to create the race again if there was an error after creating course but before creating race
            race = self.get_race(course)
        if not race.locationid and course.location:
            # app.logger.debug('updating race with location {}'.format(course.location))
            loc = self.locsvr.getlocation(course.location)
            race.locationid = loc.id
            insert_or_update(db.session, Race, race, skipcolumns=['id'], 
                             club_id=self.club_id, name=course.name, year=ftime.asc2dt(course.date).year, fixeddist=race_fixeddist(course.distmiles))
        # else:
        #     app.logger.debug('race.locationid={} course.location="{}"'.format(race.locationid, course.location))

        # debug races
        if self.racefile:
            racestatusl = []
            if not coursecached: racestatusl.append('addcourse')
            if not racecached: racestatusl.append('addrace')
            if not racestatusl: racestatusl.append('cached')
            racestatus = '-'.join(racestatusl)
            racerow = {'status': racestatus, 'runner': self.name}

            for racefield in self.racefields:
                if racefield in ['status', 'runner']: continue
                racerow[racefield] = getattr(course,racefield)
            self.RACE.writerow(racerow)


        # fill in output record fields from result, course
        # combine name, get age
        outrec['age'] = result['Age']
        outrec['fuzzyage'] = result['fuzzyage']

        # leave athlid blank if result not from an athlink member
        athlmember = result['IsMember']
        if athlmember:
            outrec['athlid'] = result['RacerID']

        # remember the entryid, high water mark of which can be used to limit the work here
        outrec['entryid'] = result['EntryID']

        # race name, location; convert from unicode if necessary
        # TODO: make function to do unicode translation -- apply to runner name as well (or should csv just store unicode?)
        outrec['race'] = course.name
        outrec['date'] = course.date
        outrec['loc'] = course.location
        
        outrec['miles'] = course.distmiles
        outrec['km'] = course.distkm
        outrec['category'] = course.surface
        resulttime = result['TicksString']

        # strange case of TicksString = ':00'
        if resulttime[0] == ':':
            resulttime = '0'+resulttime
        while resulttime.count(':') < 2:
            resulttime = '0:'+resulttime
        outrec['time'] = resulttime
        
        # strange case of 0 time, causes ZeroDivisionError and is clearly not valid
        if timeu.timesecs(resulttime) == 0: return None

        # leave out age grade if exception occurs, skip results which have outliers
        try:
            # skip result if runner's age doesn't match the age within the result
            # sometimes athlinks stores the age group of the runner, not exact age,
            # so also check if this runner's age is within the age group, and indicate if so
            e_racedate = athlinks.gettime(result['Race']['RaceDate'])
            resultgen = result['Gender'][0]
            dt_racedate = timeu.epoch2dt(e_racedate)
            racedateage = timeu.age(dt_racedate,self.dt_dob)
            agpercent,agresult,agfactor = ag.agegrade(racedateage,resultgen,course.distmiles,timeu.timesecs(resulttime))
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
        if self.racefile:
            self._RACE.close()

