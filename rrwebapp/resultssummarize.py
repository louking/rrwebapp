#!/usr/bin/python
###########################################################################################
#   resultssummarize - render age grade statistics for a club
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/17/13    Lou King    Create
#   10/27/16    Lou King    copied from running/renderclubagstats.py
#
#   Copyright 2016 Lou King
###########################################################################################
'''
resultssummarize - render age grade statistics for a club
===================================================================

Render club age grade statistics, based on collected athlinks statistics (collectathlinksresults),
club data in runningahead ( (TODO: RA data) analyzeagegrade) and club results (runningclub.exportresults)

'''

# standard
import tempfile
import csv
from datetime import datetime
import collections
import time
from urllib.parse import urlparse, parse_qsl, urlunparse
from urllib.parse import urlencode
from copy import copy
import json

# pypi
from flask import current_app
from loutilities import timeu
from loutilities.renderrun import rendertime

# home grown
from . import analyzeagegrade
from .resultsutils import ServiceAttributes, LocationServer, get_distance
from .model import Club, RaceResultService, ApiCredentials, RaceResult, Race, Location, Runner
from .settings import productname

ftime = timeu.asctime('%Y-%m-%d')

class invalidParameter(Exception): pass
METERSPERMILE = 1609.344

# table for driving trend plotting
# *** must match trendlimits in results_scatterplot.js
TRENDLIMITS = collections.OrderedDict([
            #   [min,      max)
               ((0,        5000.00), ('<5K','to5k')),
               ((5000.00,  21082),   ('5K - <HM','5ktohm')),
               ((21082,    42196),   ('HM - Mara','hmtomara')),
               ((42196,    200000),  ('Ultra','ultra')),
              ])

# priorities for deduplication
# lowest priority value of duplicate entries is kept
# must match priorities in results_scatterplot.js
PRIO_CLUBRACES = 1
PRIO_ULTRASIGNUP = 2
PRIO_ATHLINKS = 3
PRIO_RUNNINGAHEAD = 4
PRIO_STRAVA = 5
priority = {
    productname():    PRIO_CLUBRACES,
    'ultrasignup':  PRIO_ULTRASIGNUP,
    'athlinks':     PRIO_ATHLINKS,
    'runningahead': PRIO_RUNNINGAHEAD,
    'strava':       PRIO_STRAVA,
}
    
#----------------------------------------------------------------------
def mean(items):
#----------------------------------------------------------------------
    return float(sum(items))/len(items) if len(items) > 0 else float('nan')

#----------------------------------------------------------------------
def initaagrunner(aag, thisrunner, fname, lname, gender, dob, runnerid):
#----------------------------------------------------------------------
    '''
    initializaze :class:`AnalyzeAgeGrade` object, if not already initialized
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param thisrunner: key for aag structure: (runnername, asciidob)
    :param fname: first name for runner
    :param lname: last name for runner
    :param gender: M or F
    :param dob: datetime date of birth
    :param runnerid: runner.id
    '''
    if thisrunner not in aag:
        aag[thisrunner] = analyzeagegrade.AnalyzeAgeGrade()
        aag[thisrunner].set_runner(thisrunner[0], fname, lname, gender, dob, runnerid)
    
        
#----------------------------------------------------------------------
def summarize(thistask, club_id, sources, status, summaryfile, detailfile, resultsurl, minage=12, minagegrade=20, minraces=3 , mintrend=2, numyears=3, begindate=None, enddate=None):
#----------------------------------------------------------------------
    '''
    render collected results

    :param thistask: this is required for task thistask.update_state()
    :param club_id: identifies club for which results are to be stored
    :param sources: list of sources / services we're keeping status for
    :param summaryfile: summary file name (.csv)
    :param detailfile: detail file name (.csv)
    :param resultsurl: base url to send results to, for link in summary table
    :param minage: minimum age to keep track of stats
    :param minagegrade: minimum age grade
    :param minraces: minimum races in the same year as enddate
    :param mintrend: minimum races over the full period for trendline
    :param begindate: render races between begindate and enddate, datetime
    :param enddate: render races between begindate and enddate, datetime
    '''
    
    # get club slug and location for later
    club = Club.query.filter_by(id=club_id).first()
    clubslug = club.shname
    locsvr = LocationServer()
    clublocation = locsvr.getlocation(club.location)

    # get maxdistance by service
    services = RaceResultService.query.filter_by(club_id=club_id).join(ApiCredentials).all()
    maxdistance = {}
    for service in services:
        attrs = ServiceAttributes(club_id, service.apicredentials.name)
        # current_app.logger.debug('service {} attrs {}'.format(service, attrs.__dict__))
        if attrs.maxdistance:
            maxdistance[service.apicredentials.name] = attrs.maxdistance
        else:
            maxdistance[service.apicredentials.name] = None
    maxdistance[productname()] = None

    # set up date range. begindate and enddate take precedence, else use numyears from today
    if not (begindate and enddate):
        etoday = time.time()
        today = timeu.epoch2dt(etoday)
        begindate = datetime(today.year-numyears+1,1,1)
        enddate = datetime(today.year,12,31)

    firstyear = begindate.year
    lastyear = enddate.year
    yearrange = list(range(firstyear,lastyear+1))
    
    # get all the requested result data from the database and save in a data structure indexed by runner
    ## first get the data from the database
    results = RaceResult.query.join(Race).join(Runner).filter(RaceResult.club_id==club_id, 
                Race.date.between(ftime.dt2asc(begindate), ftime.dt2asc(enddate)), Runner.member==True, Runner.active==True).order_by(Runner.lname, Runner.fname).all()

    ## then set up our status and pass to the front end
    for source in sources:
        status[source]['status'] = 'summarizing'
        status[source]['lastname'] = ''
        status[source]['processed'] = 0
        status[source]['total'] = sum([1 for result in results if result.source==source])
    thistask.update_state(state='PROGRESS', meta={'progress':status})
    
    ## prepare to save detail file, for debugging
    detlfields = 'runnername,runnerid,dob,gender,resultid,racename,racedate,series,distmiles,distkm,time,timesecs,agpercent,source,sourceid'.split(',')
    detailfname = detailfile
    _DETL = open(detailfname,'w', newline='')
    DETL = csv.DictWriter(_DETL, detlfields)
    DETL.writeheader()

    ## then fill in data structure to hold AnalyzeAgeGrade objects
    ## use OrderedDict to force aag to be in same order as DETL file, for debugging
    aag = collections.OrderedDict()
    for result in results:
        # skip results which are too far away, if a maxdistance is defined for this source
        if maxdistance[result.source]:
            locationid = result.race.locationid
            if not locationid: continue
            racelocation = Location.query.filter_by(id=locationid).first()
            distance = get_distance(clublocation, racelocation)
            if distance == None or distance > maxdistance[result.source]: continue

        thisname = (result.runner.name.lower(), result.runner.dateofbirth)
        initaagrunner(aag, thisname, result.runner.fname, result.runner.lname, result.runner.gender, ftime.asc2dt(result.runner.dateofbirth), result.runner.id)
        
        # determine location name. any error gets null string
        locationname = ''
        if result.race.locationid:
            location = Location.query.filter_by(id=result.race.locationid).first()
            if location: 
                locationname = location.name

        thisstat = aag[thisname].add_stat(ftime.asc2dt(result.race.date), result.race.distance*METERSPERMILE, result.time, race=result.race.name,
                               loc=locationname, fuzzyage=result.fuzzyage,
                               source=result.source, priority=priority[result.source])

        ### TODO: store result's agpercent, in AgeGrade.crunch() skip agegrade calculation if already present
        DETL.writerow(dict(
                runnername = result.runner.name,
                runnerid = result.runner.id,
                dob = result.runner.dateofbirth,
                gender = result.runner.gender,
                resultid = result.id,
                racename = result.race.name,
                racedate = result.race.date,
                series = result.series.name if result.seriesid else None,
                distmiles = result.race.distance,
                distkm = result.race.distance*(METERSPERMILE/1000),
                timesecs = result.time,
                time = rendertime(result.time,0),
                agpercent = result.agpercent,
                source = result.source,
                sourceid = result.sourceid,
            ))

    ## close detail file
    _DETL.close()

    # initialize summary file
    summfields = ['name', 'lname', 'fname', 'age', 'gender']
    datafields = copy(summfields)
    distcategories = ['overall'] + [TRENDLIMITS[tlimit][0] for tlimit in TRENDLIMITS]
    datacategories = ['overall'] + [TRENDLIMITS[tlimit][1] for tlimit in TRENDLIMITS]
    stattypes = ['1yr agegrade','avg agegrade','trend','numraces','stderr','r-squared','pvalue']
    statdatatypes = ['1yr-agegrade','avg-agegrade','trend','numraces','stderr','r-squared','pvalue']
    for stattype, statdatatype in zip(stattypes, statdatatypes):
        for distcategory, datacategory in zip(distcategories, datacategories):
            summfields.append('{}\n{}'.format(stattype, distcategory))
            datafields.append('{}-{}'.format(statdatatype, datacategory))
        if stattype == 'numraces':
            for year in yearrange:
                summfields.append('{}\n{}'.format(stattype, year))
                datafields.append('{}-{}'.format(statdatatype, lastyear-year))

    # save summary file columns for resultsanalysissummary
    dtcolumns = json.dumps([{ 'data':d, 'name':d, 'label':l } for d,l in zip(datafields, summfields)])
    columnsfilename = summaryfile + '.cols'
    with open(columnsfilename, 'w') as cols:
        cols.write(dtcolumns)

    # set up summary file
    summaryfname = summaryfile
    _SUMM = open(summaryfname, 'w', newline='')
    SUMM = csv.DictWriter(_SUMM, summfields)
    SUMM.writeheader()
    
    # loop through each member we've recorded information about
    for thisname in aag:
        fullname, fname, lname, gender, dob, runnerid = aag[thisname].get_runner()
        rendername = fullname.title()
        
        # check stats before deduplicating
        statcount = {}
        stats = aag[thisname].get_stats()
        for source in sources:
            statcount[source] = sum([1 for s in stats if s.source == source])

        # remove duplicate entries
        aag[thisname].deduplicate()   
        
        # crunch the numbers
        aag[thisname].crunch()    # calculate age grade for each result
        stats = aag[thisname].get_stats()
        
        jan1 = ftime.asc2dt('{}-1-1'.format(lastyear))
        runnerage = timeu.age(jan1, dob)
        
        # filter out runners younger than allowed
        if runnerage < minage: continue

        # filter out runners who have not run enough races
        stats = aag[thisname].get_stats()
        if enddate:
            lastyear = enddate.year
        else:
            lastyear = timeu.epoch2dt(time.time()).year
        lastyearstats = [s for s in stats if s.date.year==lastyear]
        if len(lastyearstats) < minraces: continue
        
        # fill in row for summary output
        summout = {}

        # get link for this runner's results chart
        # see http://stackoverflow.com/questions/2506379/add-params-to-given-url-in-python
        url_parts = list(urlparse(resultsurl))
        query = dict(parse_qsl(url_parts[4]))
        query.update({'club': clubslug, 'runnerid': runnerid, 'begindate': ftime.dt2asc(begindate), 'enddate': ftime.dt2asc(enddate)})
        url_parts[4] = urlencode(query)
        resultslink = urlunparse(url_parts)

        summout['name'] = '<a href={} target=_blank>{}</a>'.format(resultslink, rendername)
        summout['fname'] = fname
        summout['lname'] = lname
        summout['age'] = runnerage
        summout['gender'] = gender
        
        # set up to collect averages
        avg = collections.OrderedDict()

        # draw trendlines, write output
        allstats = aag[thisname].get_stats()
        if len(allstats) > 0:
            avg['overall'] = mean([s.ag for s in allstats])
        trend = aag[thisname].get_trendline(debuginfo=thisname)

        oneyrstats = [s.ag for s in allstats if s.date.year == lastyear]
        if len(oneyrstats) > 0:
            summout['1yr agegrade\noverall'] = mean(oneyrstats)
        if len(allstats) > 0:
            summout['avg agegrade\noverall'] = avg['overall']
        if trend and len(allstats) >= mintrend and allstats[0].date != allstats[-1].date:
            summout['trend\noverall'] = trend.improvement
            summout['stderr\noverall'] = trend.stderr
            summout['r-squared\noverall'] = trend.r2**2
            summout['pvalue\noverall'] = trend.pvalue
        summout['numraces\noverall'] = len(allstats)
        for year in yearrange:
            summout['numraces\n{}'.format(year)] = len([s for s in allstats if s.date.year==year])
        for tlimit in TRENDLIMITS:
            distcategory,distcolor = TRENDLIMITS[tlimit]
            tstats = [s for s in allstats if s.dist >= tlimit[0] and s.dist < tlimit[1]]
            if len(tstats) > 0:
                avg[distcategory] = mean([s.ag for s in tstats])
                summout['avg agegrade\n{}'.format(distcategory)] = avg[distcategory]
            summout['numraces\n{}'.format(distcategory)] = len(tstats)
            oneyrcategory = [s.ag for s in tstats if s.date.year == lastyear]
            if len(oneyrcategory) > 0:
                summout['1yr agegrade\n{}'.format(distcategory)] = mean(oneyrcategory)
            if len(tstats) >= mintrend and tstats[0].date != tstats[-1].date:
                trend = aag[thisname].get_trendline(thesestats=tstats, debuginfo=thisname)
                # ignore trends which can't be calculated
                if trend:
                    summout['trend\n{}'.format(distcategory)] = trend.improvement
                    summout['stderr\n{}'.format(distcategory)] = trend.stderr
                    summout['r-squared\n{}'.format(distcategory)] = trend.r2
                    summout['pvalue\n{}'.format(distcategory)] = trend.pvalue
        SUMM.writerow(summout)

        # update status
        for source in sources:
            status[source]['processed'] += statcount[source]
            status[source]['lastname'] = rendername
        thistask.update_state(state='PROGRESS', meta={'progress':status})

        
    _SUMM.close()
    
