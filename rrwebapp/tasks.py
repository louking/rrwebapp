"""
tasks - define background tasks
=================================
"""
# standard
import os.path
import os
import traceback

# pypi
from loutilities.timeu import timesecs
from celery.utils.log import get_task_logger

# home grown
from .celery import celery
from .model import ManagedResult, Race
from .model import db, ApiCredentials, RaceResultService
from .settings import productname
from .resultsutils import StoreServiceResults
from .resultssummarize import summarize
from .resultsutils import ImportResults
from .raceresults import RaceResults

class ParameterError(Exception): pass

# set up logger
logger = get_task_logger(__name__)

# set up services to collect and store data from
normstoreattrs = 'runnername,dob,gender,sourceid,sourceresultid,racename,date,raceloc,raceage,distmiles,time,timesecs,fuzzyage'.split(',')
collectservices = {}
storeservices = {}

## athlinks handling
from .athlinksresults import AthlinksCollect, AthlinksResultFile
athl = AthlinksCollect()
collectservices['athlinks'] = athl.collect
athlinksattrs = 'name,dob,gender,id,entryid,racename,racedate,raceloc,age,distmiles,resulttime,timesecs,fuzzyage'.split(',')
athlinkstransform = dict(list(zip(normstoreattrs, athlinksattrs)))
# dates come in as datetime, reset to ascii
# athlinkstransform['dob'] = lambda row: ftime.dt2asc(getattr(row, 'dob'))
# athlinkstransform['date'] = lambda row: ftime.dt2asc(getattr(row, 'racedate'))
athlinkstransform['timesecs'] = lambda row: timesecs(getattr(row, 'resulttime'))    # not provided by athlinks
athlresults = AthlinksResultFile()
storeservices['athlinks'] = StoreServiceResults('athlinks', athlresults, athlinkstransform)

## ultrasignup handling
from .ultrasignupresults import UltraSignupCollect, UltraSignupResultFile
us = UltraSignupCollect()
collectservices['ultrasignup'] = us.collect
usattrs = 'name,dob,gender,sourceid,sourceresultid,race,date,raceloc,age,miles,time,timesecs,fuzzyage'.split(',')
ustransform = dict(list(zip(normstoreattrs, usattrs)))
ustransform['sourceid'] = lambda row: None
ustransform['sourceresultid'] = lambda row: None
ustransform['fuzzyage'] = lambda row: False
usresults = UltraSignupResultFile()
storeservices['ultrasignup'] = StoreServiceResults('ultrasignup', usresults, ustransform)

## runningahead handling
from .runningaheadresults import RunningAHEADCollect, RunningAHEADResultFile
ra = RunningAHEADCollect()
collectservices['runningahead'] = ra.collect
raattrs = 'name,dob,gender,sourceid,sourceresultid,race,date,loc,age,miles,time,timesecs,fuzzyage'.split(',')
ratransform = dict(list(zip(normstoreattrs, raattrs)))
ratransform['sourceid'] = lambda row: ''
ratransform['sourceresultid'] = lambda row: ''
ratransform['fuzzyage'] = lambda row: False
ratransform['loc'] = lambda row: ''
raresults = RunningAHEADResultFile()
storeservices['runningahead'] = StoreServiceResults('runningahead', raresults, ratransform)


def getservicename(service):
    apicredential = ApiCredentials.query.filter_by(id=service.apicredentials_id).first()
    servicename = apicredential.name
    return servicename

def getservicekey(service):
    apicredential = ApiCredentials.query.filter_by(id=service.apicredentials_id).first()
    servicekey = apicredential.key
    return servicekey

@celery.task(bind=True)
def importresultstask(self, club_id, raceid, resultpathname):
    '''
    background task to import results

    :param club_id: club identifier
    :param raceid: race identifier
    :param resultpathname: full pathname of results file
    '''
    try:
        # create race results iterator
        race = Race.query.filter_by(club_id=club_id,id=raceid).first()
        rr = RaceResults(resultpathname,race.distance)

        # count rows, inefficiently. TODO: add count() method to RaceResults class
        try:
            total = 0
            while True:
                next(rr)
                total += 1
        except StopIteration:
            pass

        # only update state max 100 times over course of file, but don't make it too small
        statemod = total // 100
        if statemod == 0:
            statemod = 1

        # start over
        rr.close()
        rr = RaceResults(resultpathname,race.distance)

        # create importer
        importresults = ImportResults(club_id, raceid)
        
        # collect results from resultsfile
        numentries = 0
        dbresults = []
        logfirst = True
        while True:
            try:
                if numentries % statemod == 0:
                    self.update_state(state='PROGRESS', meta={'current': numentries, 'total': total})
                fileresult = next(rr)
                if logfirst:
                    logger.debug('first file result {}'.format(fileresult))
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

@celery.task(bind=True)
def analyzeresultstask(self, club_id, action, resultsurl, memberfile, detailfile, summaryfile, fulldetailfile, taskfile):
    
    try:
        # no status yet
        status = {}

        # special processing for scoretility service
        rrs_rrwebapp_id = ApiCredentials.query.filter_by(name=productname()).first().id
        rrs_rrwebapp = RaceResultService(club_id,rrs_rrwebapp_id)

        # remember servicenames for status update
        clubservices = RaceResultService.query.filter_by(club_id = club_id).all()
        servicenames = [s.apicredentials.name for s in clubservices] + [getservicename(rrs_rrwebapp)]

        # collect results and store in database
        if action == 'collect':
            # how many members? Note memberfile always comes as list, with a header line
            nummembers = len(memberfile) - 1

            # collect all the data
            # each service creates a detailed file
            for service in clubservices + [rrs_rrwebapp]:
                status[getservicename(service)] = {'status': 'starting', 'lastname': '', 'processed': 0, 'total': nummembers}

            for service in clubservices:
                servicename = getservicename(service)
                key = getservicekey(service)
                thisdetailfile = detailfile.format(service=servicename)

                status[servicename]['status'] = 'collecting'
                collectservices[servicename](self, club_id, memberfile, thisdetailfile, status)

            # add results to database from all the services which were collected
            # add new entries, update existing entries
            for service in clubservices:
                servicename = getservicename(service)
                thisdetailfile = detailfile.format(service=servicename)
                status[servicename]['status'] = 'saving results'
                status[servicename]['total'] = storeservices[servicename].get_count(thisdetailfile)
                status[servicename]['processed'] = 0
                status[servicename]['lastname'] = ''
            for service in clubservices:
                servicename = getservicename(service)
                thisdetailfile = detailfile.format(service=servicename)
                storeservices[servicename].storeresults(self, status, club_id, thisdetailfile)

            for service in servicenames:
                status[service]['status'] = 'done collecting'

        elif action == 'summarize':
        # compile the data into summary from database, deduplicating for the summary information
        # NOTE: because this is a summary, this cannot be filtered, e.g., by date range
        #       so this is fixed a three year window
            for service in clubservices + [rrs_rrwebapp]:
                status[getservicename(service)] = {'status': 'starting', 'lastname': '', 'processed': 0, 'total': 0}

            summarize(self, club_id, servicenames, status, summaryfile, fulldetailfile, resultsurl)

            for service in servicenames:
                status[service]['status'] = 'completed'

        # unknown action
        else:
            raise ParameterError('unknown action "{}"" received'.format(action))

        # not in a task any more
        if os.path.isfile(taskfile):
            os.remove(taskfile)

        # TODO: save last status for initial status on resultsanalysisstatus view
        
        # save all our work
        db.session.commit()
        return {'progress':status}

    except:
        # log the exception first in case there's any subsequent error
        logger.error(traceback.format_exc())

        # tell the admins that this happened
        celery.mail_admins('[scoretility] analyzeresultstask: exception occurred', traceback.format_exc())

        # not in a task any more
        if os.path.isfile(taskfile):
            os.remove(taskfile)

        # roll back database updates and close transaction
        db.session.rollback()

        # report this as success, but since traceback is present, server will tell user
        return {'progress':status, 'traceback': traceback.format_exc()}


