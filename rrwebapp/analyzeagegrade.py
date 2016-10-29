#!/usr/bin/python
################################################################################
# analyzeagegrade - analyze age grade race data
#
#   Author: L King
#
#   REVISION HISTORY:
#       08/08/12    L King      Create
#       10/27/16    L King      Copied from `running` package
#
################################################################################
'''
analyzeagegrade - analyze age grade race data
=====================================================================================


'''

# standard libraries
import csv
import math
import time

# home grown libraries
from . import app
from loutilities import timeu
from loutilities import agegrade

class unexpectedEOF(Exception): pass
class invalidParameter(Exception): pass

METERSPERMILE = 1609.344

# pull in age grade object
ag = agegrade.AgeGrade()
    

#-------------------------------------------------------------------------------
def distmap(dist):
#-------------------------------------------------------------------------------
    """
    map distance to display metric
    
    :param dist: distance to map
    :rtype: float display metric for distance
    """
    return dist/100

#-------------------------------------------------------------------------------
def linear_regression(y,x):
#-------------------------------------------------------------------------------

    n = len(y)
    sum_x = 0
    sum_y = 0
    sum_xy = 0
    sum_xx = 0
    sum_yy = 0

    for i in range(len(y)):

        sum_x += x[i]
        sum_y += y[i]
        sum_xy += (x[i]*y[i])
        sum_xx += (x[i]*x[i])
        sum_yy += (y[i]*y[i])
    

    lr = TrendLine()
    lr.slope = (n * sum_xy - sum_x * sum_y) / (n*sum_xx - sum_x * sum_x)
    lr.intercept = (sum_y - lr.slope * sum_x) / n
    lr.r2 = math.pow((n*sum_xy - sum_x*sum_y)/math.sqrt((n*sum_xx-sum_x*sum_x)*(n*sum_yy-sum_y*sum_y)), 2)

    return lr


########################################################################
class AgeGradeStat():
########################################################################
    '''
    statistic for age grade analysis, for a single runner
    
    :param date: date in datetime format
    :param dist: distance in meters
    :param time: time in seconds
    :param ag: age grade percentage (float, 0-100)
    :param race: race name
    :param loc: location of race
    :param source: source of data
    :param fuzzyage: 'Y' if age check was done based on age group rather than exact age, None otherwise
    :param priority: priority for deduplication, lowest value is kept (lower number = higher priority)
    '''
    attrs = 'race,date,loc,dist,time,ag,source,fuzzyage,priority'.split(',')
    
    #-------------------------------------------------------------------------------
    def __init__(self,date=None,dist=None,time=None,ag=None,race=None,loc=None,source=None,fuzzyage=None,priority=1):
    #-------------------------------------------------------------------------------
        self.date = date
        self.dist = dist
        self.time = time
        self.ag = ag
        self.race = race
        self.loc = loc
        self.source = source
        self.fuzzyage = fuzzyage
        self.priority = priority
        
    #-------------------------------------------------------------------------------
    def __repr__(self):
    #-------------------------------------------------------------------------------
        retval = '{}({}, {} meters, {} secs'.format(self.__class__,tdisp.dt2asc(self.date),self.dist,self.time)
        if self.ag:
            retval += ', age grade = {}'.format(self.ag)
        if self.race:
            retval += ', {}'.format(self.race)
        retval += ')'
        return retval

########################################################################
class TrendLine():
########################################################################
    '''
    regression line parameters (ref http://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html)
    
    :param slope: slope of the regression line
    :param intercept: intercept fo the regression line
    :param rvalue: correlation coefficient
    :param pvalue: two-sided p-value for hypothesis test whose null hypothesis is that the slope is zero
    :param stderr: standard error of the estimate
    '''
    
    #-------------------------------------------------------------------------------
    def __init__(self, slope=None, intercept=None, r2=None, pvalue=None, stderr=None):
    #-------------------------------------------------------------------------------
        self.slope = slope
        self.intercept = intercept
        self.r2 = r2
        self.pvalue = pvalue
        self.stderr = stderr
        
    #-------------------------------------------------------------------------------
    def __repr__(self):
    #-------------------------------------------------------------------------------
        retval = 'analyzeagegrade.TrendLine(slope {:0.2f}, intercept {:0.2f}, r2 {:0.2f}, pvalue {:0.2f}, stderr {:0.2f})'.format(
            self.slope, self.intercept, self.r2, self.pvalue, self.stderr)
        return retval
    
########################################################################
class AnalyzeAgeGrade():
########################################################################
    '''
    age grade analysis
    '''
    
    #-------------------------------------------------------------------------------
    def __init__(self):
    #-------------------------------------------------------------------------------
        self.exectime = time.time()
        self.gender = None
        self.dob = None
        self.xlim = {'left':None,'right':None}
        self.ylim = None    # TODO: make 'top','bottom' dict
               
        self.clear()
        
    #-------------------------------------------------------------------------------
    def clear(self):
    #-------------------------------------------------------------------------------
        '''
        clear statistics
        '''
        # stats = list(AgeGradeStat(),... ) 
        self.stats = []
        
        # self.dists = set of distances included in stats, rounded
        self.dists = set([])

    #-------------------------------------------------------------------------------
    def add_stat(self, date, dist, time, **kwargs):
    #-------------------------------------------------------------------------------
        '''
        add an individual statistic
        
        :param date: date in datetime format
        :param dist: distance in meters
        :param time: time in seconds
        :param kwargs: keyword arguments, must match AgeGradeState attrs
        '''
        
        self.stats.append(AgeGradeStat(date,dist,time,**kwargs))
        self.dists.add(round(dist))
        
    #-------------------------------------------------------------------------------
    def del_stat(self, stat):
    #-------------------------------------------------------------------------------
        '''
        delete the indicated statistic
        
        :param stat: :class:`AgeGradeStat` to delete
        '''
        try:
            self.stats.remove(stat)
        except ValueError:
            app.logger.warning('del_stat: failed to delete {}'.format(stat))
        
    #-------------------------------------------------------------------------------
    def get_stats(self):
    #-------------------------------------------------------------------------------
        '''
        return stats collected
        
        :rtype: list of :class:`AgeGradeStat` entries
        '''
        return self.stats
    
    #-------------------------------------------------------------------------------
    def deduplicate(self):
    #-------------------------------------------------------------------------------
        '''
        remove statistics which are duplicates, assuming stats on same day
        for same distance are duplicated
        '''
        
        # be careful of degenerate case
        if len(self.stats) == 0:
            return

        # collect unique statistics, within epsilon distance
        EPS = .1   # epsilon -- if event distance is within this tolerance, it is considered the same

        # sort self.stats into stats, by date,distance
        decstats = [((s.date,s.dist),s) for s in self.stats]
        decstats.sort()
        stats = [ds[1] for ds in decstats]
        
        # deduplicate stats, paying attention to priority when races determined to be the same
        deduped = []
        while len(stats) > 0:
            # get the first entry, that's the first "samerace"
            thisstat = stats.pop(0)
            sameraces = [(thisstat.priority,thisstat)]
            
            # pull races off stats when the race date and distance are the same
            # distance has to be within epsilon to be deduced to be the same
            while   len(stats) > 0 \
                    and thisstat.date == stats[0].date \
                    and abs((thisstat.dist - stats[0].dist) / thisstat.dist) <= EPS:
                stat = stats.pop(0)
                sameraces.append((stat.priority,stat))
            
            # sort same races by priority, and add highes priority (lowest valued) to deduped list
            sameraces.sort()
            prio,stat = sameraces[0]
            deduped.append(stat)
        
        dupremoved = len(self.stats) - len(deduped)
        if dupremoved > 0:
            app.logger.debug('{} duplicate points removed, runner {}'.format(dupremoved,self.who))

        # replace self.stats with deduplicated version
        self.stats = deduped

    #-------------------------------------------------------------------------------
    def set_runner(self, who, gender, dob, runnerid):
    #-------------------------------------------------------------------------------
        '''
        set runner parameters required for age grade analysis
        
        :param who: name of runner
        :param gender: M or F
        :param dob: datetime date of birth
        :param runnerid: runner.id
        '''
        self.who = who
        self.gender = gender
        self.dob = dob
        self.runnerid = runnerid
        
    #-------------------------------------------------------------------------------
    def get_runner(self):
    #-------------------------------------------------------------------------------
        '''
        return runner data
        
        :rtype: name,gender,dob,runnerid
        '''
        return self.who, self.gender, self.dob, self.runnerid
    
    #-------------------------------------------------------------------------------
    def get_source(self):
    #-------------------------------------------------------------------------------
        '''
        return result source
        
        :rtype: source
        '''
        return self.source
    
    #-------------------------------------------------------------------------------
    def getdatafromfile(self, agfile):
    #-------------------------------------------------------------------------------
        '''
        plot the data in dists
        
        :param agfile: name of csv file containing age grade data
        :rtype: 
        '''
        
        _IN = open(agfile,'r')
        IN = csv.DictReader(_IN,dialect='excel')
    
        # collect data
        linenum = 0
        while True:
            try:
                inrow = IN.next()
                linenum += 1
            except StopIteration:
                break
                
            s_date = inrow['Date']
            date = tdisp.asc2dt(s_date)
            
            dist = float(inrow['Distance (miles)']) * METERSPERMILE
            
            # calculate number of seconds in string field [[hh:]mm:]ss[.000]
            s_rtime = inrow['Net']
            timefields = iter(s_rtime.split(':'))
            rtime = 0.0
            thisunit = float(timefields.next())
            while True:
                rtime += thisunit
                try:
                    thisunit = float(timefields.next())
                except StopIteration:
                    break
                rtime *= 60 # doesn't happen if last field was processed before
            
    
            # age grade calculation was moved to crunch() to crunch age grade and pace
            # this just saves what was in the file in case I ever want to compare
            s_ag = inrow['AG']
            if s_ag:    
                if s_ag[-1] == '%':
                    ag = float(s_ag[:-1])
                else:
                    ag = float(s_ag)
            # we don't care about this entry if AG wasn't captured
            else:
                ag = None
                
            self.dists.add(round(dist))      # keep track of distances to nearest meter
            self.stats.append(AgeGradeStat(date,dist,rtime))
            #print(s_date,date,dist,ag)
            
        _IN.close()
    
    #-------------------------------------------------------------------------------
    def getdatafromra(self):
    #-------------------------------------------------------------------------------
        '''
        get the user's data from RunningAHEAD
        
        :rtype: dists,stats,dob,gender where dists =  set of distances included in stats, stats = {'date':[datetime of race,...], 'dist':[distance(meters),...], 'time':[racetime(seconds),...]}, dob = date of birth (datetime), gender = 'M'|'F'
        '''
        # set up RunningAhead object and get users we're allowed to look at
        ra = runningahead.RunningAhead()    
        users = ra.listusers()
        day = timeu.asctime('%Y-%m-%d') # date format in RunningAhead workout object
        
        # find correct user, grab their workouts
        workouts = None
        for user in users:
            thisuser = ra.getuser(user['token'])
            if 'givenName' not in thisuser: continue    # we need to know the name
            givenName = thisuser['givenName'] if 'givenName' in thisuser else ''
            familyName = thisuser['familyName'] if 'familyName' in thisuser else ''
            thisusername = ' '.join([givenName,familyName])
            if thisusername != self.who: continue            # not this user, keep looking
            
            # grab user's date of birth and gender, if not already supplied
            if not self.dob:
                self.dob = day.asc2dt(thisuser['birthDate'])
            if not self.gender:
                self.gender = 'M' if thisuser['gender']=='male' else 'F'
            
            # if we're here, found the right user, now let's look at the workouts
            firstdate = day.asc2dt('1980-01-01')
            lastdate = day.asc2dt('2199-12-31')
            workouts = ra.listworkouts(user['token'],begindate=firstdate,enddate=lastdate,getfields=FIELD['workout'].keys())
    
            # we've found the right user and collected their data, so we're done
            break
            
        # save race workouts, if any found
        if workouts:
            tempstats = []
            for wo in workouts:
                if wo['workoutName'].lower() != 'race': continue
                thisdate = day.asc2dt(wo['date'])
                thisdist = runningahead.dist2meters(wo['details']['distance'])
                thistime = wo['details']['duration']
                
                tempstats.append((thisdate,AgeGradeStat(thisdate,thisdist,thistime)))
                
        # these may come sorted already, but just in case
        #tempstats.sort()
        
        # put the stats in the right format
        for thisdate,thisstat in tempstats:
            self.stats.append(thisstat)
            self.dists.add(round(thisstat.dist))      # keep track of distances to nearest meter
    
    #-------------------------------------------------------------------------------
    def crunch(self):
    #-------------------------------------------------------------------------------
        '''
        crunch the race data to put the age grade data into the stats
        
        '''
        ### DEBUG>
        debug = False
        if debug:
            tim = timeu.asctime('%Y-%m-%d-%H%M')
            _DEB = open('analyzeagegrade-debug-{}-crunch-{}.csv'.format(tim.epoch2asc(self.exectime,self.who)),'wb')
            fields = ['date','dist','time','ag']
            DEB = csv.DictWriter(_DEB,fields)
            DEB.writeheader()
        ### <DEBUG
            
        # calculate age grade for each sample    
        for i in range(len(self.stats)):
            racedate = self.stats[i].date
            agegradeage = racedate.year - self.dob.year - int((racedate.month, racedate.day) < (self.dob.month, self.dob.day))
            distmiles = self.stats[i].dist/METERSPERMILE
            agpercentage,agtime,agfactor = ag.agegrade(agegradeage,self.gender,distmiles,self.stats[i].time)
            self.stats[i].ag = agpercentage
            
            ### DEBUG>
            if debug:
                thisstat = {}
                for field in fields:
                    thisstat[field] = getattr(self.stats[i],field)
                DEB.writerow(thisstat)
            ### <DEBUG
            
        ### DEBUG>
        if debug:
            _DEB.close()
        ### <DEBUG
    
    #-------------------------------------------------------------------------------
    def get_trendline(self, thesestats=None):
    #-------------------------------------------------------------------------------
        '''
        determine trend line
        
        :param label: label for trendline
        :param thesestats: list of :class:`AgeGradeStat`, or None if all stats to be used
        :param color: color per matplotlib for trendline, or None to automate
        :rtype: :class:`TrendLine` containing parameters of trendline
        '''
        
        if not thesestats:
            thesestats = self.stats
        
        x = [timeu.dt2epoch(s.date) for s in thesestats]
        y = [s.ag for s in thesestats]
        
        lr = linear_regression(y, x)
        yline = [lr.slope*thisx+lr.intercept for thisx in x]
        
        return lr
