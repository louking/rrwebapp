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
ag = agegrade.AgeGrade(agegradewb='config/wavacalc15.xls')
    

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
def linear_regression(Y,X):
#-------------------------------------------------------------------------------

    n = len(Y)
    sum_x = 0
    sum_y = 0
    sum_xy = 0
    sum_xx = 0
    sum_yy = 0

    for i in range(len(Y)):

        sum_x += X[i]
        sum_y += Y[i]
        sum_xy += (X[i]*Y[i])
        sum_xx += (X[i]*X[i])
        sum_yy += (Y[i]*Y[i])
    

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
    def __init__(self, slope=None, intercept=None, r2=None, pvalue=None, stderr=None, improvement=None):
    #-------------------------------------------------------------------------------
        self.slope = slope
        self.intercept = intercept
        self.r2 = r2
        self.pvalue = pvalue
        self.stderr = stderr
        self.improvement = improvement
        
    #-------------------------------------------------------------------------------
    def __repr__(self):
    #-------------------------------------------------------------------------------
        retval = 'analyzeagegrade.TrendLine(slope {:0.2f}, intercept {:0.2f}, improvement {:0.2f}, r2 {:0.2f}, pvalue {:0.2f}, stderr {:0.2f})'.format(
            self.slope, self.intercept, self.improvement, self.r2, self.pvalue, self.stderr)
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
        :rtype: the newly created stat
        '''
        
        thisstat = AgeGradeStat(date,dist,time,**kwargs)
        self.stats.append(thisstat)
        self.dists.add(round(dist))
        return thisstat
        
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
        DIST_EPS = 2.0   # if event distance is within this tolerance (%age), assumed the same
        TIME_EPS = 2.0   # if time is within this tolerance (seconds), assumed to be the same

        # sort self.stats into stats, by date,distance
        decstats = sorted([((s.date,s.dist),s) for s in self.stats])
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
                    and abs((thisstat.dist - stats[0].dist) / thisstat.dist) <= DIST_EPS/100.0 \
                    and abs(thisstat.time - stats[0].time) <= TIME_EPS:
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
    def set_runner(self, who, fname, lname, gender, dob, runnerid):
    #-------------------------------------------------------------------------------
        '''
        set runner parameters required for age grade analysis
        
        :param who: name of runner
        :param fname: first name of runner
        :param lname: last name of runner
        :param gender: M or F
        :param dob: datetime date of birth
        :param runnerid: runner.id
        '''
        self.who = who
        self.fname = fname
        self.lname = lname
        self.gender = gender
        self.dob = dob
        self.runnerid = runnerid
        
    #-------------------------------------------------------------------------------
    def get_runner(self):
    #-------------------------------------------------------------------------------
        '''
        return runner data
        
        :rtype: name,fname,lname,gender,dob,runnerid
        '''
        return self.who, self.fname, self.lname, self.gender, self.dob, self.runnerid
    
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
                inrow = next(IN)
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
            thisunit = float(next(timefields))
            while True:
                rtime += thisunit
                try:
                    thisunit = float(next(timefields))
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
            workouts = ra.listworkouts(user['token'],begindate=firstdate,enddate=lastdate,getfields=list(FIELD['workout'].keys()))
    
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
            _DEB = open('analyzeagegrade-debug-{}-crunch-{}.csv'.format(tim.epoch2asc(self.exectime,self.who)), 'w', newline='')
            fields = ['date','dist','time','ag']
            DEB = csv.DictWriter(_DEB, fields)
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
        
        X = [timeu.dt2epoch(s.date) for s in thesestats]
        Y = [s.ag for s in thesestats]
        
        try:
            lr = linear_regression(Y, X)
        except ZeroDivisionError:
            app.logger.debug(('ZeroDivisionError\n   len(thesestats)={}\n   X={}\n   Y={}\n' +
                              '   thesestats[0].date={}').format(len(thesestats), X, Y, thesestats[0].date))
            raise

        yline = [lr.slope*thisx+lr.intercept for thisx in X]

        x1 = min(X)
        y1 = lr.slope*x1+lr.intercept
        x2 = max(X)
        y2 = lr.slope*x2+lr.intercept
        years = (x2-x1)*1.0/(60*60*24*365)      # convert seconds to years (1.0 make sure we're floating point)
        if years > 0:
            lr.improvement = (y2-y1) / years    # 100 is 100% improvement per year
        else:
            lr.improvement = -9999              # how did this happen?
        
        return lr
