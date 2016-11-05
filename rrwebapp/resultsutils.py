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

# pypi

# homegrown
from . import app
from database_flask import db   
from racedb import insert_or_update, RaceResult, Runner, Race
from race import race_fixeddist
from loutilities.csvu import str2num
from loutilities.timeu import age, asctime, epoch2dt, dt2epoch
from loutilities.agegrade import AgeGrade
from loutilities.transform import Transform

ftime = asctime('%Y-%m-%d')

RACEEPSILON = .01  # in miles, to allow for floating point precision error in database
ag = AgeGrade()

class ParameterError(Exception): pass

########################################################################
class Record():
########################################################################
    pass

########################################################################
class StoreServiceResults():
########################################################################
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

    #----------------------------------------------------------------------
    def __init__(self, servicename, serviceaccessor, xservice2norm):
    #----------------------------------------------------------------------
        self.servicename = servicename
        self.serviceaccessor = serviceaccessor
        self.service2norm = Transform(xservice2norm, sourceattr=True, targetattr=True)

    #----------------------------------------------------------------------
    def get_count(self, filename):
    #----------------------------------------------------------------------
        '''
        return the length of the service accessor file

        :param filename: name of the file
        :rtype: number of lines in the file
        '''
        self.serviceaccessor.open(filename)
        numlines = self.serviceaccessor.count()
        self.serviceaccessor.close()

        return numlines

    #----------------------------------------------------------------------
    def storeresults(self, thistask, status, club_id, filename):
    #----------------------------------------------------------------------
        '''
        create service accessor and open file
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
            filerecord = self.serviceaccessor.next()
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
                raise ParameterError, "could not find runner in database: {} line {} {} {} {}".format(filename, status[self.servicename]['processed']+2, result.runnername, result.dob, result.gender)

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
                raise ParameterError, "could not find race in database: {} line {} {} {} {}".format(filename, status[self.servicename]['processed']+2, result.racename, result.date, result.distmiles)

            ## update or create result in database
            agage = age(ftime.asc2dt(race.date), ftime.asc2dt(runner.dateofbirth))
            result.agpercent, result.agtime, result.agfactor = ag.agegrade(agage, runner.gender, result.distmiles, result.timesecs)

            dbresult = RaceResult(club_id, runner.id, race.id, None, result.timesecs, runner.gender, agage, instandings=False)
            for attr in ['agfactor', 'agtime', 'agpercent', 'source', 'sourceid', 'sourceresultid', 'fuzzyage']:
                setattr(dbresult,attr,getattr(result,attr))

            insert_or_update(db.session, RaceResult, dbresult, skipcolumns=['id'], 
                             club_id=club_id, source=self.servicename, runnerid=runner.id, raceid=race.id)

            # update the number of results processed and pass back the status
            status[self.servicename]['lastname'] = result.runnername
            status[self.servicename]['processed'] += 1
            thistask.update_state(state='PROGRESS', meta={'progress':status})

        # finished reading results, close input file
        self.serviceaccessor.close()

########################################################################
class CollectServiceResults(object):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self, servicename, resultfilehdr, resultattrs):
    #----------------------------------------------------------------------
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

    #----------------------------------------------------------------------
    def openservice(self, club_id):
    #----------------------------------------------------------------------
        '''
        initialize service
        recommended that the overriding method save service instance in `self.service`

        must be overridden when ResultsCollect is instantiated

        :param club_id: club.id for club this service is operating on
        '''
        pass

    #----------------------------------------------------------------------
    def getresults(self, name, fname, lname, gender, dt_dob, begindate, enddate):
    #----------------------------------------------------------------------
        '''
        retrieves a list of results for a single name

        must be overridden when ResultsCollect is instantiated

        use gender, dt_dob to filter errant race results, based on age of runner on race day

        :param name: name of participant for which results are to be returned
        :param fname: first name of participant
        :param lname: last name of participant
        :param gender: 'M' or 'F'
        :param dt_dob: participant's date of birth, as datetime 
        :param begindate: epoch time for start of results, 00:00:00 on date to begin
        :param end: epoch time for end of results, 23:59:59 on date to finish
        :rtype: list of serviceresults, each of which can be processed by convertresult
        '''
        pass

    #----------------------------------------------------------------------
    def convertserviceresult(self, result):
    #----------------------------------------------------------------------
        '''
        converts a single service result to dict suitable to be saved in resultfile

        result must be converted to dict with keys in `resultfilehdr` provided at instance creation

        must be overridden when ResultsCollect is instantiated

        use return value of None for cases when results could not be filtered by `:meth:getresults`

        :param result: single service result, from list retrieved through `getresults`
        :rtype: dict with keys matching `resultfilehdr`, or None if result is not to be saved
        '''
        pass

    #----------------------------------------------------------------------
    def closeservice(self):
    #----------------------------------------------------------------------
        '''
        closes service, if necessary

        may be overridden when ResultsCollect is instantiated
        '''
        pass


    #----------------------------------------------------------------------
    def collect(self, thistask, club_id, searchfile, resultfile, status, begindate=ftime.asc2epoch('1970-01-01'), enddate=ftime.asc2epoch('2999-12-31')):
    #----------------------------------------------------------------------
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
        if type(searchfile) == list:
            _IN = searchfile
        else:
            _IN = open(searchfile,'rb')
        IN = csv.DictReader(_IN)

        _OUT = open(resultfile,'wb')
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
                    outrec = self.convertserviceresult(result)
                    # only save if service wanted to save
                    if outrec:
                        OUT.writerow(outrec)
        
                # update status
                status[self.servicename]['lastname'] = name
                status[self.servicename]['processed'] += 1
                thistask.update_state(state='PROGRESS', meta={'progress':status})

        finally:
            self.closeservice()
            _OUT.close()
            if type(searchfile) != list:
                _IN.close()

        finish = time.time()
        app.logger.debug('elapsed time (min) = {}'.format((finish-start)/60))
    
########################################################################
class ServiceResult():
########################################################################
    '''
    represents single result from service
    '''

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        
        reprstr = 'ServiceResult('
        for attr in resultattrs:
            reprstr += '{}={},'.format(attr,getattr(self,attr))
        reprstr = reprstr[:-1] + ')'
        return reprstr
    
########################################################################
class ServiceResultFile(object):
########################################################################
    '''
    represents file of athlinks results collected from athlinks
    
    TODO:: add write methods, and update :func:`collect` to use :class:`ServiceResult` class
    '''
   
    #----------------------------------------------------------------------
    def __init__(self, servicename, mapping):
    #----------------------------------------------------------------------
        self.servicename = servicename
        self.mapping = mapping
        self.transform = Transform(mapping, sourceattr=False, targetattr=True).transform
        
    #----------------------------------------------------------------------
    def open(self, filename, mode='rb'):
    #----------------------------------------------------------------------
        '''
        open athlinks result file
        
        :param mode: 'rb' or 'wb' -- TODO: support 'wb'
        '''
        if mode[0] not in ['r']:
            raise invalidParameter, 'mode {} not currently supported'.format(mode)
    
        self._fh = open(filename,mode)

        # count the number of lines then reset the file pointer -- don't count header
        self._numlines = sum(1 for line in self._fh) - 1
        self._fh.seek(0)

        # create the DictReader object
        self._csv = csv.DictReader(self._fh)
        
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
            delattr(self,'_numlines')
        
    #----------------------------------------------------------------------
    def count(self):
    #----------------------------------------------------------------------
        return self._numlines
    
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
        
        serviceresult = ServiceResult()
        self.transform(fresult, serviceresult)
                
        return serviceresult
    
