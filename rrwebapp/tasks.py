"""
tasks - define background tasks
=================================
"""
# standard
import os.path
from os.path import splitext
import os
import traceback
from flask.globals import current_app
from time import time
from platform import system
from difflib import SequenceMatcher

# pypi
from loutilities.timeu import timesecs, epoch2dt, asctime, age as ageasof
from loutilities.flask_helpers.mailer import sendmail
from celery.utils.log import get_task_logger

# home grown
from .celery import celeryapp
from .model import ManagedResult, Race, Runner, RaceResult
from .model import db, ApiCredentials, RaceResultService
from .model import getunique, update, insert_or_update
from .settings import productname
from .resultsutils import StoreServiceResults
from .resultssummarize import summarize
from .resultsutils import ImportResults
from .raceresults import RaceResults
from . import clubmember

class ParameterError(Exception): pass
NAMEDIFFCUTOFF = .6

# set up logger, time
logger = get_task_logger(__name__)
tYmd = asctime('%Y-%m-%d')

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

@celeryapp.task(bind=True)
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
        admins = current_app.config['APP_ADMINS']
        sendmail('[scoretility] importresultstask: exception occurred', 'noreply@scoretility.com', admins, '', text=traceback.format_exc())

        # report this as success, but since traceback is present, server will tell user
        return {'current': 100, 'total': 100, 'traceback': traceback.format_exc()}

@celeryapp.task(bind=True)
def importmemberstask(self, club_id, tempdir, memberpathname, memberfilename):
    try:
        # get file extention
        root,ext = splitext(memberfilename)

        # encoding depends on system type, normal case utf8
        if system != 'Windows':
            encoding = 'utf8'
        # development on Windows
        else:
            encoding = 'cp1252'

        # bring in data from the file
        if ext in ['.xls','.xlsx']:
            members = clubmember.XlClubMember(memberpathname)
        elif ext in ['.csv']:
            members = clubmember.CsvClubMember(memberpathname, encoding=encoding)
        
        # how did this happen?  check member.AjaxImportMembers.allowed_file() for bugs
        else:
            db.session.rollback()
            cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext, memberfilename, memberpathname)
            raise ParameterError(cause)
        
        # remove file and temporary directory
        os.remove(memberpathname)
        try:
            os.rmdir(tempdir)
        # no idea why this can happen; hopefully doesn't happen on linux
        except WindowsError as e:
            current_app.logger.debug('WindowsError exception ignored: {}'.format(e))

        # get all the member runners currently in the database
        # hash them into dict by (name,dateofbirth)
        allrunners = Runner.query.filter_by(club_id=club_id, member=True, active=True).all()
        inactiverunners = {}
        for thisrunner in allrunners:
            inactiverunners[thisrunner.name,thisrunner.dateofbirth] = thisrunner

        # get old clubmembers from database
        dbmembers = clubmember.DbClubMember(club_id=club_id)   # use default database

        # prepare for age check
        thisyear = epoch2dt(time()).year
        asofasc = '{}-1-1'.format(thisyear) # jan 1 of current year
        asof = tYmd.asc2dt(asofasc) 

        # get current list of members
        allmembers = members.getmembers()
        allmembernames = list(allmembers.keys())
        # sort last, first
        allmembernames.sort(key=lambda m: (m.split()[-1].lower(), m.split()[0].lower()))

        # count rows
        total = len(allmembers)

        # only update state max 100 times over course of file, but don't make it too small
        statemod = total // 100
        if statemod == 0:
            statemod = 1

        # process each name in new membership list
        numentries = 0
        for memberndx in range(len(allmembers)):
            name = allmembernames[memberndx]
            # track progress for front end, make sure we update state immediately on start
            if numentries % statemod == 0:
                self.update_state(state='PROGRESS', meta={'current': numentries, 'total': total})
            numentries += 1

            # get list of similar names which are coming up in the allmembernames list
            peeknames = []
            for peekndx in range(memberndx + 1, len(allmembers)):
                peekname = allmembernames[peekndx]
                peekratio = SequenceMatcher(a=name, b=peekname).ratio()
                if peekratio >= NAMEDIFFCUTOFF:
                    peeknames.append(peekname)
                else:
                    break
            
            current_app.logger.debug(f'tasks.importmemberstask: processing {name}')
            if peeknames:
                current_app.logger.debug(f'tasks.importmemberstask: peeknames={peeknames}')

            thesemembers = allmembers[name]
            # NOTE: may be multiple members with same name
            for thismember in thesemembers:
                thisname = thismember['name']
                thisfname = thismember['fname']
                thislname = thismember['lname']
                thisdob = thismember['dob']
                thisgender = thismember['gender'][0].upper()    # male -> M, female -> F
                thishometown = thismember['hometown']
                thisrenewdate = thismember['renewdate']
                thisexpdate = thismember['expdate']

                # prep for if .. elif below by running some queries
                # handle close matches, if DOB does match
                age = ageasof(asof,tYmd.asc2dt(thisdob))
                matchingmember = dbmembers.findmember(thisname,age,asofasc)
                matchingratio = dbmembers.getratio()
                dbmember = None
                if matchingmember:
                    membername,memberdob = matchingmember
                    if memberdob == thisdob:
                        # at this point we might have the member, but need to run through the peeknames to see if any
                        # of these match better. If so, ignore this match as we'll find a better one later
                        foundbetter = False
                        for checkname in peeknames:
                            checkmembers = allmembers[checkname]
                            # first is best match
                            for checkmember in checkmembers:
                                checkmember = dbmembers.findmember(checkmember['name'], age, asofasc)
                                if checkmember:
                                    checkname, checkdob = checkmember
                                    if dbmembers.getratio() > matchingratio and checkdob == thisdob:
                                        current_app.logger.info(f'tasks.importmemberstask: found better match for names similar to {name}, peeking at {checkname} found closer match with db name {membername}')
                                        foundbetter = True
                                        break
                            if foundbetter: break
                        if not foundbetter:
                            dbmember = getunique(db.session,Runner,club_id=club_id,member=True,name=membername,dateofbirth=thisdob)
                
                # no member found, maybe there is nonmember of same name already in database
                if dbmember is None:
                    dbnonmember = getunique(db.session,Runner,club_id=club_id,member=False,name=thisname)
                    # TODO: there's a slim possibility that there are two nonmembers with the same name, but I'm sure we've already
                    # bolloxed that up in importresult as there's no way to discriminate between the two
                    
                    ## make report for new members
                    #NEWMEMCSV.writerow({'name':thisname,'dob':thisdob})
                    
                # see if this runner is a member in the database already, or was a member once and make the update
                # add or update runner in database
                # get instance, if it exists, and make any updates
                found = False
                if dbmember is not None:
                    thisrunner = Runner(club_id,membername,thisdob,thisgender,thishometown,
                                        fname=thisfname,lname=thislname,
                                        renewdate=thisrenewdate,expdate=thisexpdate)
                    
                    # this is also done down below, but must be done here in case member's name has changed
                    if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                        inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))

                    # overwrite member's name if necessary
                    thisrunner.name = thisname  
                    
                    added = update(db.session,Runner,dbmember,thisrunner,skipcolumns=['id'])
                    found = True
                    
                # if runner's name is in database, but not a member, see if this runner is a nonmemember which can be converted
                # Check first result for age against age within the input file
                # if ages match, convert nonmember to member
                elif dbnonmember is not None:
                    # get dt for date of birth, if specified
                    try:
                        dob = tYmd.asc2dt(thisdob)
                    except ValueError:
                        dob = None
                        
                    # nonmember came into the database due to a nonmember race result, so we can use any race result to check nonmember's age
                    if dob:
                        result = RaceResult.query.filter_by(runnerid=dbnonmember.id).first()
                        resultage = result.agage
                        racedate = tYmd.asc2dt(result.race.date)
                        expectedage = ageasof(racedate,dob)
                        #expectedage = racedate.year - dob.year - int((racedate.month, racedate.day) < (dob.month, dob.day))
                    
                    # we found the right person, always if dob isn't specified, but preferably check race result for correct age
                    if dob is None or resultage == expectedage:
                        thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                            fname=thisfname,lname=thislname,
                                            renewdate=thisrenewdate,expdate=thisexpdate)
                        added = update(db.session,Runner,dbnonmember,thisrunner,skipcolumns=['id'])
                        found = True
                    else:
                        current_app.logger.warning('{} found in database, wrong age, expected {} found {} in {}'.format(thisname,expectedage,resultage,result))
                        # TODO: need to make file for these, also need way to force update, because maybe bad date in database for result
                        # currently this will cause a new runner entry
                
                # if runner was not found in database, just insert new runner
                if not found:
                    thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                        fname=thisfname,lname=thislname,
                                        renewdate=thisrenewdate,expdate=thisexpdate)
                    added = insert_or_update(db.session,Runner,thisrunner,skipcolumns=['id'],club_id=club_id,name=thisname,dateofbirth=thisdob)
                    
                # remove this runner from collection of runners which should be deactivated in database
                if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                    inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))
            
        # any runners remaining in 'inactiverunners' should be deactivated
        for (name,dateofbirth) in inactiverunners:
            thisrunner = Runner.query.filter_by(club_id=club_id,name=name,dateofbirth=dateofbirth).first() # should be only one returned by filter
            thisrunner.active = False
    
        # not sure this is necessary, but final state update
        self.update_state(state='PROGRESS', meta={'current': numentries, 'total': total})

        # we're done
        db.session.commit()
        return {'current': total, 'total': total, 'club_id': club_id}

    except:
        # close database session and roll back
        # see http://stackoverflow.com/questions/7672327/how-to-make-a-celery-task-fail-from-within-the-task
        db.session.rollback()

        # tell the admins that this happened
        admins = current_app.config['APP_ADMINS']
        sendmail('[scoretility] importmemberstask: exception occurred', 'noreply@scoretility.com', admins, '', text=traceback.format_exc())

        # report this as success, but since traceback is present, server will tell user
        return {'current': 100, 'total': 100, 'traceback': traceback.format_exc()}


@celeryapp.task(bind=True)
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
        admins = current_app.config['APP_ADMINS']
        sendmail('[scoretility] analyzeresultstask: exception occurred', 'noreply@scoretility.com', admins, '', text=traceback.format_exc())

        # not in a task any more
        if os.path.isfile(taskfile):
            os.remove(taskfile)

        # roll back database updates and close transaction
        db.session.rollback()

        # report this as success, but since traceback is present, server will tell user
        return {'progress':status, 'traceback': traceback.format_exc()}


