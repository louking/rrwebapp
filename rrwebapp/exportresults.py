#!/usr/bin/python
###########################################################################################
# exportresults - export race results from database
#
#	Date		Author		Reason
#	----		------		------
#       11/17/14        Lou King        Move to rrwebapp
#       11/20/13        Lou King        Create
#
#   Copyright 2013,2014 Lou King
#
###########################################################################################
'''
exportresults - export race results from database
==============================================================================

'''

# standard
import csv

# pypi

# github

# other

# home grown
from .racedb import Runner, Race
from loutilities import timeu
from loutilities.csvwt import wlist
import loutilities.renderrun as render

tdb = timeu.asctime('%Y-%m-%d')

METERSPERMILE = 1609.334

#----------------------------------------------------------------------
def collectresults(club_id, begindate=None, enddate=None): 
#----------------------------------------------------------------------
    '''
    collect race information from database, and save to file
    
    :param club_id: id of club to collect data for
    :param begindate: collect races between begindate and enddate, yyyy-mm-dd
    :param enddate: collect races between begindate and enddate, yyyy-mm-dd
    :rtype: csv file data, string format (e.g., data for make_response(data))
    '''
    # TODO: check format of begindate, enddate
    
    # output fields
    outfields = 'name,dob,gender,race,date,miles,km,time,ag'.split(',')
    
    # create/open results file
    tfile = timeu.asctime('%Y-%m-%d')

    # get ready for output
    outdatalist = wlist()
    OUT = csv.DictWriter(outdatalist,outfields)
    OUT.writeheader()

    # set defaults for begin and end date
    if not begindate:
        begindate = '1970-01-01'
    if not enddate:
        enddate = '2500-12-31'

    # for each member, gather results
    members = Runner.query.filter_by(club_id=club_id,member=True,active=True).all()
    rows = []
    for member in members:
        runnername = member.name
        runnerdob = member.dateofbirth
        runnergender = member.gender

        # loop through each of the runner's results
        # NOTE: results are possibly stored multiple times, for different series -- these will be deduplicated later
        for result in member.results:
            race = Race.query.filter_by(id=result.raceid).first()
            if race.date < begindate or race.date > enddate: continue
            
            resulttime = result.time
            rendertime = render.rendertime(resulttime,0)
            while len(rendertime.split(':')) < 3:
                rendertime = '0:' + rendertime
            resultag = result.agpercent
            racename = race.name
            racedate = race.date
            racemiles = race.distance
            racekm = (race.distance*METERSPERMILE)/1000
            
            # send to output - name,dob,gender,race,date,miles,km,time,ag
            row = {}
            row['name'] = runnername
            row['dob'] = runnerdob
            row['gender'] = runnergender
            row['race'] = racename
            row['date'] = racedate
            row['miles'] = racemiles
            row['km'] = racekm
            row['time'] = rendertime
            row['ag'] = resultag
            
            # deduplicate
            if row not in rows:
                rows.append(row)
    
    OUT.writerows(rows)
    
    # one big string for return data
    outputdata = ''.join(outdatalist)
    return outputdata


