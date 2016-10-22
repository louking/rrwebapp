#!/usr/bin/python
###########################################################################################
#   athlinksresults - manage race results data from athlinks
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/13/13    Lou King    Create
#
#   Copyright 2013 Lou King
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
'''
athlinksresults - manage race results data from athlinks
===================================================================


'''

# standard
import pdb
import argparse
import os.path
import tempfile
import csv
import datetime
import time

# pypi

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from loutilities import agegrade
from running import athlinks
from database_flask import db   # this is ok because this module only runs under flask
from racedb import Course, Race, MAX_RACENAME_LEN, MAX_LOCATION_LEN

# see http://api.athlinks.com/Enums/RaceCategories
CAT_RUNNING = 2
CAT_TRAILS = 15
race_category = {CAT_RUNNING:'road',CAT_TRAILS:'trail'}
ag = agegrade.AgeGrade()
class invalidParameter(Exception): pass

# resultfilehdr needs to associate 1:1 with resultattrs
resultfilehdr = 'GivenName,FamilyName,name,DOB,Gender,athlmember,athlid,race,date,loc,age,fuzzyage,miles,km,category,time,ag'.split(',')
resultattrs = 'firstname,lastname,name,dob,gender,member,id,racename,racedate,raceloc,age,fuzzyage,distmiles,distkm,racecategory,resulttime,resultagegrade'.split(',')
resultdates = 'dob,racedate'.split(',')
hdrtransform = dict(zip(resultfilehdr,resultattrs))
ftime = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def collect(self, club_id, searchfile, outfile, coursefile, status, begindate=ftime.asc2epoch('1970-01-01'), enddate=ftime.asc2epoch('2999-12-31'), key=None):
#----------------------------------------------------------------------
    '''
    collect race results from athlinks
    
    :param self: this is required for task self.update_state()
    :param club_id: club id for club being operated on
    :param searchfile: path to file containing names, genders, birth dates to search for
    :param outfile: detailed output file path
    :param coursefile: debug coursefile saves information about races added to the database, None to turn off coursefile output
    :param status: dict containing current status
    :param begindate: epoch time - choose races between begindate and enddate
    :param enddate: epoch time - choose races between begindate and enddate
    :param key: key for access to athlinks
    '''
    
    # open files
    if type(searchfile) == list:
        _IN = searchfile
    else:
        _IN = open(searchfile,'rb')
    IN = csv.DictReader(_IN)

    _OUT = open(outfile,'wb')
    OUT = csv.DictWriter(_OUT,resultfilehdr)
    OUT.writeheader()

    # debug file for races saved
    if coursefile:
        _COURSE = open(coursefile, 'wb')
        coursefields = 'id,name,date,distmiles,status,runner'.split(',')
        COURSE = csv.DictWriter(_COURSE, coursefields)
        COURSE.writeheader()

    # common fields between input and output
    commonfields = 'GivenName,FamilyName,DOB,Gender'.split(',')

    try:

        # create athlinks
        athl = athlinks.Athlinks(debug=True, key=key)

        # reset begindate to beginning of day, enddate to end of day
        dt_begindate = timeu.epoch2dt(begindate)
        adj_begindate = datetime.datetime(dt_begindate.year,dt_begindate.month,dt_begindate.day,0,0,0)
        begindate = timeu.dt2epoch(adj_begindate)
        dt_enddate = timeu.epoch2dt(enddate)
        adj_enddate = datetime.datetime(dt_enddate.year,dt_enddate.month,dt_enddate.day,23,59,59)
        enddate = timeu.dt2epoch(adj_enddate)
        
        # get today's date for high level age filter
        start = time.time()
        today = timeu.epoch2dt(start)
        
        # loop through runners in the input file
        for runner in IN:
            name = ' '.join([runner['GivenName'],runner['FamilyName']])

            e_dob = ftime.asc2epoch(runner['DOB'])
            dt_dob = ftime.asc2dt(runner['DOB'])
            
            # get results for this athlete
            results = athl.listathleteresults(name)
            
            # loop through each result
            for result in results:
                e_racedate = athlinks.gettime(result['Race']['RaceDate'])
                
                # skip result if outside the desired time window
                if e_racedate < begindate or e_racedate > enddate: continue
                
                # create output record and copy common fields
                outrec = {}
                for field in commonfields:
                    outrec[field] = runner[field]
                    
                # skip result if runner's age doesn't match the age within the result
                # sometimes athlinks stores the age group of the runner, not exact age,
                # so also check if this runner's age is within the age group, and indicate if so
                dt_racedate = timeu.epoch2dt(e_racedate)
                racedateage = timeu.age(dt_racedate,dt_dob)
                resultage = int(result['Age'])
                if resultage != racedateage:
                    # if results are not stored as age group, skip this result
                    if (resultage/5)*5 != resultage:
                        continue
                    # result's age might be age group, not exact age
                    else:
                        # if runner's age consistent with race age, use result, but mark "fuzzy"
                        if (racedateage/5)*5 == resultage:
                            outrec['fuzzyage'] = 'Y'
                        # otherwise skip result
                        else:
                            continue
                
                # skip result if runner's gender doesn't match gender within the result
                resultgen = result['Gender'][0]
                if resultgen != runner['Gender'][0]: continue
                
                # some debug items - assume everything is cached
                coursecached = True
                racecached = True

                # get course used for this result
                courseid = '{}/{}'.format(result['Race']['RaceID'], result['CourseID'])
                course = Course.query.filter_by(source='athlinks', sourceid=courseid).first()
                if not course:
                    coursecached = False

                    coursedata = athl.getcourse(result['Race']['RaceID'], result['CourseID'])

                    distmiles = athlinks.dist2miles(coursedata['Courses'][0]['DistUnit'],coursedata['Courses'][0]['DistTypeID'])
                    distkm = athlinks.dist2km(coursedata['Courses'][0]['DistUnit'],coursedata['Courses'][0]['DistTypeID'])
                    if distkm < 0.050: continue # skip timed events, which seem to be recorded with 0 distance

                    # skip result if not Running or Trail Running race
                    thiscategory = coursedata['Courses'][0]['RaceCatID']
                    if thiscategory not in race_category: continue
                
                    course = Course()
                    course.source = 'athlinks'
                    course.sourceid = courseid

                    racename = csvu.unicode2ascii(coursedata['RaceName'])
                    coursename = csvu.unicode2ascii(coursedata['Courses'][0]['CourseName'])
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
                    # Race has uniqueconstraint for club_id/name/year. It's been seen that there are additional races in athlinks, 
                    # but just assume the first is the correct one.
                    raceyear = ftime.asc2dt(course.date).year
                    race = Race.query.filter_by(club_id=club_id, name=course.name, year=raceyear).first()
                    ### TODO: should the above be .all() then check for first race within epsilon distance?
                    if not race:
                        racecached = False
                        race = Race(club_id, raceyear)
                        race.name = course.name
                        race.distance = course.distmiles
                        race.date = course.date
                        race.active = True
                        race.external = True
                        db.session.add(race)
                        db.session.flush()  # force id to be created

                    course.raceid = race.id
                    db.session.add(course)
                    db.session.flush()      # force id to be created

                # debug races
                if coursefile:
                    racestatusl = []
                    if not coursecached: racestatusl.append('addcourse')
                    if not racecached: racestatusl.append('addrace')
                    if not racestatusl: racestatusl.append('cached')
                    racestatus = '-'.join(racestatusl)
                    courserow = {'status': racestatus, 'runner': name}

                    for coursefield in coursefields:
                        if coursefield in ['status', 'runner']: continue
                        courserow[coursefield] = getattr(course,coursefield)
                    COURSE.writerow(courserow)

                # fill in output record fields from runner, result, course
                # combine name, get age
                outrec['name'] = '{} {}'.format(runner['GivenName'],runner['FamilyName'])
                outrec['age'] = result['Age']

                # leave athlmember and athlid blank if result not from an athlink member
                athlmember = result['IsMember']
                if athlmember:
                    outrec['athlmember'] = 'Y'
                    outrec['athlid'] = result['RacerID']

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

                # leave out age grade if exception occurs, skip results which have outliers
                try:
                    agpercent,agresult,agfactor = ag.agegrade(racedateage,resultgen,course.distmiles,timeu.timesecs(resulttime))
                    outrec['ag'] = agpercent
                    if agpercent < 15 or agpercent >= 100: continue # skip obvious outliers
                except:
                    pass

                OUT.writerow(outrec)
    
            # update status
            status['athlinks']['lastname'] = name
            status['athlinks']['processed'] += 1
            self.update_state(state='PROGRESS', meta={'progress':status})

    finally:
        _OUT.close()
        if type(searchfile) != list:
            _IN.close()
        if coursefile:
            _COURSE.close()
    
    finish = time.time()
    print 'number of URLs retrieved = {}'.format(athl.geturlcount())
    print 'elapsed time (min) = {}'.format((finish-start)/60)
    
########################################################################
class AthlinksResult():
########################################################################
    '''
    represents single result from athlinks
    '''


    #----------------------------------------------------------------------
    def __init__(self,**myattrs):
    #----------------------------------------------------------------------

        for attr in resultattrs:
            setattr(self,attr,None)
            
        for attr in myattrs:
            if attr not in resultattrs:
                raise invalidParameter,'unknown attribute: {}'.format(attr)
            setattr(self,attr,myattrs[attr])
    
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        
        reprstr = 'athlinksresult.AthlinksResult('
        for attr in resultattrs:
            reprstr += '{}={},'.format(attr,getattr(self,attr))
        reprstr = reprstr[:-1] + ')'
        return reprstr
    
########################################################################
class AthlinksResultFile():
########################################################################
    '''
    represents file of athlinks results collected from athlinks
    
    TODO:: add write methods, and update :func:`collect` to use :class:`AthlinksResult` class
    '''
   
    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------
        self.filename = filename
        
    #----------------------------------------------------------------------
    def open(self,mode='rb'):
    #----------------------------------------------------------------------
        '''
        open athlinks result file
        
        :param mode: 'rb' or 'wb' -- TODO: support 'wb'
        '''
        if mode[0] not in 'r':
            raise invalidParameter, 'mode {} not currently supported'.format(mode)
    
        self._fh = open(self.filename,mode)
        if mode[0] == 'r':
            self._csv = csv.DictReader(self._fh)
        else:
            pass
        
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close athlinks result file
        '''
        if hasattr(self,'_fh'):
            self._fh.close()
            delattr(self,'_fh')
            delattr(self,'_csv')
        
    #----------------------------------------------------------------------
    def next(self):
    #----------------------------------------------------------------------
        '''
        get next :class:`AthlinksResult`
        
        :rtype: :class:`AthlinksResult`, or None when end of file reached
        '''
        try:
            fresult = self._csv.next()
            
        except StopIteration:
            return None
        
        aresultargs = {}
        for fattr in hdrtransform:
            aattr = hdrtransform[fattr]
            
            # special handling for gender
            if aattr == 'gender':
                aresultargs[aattr] = fresult[fattr][0]
                
            # special handling for dates
            elif aattr in resultdates:
                aresultargs[aattr] = ftime.asc2dt(fresult[fattr])
                
            else:
                # convert numbers
                try:
                    aresultargs[aattr] = int(fresult[fattr])
                except ValueError:
                    try:
                        aresultargs[aattr] = float(fresult[fattr])
                    except ValueError:
                        aresultargs[aattr] = fresult[fattr]
                
        return AthlinksResult(**aresultargs)
    
