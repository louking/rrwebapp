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

# pypi

# homegrown
from . import app
from database_flask import db   
from racedb import insert_or_update, RaceResult, Runner, Race
from race import race_fixeddist
from loutilities.csvu import str2num
from loutilities.timeu import age, asctime
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
    :param serviceaccessclass: class to access result from service file
    :param xservice2norm: {'normattr_n':'serviceattr_n', 'normattr_m':f(servicerow), ...}
    '''

    #----------------------------------------------------------------------
    def __init__(self, servicename, serviceaccessclass, xservice2norm):
    #----------------------------------------------------------------------
        self.servicename = servicename
        self.serviceaccessclass = serviceaccessclass
        self.service2norm = Transform(xservice2norm, sourceattr=True, targetattr=True)

        self.accessor = None

    #----------------------------------------------------------------------
    def get_count(self, filename):
    #----------------------------------------------------------------------
        '''
        return the length of the service accessor file

        :param filename: name of the file
        :rtype: number of lines in the file
        '''
        accessor = self.serviceaccessclass(filename)
        accessor.open()
        numlines = accessor.count()
        accessor.close()

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
        self.accessor = self.serviceaccessclass(filename)
        self.accessor.open()

        status[self.servicename]['total'] = self.accessor.count()
        status[self.servicename]['processed'] = 0

        # loop through all results and store in database
        try:
            while True:
                filerecord = self.accessor.next()
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

            # finished reading results
            status[self.servicename]['status'] = 'completed'
            thistask.update_state(state='PROGRESS', meta={'progress':status})
        
        # close input file
        finally:
            self.accessor.close()
            self.accessor = None


