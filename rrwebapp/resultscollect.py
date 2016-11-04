###########################################################################################
#   resultscollect - collect race results data from a service
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/03/16    Lou King    Create
#
#   Copyright 2016 Lou King
###########################################################################################
'''
resultscollect - collect race results data from a service
===================================================================


'''

# standard
import csv
from datetime import datetime
import time

# pypi

# github

# other

# home grown
from . import app
from loutilities.transform import Transform
from loutilities import timeu
ftime = timeu.asctime('%Y-%m-%d')

########################################################################
class ResultsCollect(object):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self, servicename, resultfilehdr, resultattrs):
    #----------------------------------------------------------------------
        '''
        initialize object instance

        may be overridden when ResultsCollect is instantiated, but overriding method must call
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
            dt_begindate = timeu.epoch2dt(begindate)
            adj_begindate = datetime(dt_begindate.year,dt_begindate.month,dt_begindate.day,0,0,0)
            begindate = timeu.dt2epoch(adj_begindate)
            dt_enddate = timeu.epoch2dt(enddate)
            adj_enddate = datetime(dt_enddate.year,dt_enddate.month,dt_enddate.day,23,59,59)
            enddate = timeu.dt2epoch(adj_enddate)
            
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
    
