#!/usr/bin/python
###########################################################################################
# renderstandings - render result information within database for standings
#
#	Date		Author		Reason
#	----		------		------
#       03/20/14        Lou King        Adapted from runningclub
#
#   Copyright 2014 Lou King
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
renderstandings - render result information within database for standings
==============================================================================

'''

# standard
import pdb
import argparse
import math

# pypi
import xlwt

# github

# other

# home grown
from config import parameterError,dbConsistencyError
import racedb
from loutilities import renderrun as render

########################################################################
class BaseStandingsHandler():
########################################################################
    '''
    Base StandingsHandler class -- this is an empty class, to be used as a
    template for filehandler classes.  Each method must be replaced or enhanced.
    
    '''
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------

        self.style = {
            'majorhdr': None,
            'hdr': None,
            'divhdr': None,
            'racehdr': None,
            'racename': None,
            'place': None,
            'name': None,
            'name-won-agegroup': None,
            'name-noteligable': None,
            'race': None,
            'race-dropped': None,
            'total': None,
            }

    #----------------------------------------------------------------------
    def prepare(self,gen,series,year):
    #----------------------------------------------------------------------
        '''
        prepare output file for output, including as appropriate
        
        * open
        * print header information
        * collect format for output
        * collect print line dict for output
        
        numraces has number of races
        
        :param gen: gender M or F
        :param series: Series
        :param year: year of races
        :rtype: numraces
        '''

        pass
    
    #----------------------------------------------------------------------
    def setheader(self,gen,header):
    #----------------------------------------------------------------------
        '''
        enable / disable header processing
        
        this is used to determine if header processing is over
        once header processing is over, when rendering, new headers are ignored
        
        :param gen: gender M or F
        :param header: True or False
        '''
        pass
        
    #----------------------------------------------------------------------
    def clearline(self,gen):
    #----------------------------------------------------------------------
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''

        pass
    
    #----------------------------------------------------------------------
    def setplace(self,gen,place,stylename='place'):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def setdivision(self,gen,division,styledivision='division'):
    #----------------------------------------------------------------------
        '''
        put value in 'division' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param division: value for division column
        :param styledivision: name of style for field display
        '''
        
        pass
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name'):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def setrace(self,gen,racenum,result,stylename='race'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def settotal(self,gen,total,stylename='total'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param value: value for total column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def render(self,gen):
    #----------------------------------------------------------------------
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        pass

    #----------------------------------------------------------------------
    def skipline(self,gen):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        pass
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close files associated with this object
        '''
        
        pass
    
########################################################################
class ListStandingsHandler():
########################################################################
    '''
    Like BaseStandingsHandler class, but adds addhandler method.
    
    file handler operations are done for multiple files
    '''
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        self.fhlist = []
    
    #----------------------------------------------------------------------
    def addhandler(self,fh):
    #----------------------------------------------------------------------
        '''
        add derivative of BaseStandingsHandler to list of StandingsHandlers which
        will be processed
        
        :param fh: derivative of BaseStandingsHandler
        '''
        
        self.fhlist.append(fh)
        
    #----------------------------------------------------------------------
    def prepare(self,gen,series,year):
    #----------------------------------------------------------------------
        '''
        prepare output file for output, including as appropriate
        
        * open
        * print header information
        * collect format for output
        * collect print line dict for output
        
        numraces has number of races
        
        :param gen: gender M or F
        :param series: Series
        :param year: year of races
        :rtype: numraces
        '''
        
        numraces = None
        for fh in self.fhlist:
            numraces = fh.prepare(gen,series,year)
            
        # ok to use the last one
        return numraces
    
    #----------------------------------------------------------------------
    def clearline(self,gen):
    #----------------------------------------------------------------------
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''

        for fh in self.fhlist:
            fh.clearline(gen)
    
    #----------------------------------------------------------------------
    def setplace(self,gen,place,stylename='place'):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.setplace(gen,place,stylename)
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name'):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.setname(gen,name,stylename)
    
    #----------------------------------------------------------------------
    def setrace(self,gen,racenum,result,stylename='race'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.setrace(gen,racenum,result,stylename)
    
    #----------------------------------------------------------------------
    def settotal(self,gen,total,stylename='total'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param value: value for total column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.settotal(gen,total,stylename)
    
    #----------------------------------------------------------------------
    def render(self,gen):
    #----------------------------------------------------------------------
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        for fh in self.fhlist:
            fh.render(gen)

    #----------------------------------------------------------------------
    def skipline(self,gen):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        for fh in self.fhlist:
            fh.skipline(gen)
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close files associated with this object
        '''
        
        for fh in self.fhlist:
            fh.close()
    
########################################################################
class TxtStandingsHandler(BaseStandingsHandler):
########################################################################
    '''
    StandingsHandler for .txt files
    
    :param session: database session
    '''
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        BaseStandingsHandler.__init__(self)
        self.TXT = {}
        self.pline = {'F':{},'M':{}}
    
    #----------------------------------------------------------------------
    def prepare(self,gen,series,year):
    #----------------------------------------------------------------------
        '''
        prepare output file for output, including as appropriate
        
        * open
        * print header information
        * collect format for output
        * collect print line dict for output
        
        numraces has number of races
        
        :param gen: gender M or F
        :param series: Series
        :param year: year of races
        :rtype: numraces
        '''
        
        # open output file
        MF = {'F':'Women','M':'Men'}
        rengen = MF[gen]
        self.TXT[gen] = open('{0}-{1}-{2}.txt'.format(year,series.name,rengen),'w')
        
        # render list of all races which will be in the series
        self.TXT[gen].write("FSRC {0}'s {1} {2} standings\n".format(rengen,year,series.name))
        self.TXT[gen].write('\n')                
        numraces = 0
        self.racelist = []
        for race in Race.query.join("series").filter_by(club_id=self.club_id,seriesid=series.id,active=True).order_by(Race.date).all():
            self.racelist.append(race.racenum)
            self.TXT[gen].write('\tRace {0}: {1}: {2}\n'.format(race.racenum,race.name,render.renderdate(race.date)))
            numraces += 1
        self.TXT[gen].write('\n')

        # set up cols format string, and render header
        NAMELEN = 40
        COLWIDTH = 5
        self.linefmt = '{{place:5s}} {{name:{0}s}} '.format(NAMELEN)
        for racenum in self.racelist:
            self.linefmt += '{{race{0}:{1}s}} '.format(racenum,COLWIDTH)
        self.linefmt += '{total:10s}\n'
        
        self.clearline(gen)
        self.setplace(gen,'')
        self.setname(gen,'')
        self.settotal(gen,'Total Pts.')
        
        for racenum in self.racelist:
            self.setrace(gen,racenum,racenum)
            
        self.render(gen)

        return numraces
    
    #----------------------------------------------------------------------
    def clearline(self,gen):
    #----------------------------------------------------------------------
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''
        
        for k in self.pline[gen]:
            self.pline[gen][k] = ''
    
    #----------------------------------------------------------------------
    def setplace(self,gen,place,stylename='place'):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['place'] = str(place)
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name'):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['name'] = str(name)
    
    #----------------------------------------------------------------------
    def setrace(self,gen,racenum,result,stylename='race'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['race{0}'.format(racenum)] = str(result)
    
    #----------------------------------------------------------------------
    def settotal(self,gen,total,stylename='total'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param value: value for total column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['total'] = str(total)
    
    #----------------------------------------------------------------------
    def render(self,gen):
    #----------------------------------------------------------------------
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        self.TXT[gen].write(self.linefmt.format(**self.pline[gen]))
    
    #----------------------------------------------------------------------
    def skipline(self,gen):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        self.TXT[gen].write('\n')
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''
        
        for gen in ['F','M']:
            self.TXT[gen].close()
    
########################################################################
class HtmlStandingsHandler(BaseStandingsHandler):
########################################################################
    '''
    StandingsHandler for .html files
    
    :param racelist: list of race numbers in series
    '''
    #----------------------------------------------------------------------
    def __init__(self,racelist):
    #----------------------------------------------------------------------
        BaseStandingsHandler.__init__(self)
        self.HTML = {}
        self.pline = {'F':{},'M':{}}
        self.racelist = racelist
    
    #----------------------------------------------------------------------
    def prepare(self,gen,series,year):
    #----------------------------------------------------------------------
        '''
        prepare output file for output, including as appropriate
        
        * open
        * print header information
        * collect format for output
        * collect print line dict for output
        
        numraces has number of races
        
        :param gen: gender M or F
        :param series: Series
        :param year: year of races
        :rtype: numraces
        '''
        
        # open output file
        self.HTML[gen] = [] # "file" will be a list of plines
        
        # generate the header
        self.setheader(gen,True)
        self.setplace(gen,'Place')
        self.setname(gen,'Name')
        self.setdivision(gen,'Division')
        self.settotal(gen,'Total Pts.')
        
        for racenum in self.racelist:
            self.setrace(gen,racenum,racenum)
            
        self.render(gen)
        self.setheader(gen,False)
        
        return len(self.racelist)
    
    #----------------------------------------------------------------------
    def clearline(self,gen):
    #----------------------------------------------------------------------
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''
        
        for k in self.pline[gen]:
            if k in ['header','division']: continue  # header indication and division text are persistent
            self.pline[gen][k] = ''
    
    #----------------------------------------------------------------------
    def setheader(self,gen,header):
    #----------------------------------------------------------------------
        '''
        enable / disable header processing
        
        this is used to determine if header processing is over
        once header processing is over, when rendering, new headers are ignored
        
        :param gen: gender M or F
        :param header: True or False
        '''
        set.pline[gen]['header'] = header
        
    #----------------------------------------------------------------------
    def setplace(self,gen,place,stylename='place'):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['place'] = str(place)
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name'):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['name'] = str(name)
    
    #----------------------------------------------------------------------
    def setdivision(self,gen,division,styledivision='division'):
    #----------------------------------------------------------------------
        '''
        put value in 'division' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param division: value for division column
        :param styledivision: name of style for field display
        '''
        
        self.pline[gen]['division'] = str(division)
    
    #----------------------------------------------------------------------
    def setrace(self,gen,racenum,result,stylename='race'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['race{0}'.format(racenum)] = str(result)
    
    #----------------------------------------------------------------------
    def settotal(self,gen,total,stylename='total'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param value: value for total column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['total'] = str(total)
    
    #----------------------------------------------------------------------
    def render(self,gen):
    #----------------------------------------------------------------------
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        self.HTML[gen].append(self.pline[gen])
    
    #----------------------------------------------------------------------
    def skipline(self,gen):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        # this is NOOP for HTML
        pass
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''
        
        #this is NOOP for HTML
        pass
    
    #----------------------------------------------------------------------
    def iter(self,gen):
    #----------------------------------------------------------------------
        '''
        return iterable for gender

        :param gen: gender M or F
        '''
        
        return iter(self.HTML[gen])
    
########################################################################
class XlStandingsHandler(BaseStandingsHandler):
########################################################################
    '''
    StandingsHandler for .xls files
    
    :param session: database session
    '''
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        BaseStandingsHandler.__init__(self)
        self.wb = xlwt.Workbook()
        self.ws = {}
        
        self.rownum = {'F':0,'M':0}
    
        # height is points*20
        self.style = {
            'majorhdr': xlwt.easyxf('font: bold true, height 240'),
            'hdr': xlwt.easyxf('font: bold true, height 200'),
            'divhdr': xlwt.easyxf('font: bold true, height 200'),
            'racehdr': xlwt.easyxf('align: horiz center; font: bold true, height 200'),
            'racename': xlwt.easyxf('font: height 200'),
            'place': xlwt.easyxf('align: horiz center; font: height 200',num_format_str='general'),
            'name': xlwt.easyxf('font: height 200'),
            'name-won-agegroup': xlwt.easyxf('font: height 200, color green',num_format_str='general'),
            'name-noteligable': xlwt.easyxf('font: height 200, color blue',num_format_str='general'),
            'race': xlwt.easyxf('align: horiz center; font: height 200',num_format_str='general'),
            'race-dropped': xlwt.easyxf('align: horiz center; font: height 200, color red',num_format_str='general'),
            'total': xlwt.easyxf('align: horiz center; font: height 200',num_format_str='general'),
            }
        
    #----------------------------------------------------------------------
    def prepare(self,gen,series,year):
    #----------------------------------------------------------------------
        '''
        prepare output file for output, including as appropriate
        
        * open
        * print header information
        * collect format for output
        * collect print line dict for output
        
        numraces has number of races
        
        :param gen: gender M or F
        :param series: Series
        :param year: year of races
        :rtype: numraces
        '''
        
        # open output file
        MF = {'F':'Women','M':'Men'}
        rengen = MF[gen]
        self.fname = '{0}-{1}.xls'.format(year,series.name)
        self.ws[gen] = self.wb.add_sheet(rengen)
        
        # render list of all races which will be in the series
        hdrcol = 0
        self.ws[gen].write(self.rownum[gen],hdrcol,"FSRC {0}'s {1} {2} standings\n".format(rengen,year,series.name),self.style['majorhdr'])
        self.rownum[gen] += 1
        hdrcol = 1
        # only drop races if max defined
        if series.maxraces:
            self.ws[gen].write(self.rownum[gen],hdrcol,'Points in red are dropped.',self.style['hdr'])
            self.rownum[gen] += 1
        # don't mention divisions unless series is using divisions
        if series.divisions:
            self.ws[gen].write(self.rownum[gen],hdrcol,'Runners highlighted in blue won an overall award and are not eligible for age group awards.',self.style['hdr'])
            self.rownum[gen] += 1
            self.ws[gen].write(self.rownum[gen],hdrcol,'Runners highlighted in green won an age group award.',self.style['hdr'])
            self.rownum[gen] += 1
        self.rownum[gen] += 1

        self.racelist = []
        self.races = Race.query.join("series").filter_by(club_id=self.club_id,seriesid=series.id,active=True).order_by(Race.date).all()
        numraces = len(self.races)
        nracerows = int(math.ceil(numraces/2.0))
        thiscol = 1
        for racendx in range(nracerows):
            race = self.races[racendx]
            self.racelist.append(race.racenum)
            thisrow = self.rownum[gen]+racendx
            self.ws[gen].write(thisrow,thiscol,'\tRace {0}: {1}: {2}\n'.format(race.racenum,race.name,render.renderdate(race.date)),self.style['racename'])
        thiscol = 6
        for racendx in range(nracerows,numraces):
            race = self.races[racendx]
            self.racelist.append(race.racenum)
            thisrow = self.rownum[gen]+racendx-nracerows
            self.ws[gen].write(thisrow,thiscol,'\tRace {0}: {1}: {2}\n'.format(race.racenum,race.name,render.renderdate(race.date)),self.style['racename'])

        self.rownum[gen] += nracerows+1
        
        # set up column numbers -- reset for each series
        # NOTE: assumes genders are processed within series loop
        self.colnum = {}
        self.colnum['place'] = 0
        self.colnum['name'] = 1
        thiscol = 2
        for racenum in self.racelist:
            self.colnum['race{0}'.format(racenum)] = thiscol
            thiscol += 1
        self.colnum['total'] = thiscol

        # set up col widths
        self.ws[gen].col(self.colnum['place']).width = 6*256
        self.ws[gen].col(self.colnum['name']).width = 19*256
        self.ws[gen].col(self.colnum['total']).width = 9*256
        for racenum in self.racelist:
            self.ws[gen].col(self.colnum['race{0}'.format(racenum)]).width = 6*256
        
        # render header
        self.clearline(gen)
        self.setplace(gen,'')
        self.setname(gen,'')
        self.settotal(gen,'Total Pts.',stylename='racehdr')
        
        for racenum in self.racelist:
            self.setrace(gen,racenum,racenum,stylename='racehdr')
            
        self.render(gen)

        return numraces
    
    #----------------------------------------------------------------------
    def clearline(self,gen):
    #----------------------------------------------------------------------
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''
        
        pass    # noop for excel - avoid 'cell overwrite' exception
    
    #----------------------------------------------------------------------
    def setplace(self,gen,place,stylename='place'):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: key into self.style
        '''
        
        self.ws[gen].write(self.rownum[gen],self.colnum['place'],place,self.style[stylename])
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name'):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: key into self.style
        '''
        
        self.ws[gen].write(self.rownum[gen],self.colnum['name'],name,self.style[stylename])
    
    #----------------------------------------------------------------------
    def setrace(self,gen,racenum,result,stylename='race'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: key into self.style
        '''
        
        # skip races not in this series
        # this is a bit of a kludge but it keeps StandingsRenderer from knowing which races are within each series
        if 'race{0}'.format(racenum) in self.colnum: 
            self.ws[gen].write(self.rownum[gen],self.colnum['race{0}'.format(racenum)],result,self.style[stylename])
    
    #----------------------------------------------------------------------
    def settotal(self,gen,total,stylename='total'):
    #----------------------------------------------------------------------
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param total: value for total column
        :param stylename: key into self.style
        '''
        
        self.ws[gen].write(self.rownum[gen],self.colnum['total'],total,self.style[stylename])
    
    #----------------------------------------------------------------------
    def render(self,gen):
    #----------------------------------------------------------------------
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        self.rownum[gen] += 1
    
    #----------------------------------------------------------------------
    def skipline(self,gen):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        self.rownum[gen] += 1
    
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''
        
        self.wb.save(self.fname)
        
        # kludge to force a new workbook for the next series
        del self.wb
        self.wb = xlwt.Workbook()
        self.rownum = {'F':0,'M':0}
    
########################################################################
class StandingsRenderer():
########################################################################
    '''
    StandingsRenderer collects standings and provides rendering methods, for a single series
    
    :param club_id: club.id
    :param year: year for standings
    :param series: Series
    :param races: list of Races
    :param racenums: list of race numbers for standings 
    '''
    #----------------------------------------------------------------------
    def __init__(self,club_id,year,series,races,racenums):
    #----------------------------------------------------------------------
        self.club_id = club_id
        self.series = series
        self.orderby = series.orderby
        self.hightolow = series.hightolow
        self.bydiv = series.divisions
        self.avgtie = series.averagetie
        self.multiplier = series.multiplier
        self.maxgenpoints = series.maxgenpoints
        self.maxdivpoints = series.maxdivpoints
        self.maxraces = series.maxraces
        self.maxbynumrunners = series.maxbynumrunners
        self.year = year
        self.races = races
        self.racenums = racenums
        
    #----------------------------------------------------------------------
    def collectstandings(self,racesprocessed,gen,raceid,byrunner,divrunner): 
    #----------------------------------------------------------------------
        '''
        collect standings for this race / series
        
        in byrunner[name][type], points{race} entries are set to '' for race not run, to 0 for race run but no points given
        
        :param racesprocessed: number of races processed so far
        :param gen: gender, M or F
        :param raceid: race.id to collect standings for
        :param byrunner: dict updated as runner standings are collected {name:{'bygender':[points1,points2,...],'bydivision':[points1,points2,...]}}
        :param divrunner: dict updated with runner names by division {div:[runner1,runner2,...],...}
        :rtype: number of standings processed for this race / series
        '''
        numresults = 0
    
        # get all the results currently in the database
        # byrunner = {name:{'bygender':[points,points,...],'bydivision':[points,points,...]}, ...}
        allresults = RaceResult.query.order_by(self.orderby).filter_by(club_id=self.club_id,raceid=raceid,seriesid=self.series.id,gender=gen).all()
        if self.hightolow: allresults.sort(reverse=True)
        
        for resultndx in range(len(allresults)):
            numresults += 1
            result = allresults[resultndx]
            
            # add runner name 
            name = result.runner.name
            if name not in byrunner:
                byrunner[name] = {}
                byrunner[name]['bygender'] = []
                if self.bydiv:
                    if name not in divrunner[(result.divisionlow,result.divisionhigh)]:
                        divrunner[(result.divisionlow,result.divisionhigh)].append(name)
                    byrunner[name]['bydivision'] = []
            
            # for this runner, catch 'bygender' and 'bydivision' up to current race position
            while len(byrunner[name]['bygender']) < racesprocessed:
                byrunner[name]['bygender'].append('')
                if self.bydiv:
                    byrunner[name]['bydivision'].append('')
                    
            # accumulate points for this result
            # if result is ordered by time, genderplace and divisionplace may be used
            if self.orderby == RaceResult.time:
                # if result points depend on the number of runners, update maxgenpoints
                if self.maxbynumrunners:
                    self.maxgenpoints = len(allresults)
                
                # if starting at the top (i.e., maxgenpoints is non-zero, accumulate points accordingly
                if self.maxgenpoints:
                    genpoints = self.multiplier*(self.maxgenpoints+1-result.genderplace)
                
                # otherwise, accumulate from the bottom
                else:
                    genpoints = self.multiplier*result.genderplace
                
                byrunner[name]['bygender'].append(max(genpoints,0))
                if self.bydiv:
                    divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                    byrunner[name]['bydivision'].append(max(divpoints,0))
            
            # if result was ordered by agpercent, agpercent is used -- assume no divisions
            elif self.orderby == RaceResult.agpercent:
                # some combinations don't make sense, and have been commented out
                # TODO: verify combinations in updaterace.py
                
                ## if result points depend on the number of runners, update maxgenpoints
                #if byrunner:
                #    maxgenpoints = len(allresults)
                #
                ## if starting at the top (i.e., maxgenpoints is non-zero, accumulate points accordingly
                #if maxgenpoints:
                #    genpoints = self.multiplier*(self.maxgenpoints+1-result.genderplace)
                #
                ## otherwise, accumulate from the bottom (this should never happen)
                #else:
                genpoints = int(round(self.multiplier*result.agpercent))
                
                byrunner[name]['bygender'].append(max(genpoints,0))
                #if self.bydiv:
                #    divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                #    byrunner[name]['bydivision'].append(max(divpoints,0))
            
            # if result is ordered by agtime, agtimeplace may be used -- assume no divisions
            elif self.orderby == RaceResult.agtime:
                # if result points depend on the number of runners, update maxgenpoints
                if byrunner:
                    self.maxgenpoints = len(allresults)
                
                # if starting at the top (i.e., maxgenpoints is non-zero, accumulate points accordingly
                if self.maxgenpoints:
                    genpoints = self.multiplier*(self.maxgenpoints+1-result.agtimeplace)
                
                # otherwise, accumulate from the bottom
                else:
                    genpoints = self.multiplier*result.agtimeplace
                
                byrunner[name]['bygender'].append(max(genpoints,0))
                #if self.bydiv:
                #    divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                #    byrunner[name]['bydivision'].append(max(divpoints,0))
                #
            else:
                raise parameterError, 'results must be ordered by time, agtime or agpercent'
            
        return numresults            
    
    #----------------------------------------------------------------------
    def renderseries(self,fh): 
    #----------------------------------------------------------------------
        '''
        render standings for a single series
        
        see BaseStandingsHandler for methods of fh
        
        :param fh: StandingsHandler object-like
        '''

        # collect divisions, if necessary
        if self.bydiv:
            divisions = []
            for div in Divisions.query.filter_by(club_id=self.club_id,seriesid=self.series.id,active=True).order_by(Divisions.divisionlow).all():
                divisions.append((div.divisionlow,div.divisionhigh))
            if len(divisions) == 0:
                raise dbConsistencyError, 'series {0} indicates divisions to be calculated, but no divisions found'.format(self.series.name)

        # process each gender
        for gen in ['F','M']:
            # open file, prepare header, etc
            fh.prepare(gen,self.series,self.year)
                    
            # collect data for each race, within byrunner dict
            # also track names of runners within each division
            byrunner = {}
            divrunner = None
            if self.bydiv:
                divrunner = {}
                for div in divisions:
                    divrunner[div] = []
                
            # pick up active races as supplied by caller
            racesprocessed = 0
            for race in self.races:
                # skip races not included in this series (note race.series points at raceseries table)
                #if self.series.id not in [s.seriesid for s in race.series]: continue
                self.collectstandings(racesprocessed,gen,race.id,byrunner,divrunner)
                racesprocessed += 1
                
            # render standings
            # first by division
            if self.bydiv:
                fh.setheader(gen,True)
                fh.clearline(gen)
                fh.setplace(gen,'Place','racehdr')
                fh.setname(gen,'Age Group','divhdr')
                fh.render(gen)
                fh.setheader(gen,False)
                
                for div in divisions:
                    fh.setheader(gen,True)
                    fh.clearline(gen)
                    divlow,divhigh = div
                    if divlow == 0:     divtext = '{0} & Under'.format(divhigh)
                    elif divhigh == 99: divtext = '{0} & Over'.format(divlow)
                    else:               divtext = '{0} to {1}'.format(divlow,divhigh)
                    fh.setname(gen,divtext,'divhdr')
                    fh.setdivision(gen,divtext)
                    fh.render(gen)
                    fh.setheader(gen,False)
                    
                    # calculate runner total points
                    bypoints = []
                    for name in divrunner[div]:
                        # convert each race result to int if possible
                        byrunner[name]['bydivision'] = [int(r) if type(r)==float and r==int(r) else r for r in byrunner[name]['bydivision']]
                        racetotals = byrunner[name]['bydivision'][:]    # make a copy
                        racetotals.sort(reverse=True)
                        # total numbers only, and convert to int if possible
                        racetotals = [r for r in racetotals if type(r) in [int,float]]
                        racesused = racetotals[:min(self.maxraces,len(racetotals))]
                        byrunner[name]['racesused'] = racesused[:]  # NOTE: this field will be reinitialized for overall / gender standings
                        totpoints = sum(racesused)
                        # render as integer if result same as integer
                        totpoints = int(totpoints) if totpoints == int(totpoints) else totpoints
                        bypoints.append((totpoints,name))
                    
                    # sort runners within division by total points and render
                    bypoints.sort(reverse=True)
                    thisplace = 1
                    lastpoints = -999
                    for runner in bypoints:
                        totpoints,name = runner
                        fh.clearline(gen)
                        
                        # render place if it's different than last runner's place, else there was a tie
                        renderplace = thisplace
                        if totpoints == lastpoints:
                            renderplace = ''
                        fh.setplace(gen,renderplace)
                        thisplace += 1
                        
                        # render name and total points, remember last total points
                        fh.setname(gen,name)
                        fh.settotal(gen,totpoints)
                        lastpoints = totpoints
                        
                        # render race results
                        iracenums = iter(self.racenums)
                        for pts in byrunner[name]['bydivision']:
                            racenum = next(iracenums)
                            if pts in byrunner[name]['racesused']:
                                fh.setrace(gen,racenum,pts)
                                byrunner[name]['racesused'].remove(pts)
                            else:
                                fh.setrace(gen,racenum,pts,stylename='race-dropped')
                        fh.render(gen)
                        
                    # skip line between divisions
                    fh.skipline(gen)
                        
            # then overall
            fh.setheader(gen,True)
            fh.clearline(gen)
            fh.setplace(gen,'Place','racehdr')
            fh.setname(gen,'Overall','divhdr')
            fh.setdivision(gen,'Overall')
            fh.render(gen)
            fh.setheader(gen,False)
            
            # calculate runner total points
            bypoints = []
            for name in byrunner:
                # convert each race result to int if possible
                byrunner[name]['bygender'] = [int(r) if type(r)==float and r==int(r) else r for r in byrunner[name]['bygender']]
                racetotals = byrunner[name]['bygender'][:]    # make a copy
                racetotals.sort(reverse=True)
                # total numbers only, and convert to int if possible
                racetotals = [r for r in racetotals if type(r) in [int,float]]
                racesused = racetotals[:min(self.maxraces,len(racetotals))]
                byrunner[name]['racesused'] = racesused[:]  # NOTE: this field will be reinitialized for overall / gender standings
                totpoints = sum(racesused)
                totpoints = int(totpoints) if totpoints == int(totpoints) else totpoints
                bypoints.append((totpoints,name))
            
            # sort runners by total points and render
            bypoints.sort(reverse=True)
            thisplace = 1
            lastpoints = -999
            for runner in bypoints:
                totpoints,name = runner
                fh.clearline(gen)
                        
                # render place if it's different than last runner's place, else there was a tie
                renderplace = thisplace
                if totpoints == lastpoints:
                    renderplace = ''
                fh.setplace(gen,renderplace)
                thisplace += 1
                
                # render name and total points, remember last total points
                fh.setname(gen,name)
                fh.settotal(gen,totpoints)
                lastpoints = totpoints
                
                # render race results
                iracenums = iter(self.racenums)
                for pts in byrunner[name]['bygender']:
                    racenum = next(iracenums)
                    if pts in byrunner[name]['racesused']:
                        fh.setrace(gen,racenum,pts)
                        byrunner[name]['racesused'].remove(pts)
                    else:
                        fh.setrace(gen,racenum,pts,stylename='race-dropped')
                fh.render(gen)

            fh.skipline(gen)
                        
        # done with rendering
        fh.close()
            
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    '''
    render result information
    '''
    parser = argparse.ArgumentParser(version='{0} {1}'.format('runningclub',version.__version__))
    parser.add_argument('-s','--series',help='series to render',default=None)
    parser.add_argument('-r','--racedb',help='filename of race database (default is as configured during rcuserconfig)',default=None)
    args = parser.parse_args()
    
    racedb.setracedb(args.racedb)
    session = racedb.Session()
    
    # get filtered series, which have any results
    sfilter = {'active':True}
    theseseries = session.query(Series).filter_by(club_id=self.club_id,**sfilter).join("results").all()
    
    fh = ListStandingsHandler()
    fh.addhandler(TxtStandingsHandler(session))
    fh.addhandler(XlStandingsHandler(session))
    
    for series in theseseries:
        # render the standings, according to series specifications
        rr = StandingsRenderer(session,series)
        rr.renderseries(fh)

    session.close()
        
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()
