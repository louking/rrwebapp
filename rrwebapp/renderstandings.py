#!/usr/bin/python
###########################################################################################
# renderstandings - render result information within database for standings
#
#	Date		Author		Reason
#	----		------		------
#       03/20/14        Lou King        Adapted from runningclub
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################
'''
renderstandings - render result information within database for standings
==============================================================================

'''

# standard
import math
import copy
import urllib.request, urllib.parse, urllib.error
from datetime import datetime
from functools import cmp_to_key

# pypi
import xlwt
import flask
from flask import current_app
from dominate.tags import div, a
from dominate.util import text
from loutilities import renderrun as render
from loutilities import timeu

from rrwebapp.resultssummarize import mean

# home grown
from .model import Divisions, Race, RaceResult, Runner
from .model import SERIES_OPTION_PROPORTIONAL_SCORING, SERIES_OPTION_REQUIRES_CLUB, SERIES_OPTION_DISPLAY_CLUB
from .model import SERIES_TIE_OPTIONS, SERIES_TIE_OPTION_SEPARATOR, SERIES_TIE_OPTION_COMPARE_AVG, \
                   SERIES_TIE_OPTION_DIV_COMPARE_OVERALL, SERIES_TIE_OPTION_HEAD_TO_HEAD_POINTS
from .resultsutils import get_earliestrace, clubaffiliationelement

tYmd = timeu.asctime('%Y-%m-%d')

class parameterError(Exception): pass
class dbConsistencyError(Exception): pass

class Points(object):
    '''
    object to hold points information (see calcpoints())
    '''
    def __init__(self, **kwargs):
        for f in kwargs:
            setattr(self, f, kwargs[f])

#----------------------------------------------------------------------
def addstyle(header, contents, style, title=None):
#----------------------------------------------------------------------
    '''
    add style class to table element

    :param header: true if this is to be a header element
    :param contents: text or dominate tag for final element, can be list of dominate tags
    :param style: name for style class
    :param title: (optional) title for element
    :rtype: html string
    '''
    if not isinstance(contents, list):
        el = div(contents, _class=f'_rrwebapp-class-standings-data-{style}')
        if title:
            el['title'] = title
    
    # handle list of dominate tags
    else:
        el = div(_class=f'_rrwebapp-class-standings-data-{style}')
        if title:
            el['title'] = title
        for item in contents:
            el.add(item)
            separator = text(', ')
            el.add(separator)
        # remove last separator
        el.remove(separator)

    return el.render()
    
#----------------------------------------------------------------------
def makelink(href,text):
#----------------------------------------------------------------------
    '''
    add style class to table element

    :param header: true if this is to be a header element
    :param text: text for final element
    :param style: name for style class
    :rtype: etree.Element
    '''
    el = a(text, href=href)
    return el
    
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
            'age': None,
            'clubs': None,
            'nraces': None,
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
    def setplace(self, gen, place, stylename='place', title=None):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        :param title: (optional) title for popup display        
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
        :param title: (optional) title for popup display
        '''
        
        pass
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name',runnerid=None):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        :param runnerid: runner's id from runner table
        '''

        pass
    
    #----------------------------------------------------------------------
    def setage(self,gen,age,stylename='age'):
    #----------------------------------------------------------------------
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param age: value for age column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def setclubs(self,gen,clubs,stylename='clubs'):
    #----------------------------------------------------------------------
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param clubs: value for clubs column
        :param stylename: name of style for field display
        '''

        pass
    
    #----------------------------------------------------------------------
    def setnraces(self,gen,nraces,stylename='nraces'):
    #----------------------------------------------------------------------
        '''
        put value in 'nraces' column for output

        :param gen: gender M or F
        :param nraces: value for nraces column
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
    def setplace(self,gen,place,stylename='place',title=None):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        :param title: (optional) title for popup display
        '''

        for fh in self.fhlist:
            fh.setplace(gen, place, stylename, title=title)
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name',runnerid=None):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        :param runnerid: runner's id from runner table
        '''

        for fh in self.fhlist:
            fh.setname(gen,name,stylename)
    
    #----------------------------------------------------------------------
    def setage(self,gen,age,stylename='age'):
    #----------------------------------------------------------------------
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param age: value for age column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.setage(gen,age,stylename)
    
    #----------------------------------------------------------------------
    def setclubs(self,gen,clubs,stylename='clubs'):
    #----------------------------------------------------------------------
        '''
        put value in 'clubs' column for output

        :param gen: gender M or F
        :param clubs: value for clubs column
        :param stylename: name of style for field display
        '''

        for fh in self.fhlist:
            fh.setclubs(gen, clubs, stylename)
    
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
        self.linefmt = '{{place:5s}} {{name:{0}s}} {{age:5s}} '.format(NAMELEN)
        for racenum in self.racelist:
            self.linefmt += '{{race{0}:{1}s}} '.format(racenum,COLWIDTH)
        self.linefmt += '{total:10s}\n'
        
        self.clearline(gen)
        self.setplace(gen,'')
        self.setname(gen,'')
        self.setage(gen,'')
        self.setclubs(gen,'')
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
    def setplace(self,gen,place,stylename='place',title=None):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        :param title: (optional) title for popup display
        '''
        
        self.pline[gen]['place'] = str(place)
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name',runnerid=None):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        :param runnerid: runner's id from runner table
        '''
        
        self.pline[gen]['name'] = str(name)
    
    #----------------------------------------------------------------------
    def setage(self,gen,age,stylename='age'):
    #----------------------------------------------------------------------
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param age: value for age column
        :param stylename: name of style for field display
        '''

        self.pline[gen]['age'] = str(age)

    #----------------------------------------------------------------------
    def setclubs(self,gen,clubs,stylename='clubs'):
    #----------------------------------------------------------------------
        '''
        put value in 'clubs' column for output

        :param gen: gender M or F
        :param clubs: value for clubs column
        :param stylename: name of style for field display
        '''

        self.pline[gen]['clubs'] = str(clubs)
    
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
    
class HtmlStandingsHandler(BaseStandingsHandler):
    '''
    StandingsHandler for .html files
    
    :param racelist: list of race numbers in series
    '''
    def __init__(self,racelist):
        BaseStandingsHandler.__init__(self)
        self.HTML = {}
        self.pline = {'F':{},'M':{}}
        self.racelist = racelist
    
    def prepare(self,gen,series,year):
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
        
        # remember the series name -- this is used from the url generated in setname
        self.seriesname = series.name
        
        # open output file
        self.HTML[gen] = [] # "file" will be a list of plines
        
        # generate the header
        self.setheader(gen,True)
        self.setrowclass(gen, '')
        self.setplace(gen,'Place')
        self.setname(gen,'Name')
        self.setage(gen,'Div Age')
        self.setclubs(gen, 'Club')
        self.setnraces(gen,'n')
        self.setdivision(gen,'Division')
        self.settotal(gen,'Total Pts.')
        
        for racenum in self.racelist:
            self.setrace(gen,racenum,racenum)
            
        self.render(gen)
        self.setheader(gen,False)
        
        return len(self.racelist)
    
    def clearline(self,gen):
        '''
        prepare rendering line for output by clearing all entries

        :param gen: gender M or F
        '''
        
        # clear the line
        for k in self.pline[gen]:
            if k in ['header','division']: continue  # header indication and division text are persistent
            self.pline[gen][k] = ''
        
    def setheader(self,gen,header):
        '''
        enable / disable header processing
        
        this is used to determine if header processing is over
        once header processing is over, when rendering, new headers are ignored
        
        :param gen: gender M or F
        :param header: True or False
        '''
        self.pline[gen]['header'] = header
        
    def setrowclass(self, gen, _class):
        '''
        set class(es) for the row

        :param gen: gender M or F
        :param _class: value for the row class
        '''
        
        self.pline[gen]['_class'] = _class
    
    def setplace(self, gen, place, stylename='place', title=None):
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: name of style for field display
        :param title: (optional) title for popup display
        '''
        
        self.pline[gen]['place'] = addstyle(self.pline[gen]['header'], str(place), stylename, title=title)
    
    def setname(self,gen,name,stylename='name',runnerid=None):
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        :param runnerid: runner's id from runner table
        '''
        name = str(name)
        if runnerid:
            nameurl = makelink('{}?{}'.format(flask.url_for('admin.results'),urllib.parse.urlencode({'participant':runnerid,'series':self.seriesname})),name)
        else:
            nameurl = name
        self.pline[gen]['name'] = addstyle(self.pline[gen]['header'],nameurl,stylename)
    
    def setage(self,gen,age,stylename='age'):
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param age: value for age column
        :param stylename: name of style for field display
        '''

        self.pline[gen]['age'] = addstyle(self.pline[gen]['header'],str(age),stylename)

    def setclubs(self,gen,clubs,stylename='clubs'):
        '''
        put value in 'clubs' column for output

        :param gen: gender M or F
        :param clubs: value for clubs column
        :param stylename: name of style for field display
        '''

        self.pline[gen]['clubs'] = addstyle(self.pline[gen]['header'],clubs,stylename)
    
    def setnraces(self,gen,nraces,stylename='nraces'):
        '''
        put value in 'nraces' column for output

        :param gen: gender M or F
        :param nraces: value for nraces column
        :param stylename: name of style for field display
        '''

        self.pline[gen]['nraces'] = addstyle(self.pline[gen]['header'],str(nraces),stylename)

    def setdivision(self,gen,division,stylename='division'):
        '''
        put value in 'division' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param division: value for division column
        :param styledivision: name of style for field display
        '''
        
        self.pline[gen]['division'] = addstyle(self.pline[gen]['header'],str(division),stylename)
    
    def setrace(self,gen,racenum,result,stylename='race'):
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param racenum: number of race
        :param result: value for race column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['race{0}'.format(racenum)] = addstyle(self.pline[gen]['header'],str(result),stylename)
    
    def settotal(self,gen,total,stylename='total'):
        '''
        put value in 'race{n}' column for output, for race n
        should be '' for empty race

        :param gen: gender M or F
        :param value: value for total column
        :param stylename: name of style for field display
        '''
        
        self.pline[gen]['total'] = addstyle(self.pline[gen]['header'],str(total),stylename)
    
    def render(self,gen):
        '''
        output current line to gender file

        :param gen: gender M or F
        '''

        self.HTML[gen].append(self.pline[gen])

        # make sure we have a new instance after "rendering"
        self.pline[gen] = copy.copy(self.pline[gen])
    

    def skipline(self,gen):
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''

        # this is NOOP for HTML
        pass
    
    def close(self):
        '''
        output blank line to gender file

        :param gen: gender M or F
        '''
        
        #this is NOOP for HTML
        pass
    
    def iter(self,gen):
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
        self.colnum['age'] = 2
        self.colnum['clubs'] = 3
        thiscol = 4
        for racenum in self.racelist:
            self.colnum['race{0}'.format(racenum)] = thiscol
            thiscol += 1
        self.colnum['total'] = thiscol

        # set up col widths
        self.ws[gen].col(self.colnum['place']).width = 6*256
        self.ws[gen].col(self.colnum['name']).width = 19*256
        self.ws[gen].col(self.colnum['age']).width = 6*256
        self.ws[gen].col(self.colnum['clubs']).width = 6*256
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
    def setplace(self,gen,place,stylename='place',title=None):
    #----------------------------------------------------------------------
        '''
        put value in 'place' column for output (this should be rendered in 1st column)

        :param gen: gender M or F
        :param place: value for place column
        :param stylename: key into self.style
        :param title: (optional) title for popup display
        '''
        
        self.ws[gen].write(self.rownum[gen],self.colnum['place'],place,self.style[stylename])
    
    #----------------------------------------------------------------------
    def setname(self,gen,name,stylename='name',runnerid=None):
    #----------------------------------------------------------------------
        '''
        put value in 'name' column for output (this should be rendered in 2nd column)

        :param gen: gender M or F
        :param name: value for name column
        :param stylename: name of style for field display
        :param runnerid: runner's id from runner table
        '''
        
        self.ws[gen].write(self.rownum[gen],self.colnum['name'],name,self.style[stylename])
    
    #----------------------------------------------------------------------
    def setage(self,gen,age,stylename='age'):
    #----------------------------------------------------------------------
        '''
        put value in 'age' column for output

        :param gen: gender M or F
        :param age: value for age column
        :param stylename: name of style for field display
        '''

        self.ws[gen].write(self.rownum[gen],self.colnum['age'],age,self.style[stylename])

    #----------------------------------------------------------------------
    def setclubs(self,gen,clubs,stylename='clubs'):
    #----------------------------------------------------------------------
        '''
        put value in 'clubs' column for output

        :param gen: gender M or F
        :param clubs: value for clubs column
        :param stylename: name of style for field display
        '''

        self.ws[gen].write(self.rownum[gen],self.colnum['clubs'],clubs,self.style[stylename])
    
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
        self.proportional_scoring = series.has_series_option(SERIES_OPTION_PROPORTIONAL_SCORING)
        self.requires_club = series.has_series_option(SERIES_OPTION_REQUIRES_CLUB)
        self.display_club = series.has_series_option(SERIES_OPTION_DISPLAY_CLUB)
        self.year = year
        self.races = races
        self.racenums = racenums
        
    #----------------------------------------------------------------------
    def collectstandings(self, racesprocessed, gen, raceid, byrunner, divrunner, runnerresults): 
    #----------------------------------------------------------------------
        '''
        collect standings for this race / series
        
        in byrunner[runnerid,name,age][type], points{race} entries are set to '' for race not run, to 0 for race run but no points given
        
        :param racesprocessed: number of races processed so far
        :param gen: gender, M or F
        :param raceid: race.id to collect standings for
        :param byrunner: dict updated as runner standings are collected {runnerid,name,age:{'bygender':[points1,points2,...],'bydivision':[points1,points2,...]}}
        :param divrunner: dict updated with runner names by division {divlow,divhigh:[runner1,runner2,...],...}
        :param runnerresults: dict updated with set of results runner has {runnerid:{RaceResult1, ...}}
        :rtype: number of standings processed for this race / series
        '''
        numresults = 0
    
        # get all the results currently in the database
        # byrunner = {name:{'bygender':[points,points,...],'bydivision':[points,points,...]}, ...}
        allresults = RaceResult.query.order_by(self.orderby).filter_by(club_id=self.club_id,raceid=raceid,seriesid=self.series.id,gender=gen).all()
        #app.logger.debug('gather results for: clubid={}, raceid={}, seriesid={}, gen={}'.format(self.club_id,raceid,self.series.id,gen))
        if self.hightolow: 
            allresults.reverse()
        
        # determine age for all runners for which there are results
        age = {}

        # for proportional scoring, make a pass through the results to determine best times for gender, division
        if self.proportional_scoring:
            # 48 hours seems long enough
            LONGTIME = 48*60*60
            propbest = {
                'M': {'time': LONGTIME, 'div': {}},
                'F': {'time': LONGTIME, 'div': {}},
            }
            for result in allresults:
                gen = result.gender
                div = (result.divisionlow, result.divisionhigh)
                propbest[gen]['div'].setdefault(div, LONGTIME)
                if result.time < propbest[gen]['time']:
                    propbest[gen]['time'] = result.time
                if result.time < propbest[gen]['div'][div]:
                    propbest[gen]['div'][div] = result.time

        # accumulate results
        for resultndx in range(len(allresults)):
            numresults += 1
            result = allresults[resultndx]
            
            # add runner name 
            name = result.runner.name
            runnerid = result.runnerid
            
            # collect runner's results
            if runnerid not in runnerresults:
                runnerresults[runnerid] = set()
            runnerresults[runnerid].add(result)
            
            # convenience variables
            gen = result.gender
            div = (result.divisionlow, result.divisionhigh)
            racedate = tYmd.asc2dt(result.race.date)
            clubaffiliation = clubaffiliationelement(result)

            # get runner's age for standings
            if runnerid not in age:
                # should be no need to filter on club here
                runner = Runner.query.filter_by(id=runnerid).one()
                # use age on Jan 1 from current year if dob available, else just use age from earliest result
                if runner.dateofbirth:
                    if not runner.estdateofbirth:
                        thisage = timeu.age(datetime(int(self.year),1,1),tYmd.asc2dt(runner.dateofbirth))
                    else:
                        # TODO: this doesn't quite seem right -- we want to emulate Jan 1, but don't know the real dob 
                        # -- should we be looking at earliest race in *any* year?
                        # get_earliestrace can return None if none found, but logic to get here guarantees at least one will be found
                        earlyresult = get_earliestrace(runner, year=racedate.year)
                        divdate = tYmd.asc2dt(earlyresult.race.date)
                        thisage = timeu.age(divdate, tYmd.asc2dt(runner.dateofbirth))
                # no dob found, so just use age from earliest race in the race's year
                else:
                    # get_earliestrace can return None if none found, but logic to get here guarantees at least one will be found
                    earlyresult = get_earliestrace(runner, year=racedate.year)
                    # but check anyway
                    if earlyresult:
                        divdate = tYmd.asc2dt(earlyresult.race.date)
                        # estimate this non-member's birth date to be date of race in the year indicated by age
                        racedatedt = tYmd.asc2dt(earlyresult.race.date)
                        dobdt = datetime(racedatedt.year-earlyresult.age, racedatedt.month, racedatedt.day)
                        # this assumes previously recorded age was correct, probably ok for most series
                        thisage = timeu.age(divdate, dobdt)
                    # strange, how is there RaceResult but no ManagedResult?
                    else:
                        current_app.logger.warning(f'no ManagedResult found for raceid {result.race.id} {runner.name}')
                        thisage = result.agage
                age[runnerid] = thisage
            thisage = age[runnerid]
            
            if (runnerid, name, thisage) not in byrunner:
                byrunner[runnerid, name, thisage] = {}
                byrunner[runnerid, name, thisage]['bygender'] = []
                if self.bydiv:
                    if (runnerid, name, thisage) not in divrunner[(result.divisionlow, result.divisionhigh)]:
                        divrunner[(result.divisionlow,result.divisionhigh)].append((runnerid, name, thisage))
                    byrunner[runnerid, name, thisage]['bydivision'] = []
                if self.display_club:
                    byrunner[runnerid, name, thisage]['clubaffiliation'] = []
            
            # pick up club affiliation if needed and not already in the list
            if self.display_club:
                if clubaffiliation and clubaffiliation.render() not in [c.render() for c in byrunner[runnerid, name, thisage]['clubaffiliation']]:
                    byrunner[runnerid, name, thisage]['clubaffiliation'].append(clubaffiliation)

            # for this runner, catch 'bygender' and 'bydivision' up to current race position
            while len(byrunner[runnerid,name,thisage]['bygender']) < racesprocessed:
                byrunner[runnerid, name, thisage]['bygender'].append('')
                if self.bydiv:
                    byrunner[runnerid, name, thisage]['bydivision'].append('')
                    
            # accumulate points for this result
            # if result is ordered by time, genderplace and divisionplace may be used
            if self.orderby in ['time', 'overallplace']:
                # if result points depend on the number of runners, update maxgenpoints
                if self.maxbynumrunners:
                    self.maxgenpoints = len(allresults)
                
                # if starting at the top (i.e., maxgenpoints is non-zero, accumulate points accordingly
                if self.maxgenpoints:
                    genpoints = self.multiplier*(self.maxgenpoints+1-result.genderplace)
                
                # proportional scoring means points = multiplier * toptime/thistime
                elif self.proportional_scoring:
                    genpoints = round(self.multiplier * (propbest[gen]['time'] / result.time))

                # otherwise, accumulate from the bottom
                else:
                    genpoints = self.multiplier*result.genderplace
                
                # record gender points
                byrunner[runnerid,name,thisage]['bygender'].append(max(genpoints,0))

                # handle divisions
                if self.bydiv:
                    # "normal" case is by max division points
                    if not self.proportional_scoring:
                        divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                    
                    # proportional scoring means points = multiplier * toptime/thistime
                    else:
                        divpoints = round(self.multiplier * (propbest[gen]['div'][div] / result.time))
                    
                    byrunner[runnerid,name,thisage]['bydivision'].append(max(divpoints,0))
            
            # if result was ordered by agpercent, agpercent is used -- assume no divisions
            elif self.orderby == 'agpercent':
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
                
                byrunner[runnerid,name,thisage]['bygender'].append(max(genpoints,0))
                #if self.bydiv:
                #    divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                #    byrunner[runnerid,name,thisage]['bydivision'].append(max(divpoints,0))
            
            # if result is ordered by agtime, agtimeplace may be used -- assume no divisions
            elif self.orderby == 'agtime':
                # if result points depend on the number of runners, update maxgenpoints
                if byrunner:
                    self.maxgenpoints = len(allresults)
                
                # if starting at the top (i.e., maxgenpoints is non-zero, accumulate points accordingly
                if self.maxgenpoints:
                    genpoints = self.multiplier*(self.maxgenpoints+1-result.agtimeplace)
                
                # otherwise, accumulate from the bottom
                else:
                    genpoints = self.multiplier*result.agtimeplace
                
                byrunner[runnerid,name,thisage]['bygender'].append(max(genpoints,0))
                #if self.bydiv:
                #    divpoints = self.multiplier*(self.maxdivpoints+1-result.divisionplace)
                #    byrunner[runnerid,name]['bydivision'].append(max(divpoints,0))
                #
            else:
                raise parameterError("series '{}' results must be ordered by time, overallplace, agtime or agpercent".format(self.series.name))
            
        return numresults            
    
    #----------------------------------------------------------------------
    def renderseries(self,fh): 
    #----------------------------------------------------------------------
        '''
        render standings for a single series
        
        see BaseStandingsHandler for methods of fh
        
        :param fh: StandingsHandler object-like
        '''

        # calculate points
        def calcpoints(byrunner, runnerpool, selector):
            '''
            calculate sorted list of runner results by total points (max to min)
            
            :param byrunner: full data structure by runner
            :param runnerpool: pool of runners to use for this set of results
            :param selector: selector from point to pull results, either 'bygender' or 'bydivision'
            '''
            bypoints = []
            for runnerid,name,age in runnerpool:
                # convert each race result to int if possible
                byrunner[runnerid,name,age][selector] = [int(r) if isinstance(r, float) and r==int(r) else r for r in byrunner[runnerid,name,age][selector]]
                racetotals = byrunner[runnerid,name,age][selector][:]    # make a copy
                # total numbers only, and convert to int if possible
                racetotals = [r for r in racetotals if type(r) in [int,float]]
                racetotals.sort(reverse=True)
                numracesused = min(self.maxraces, len(racetotals)) if self.maxraces else len(racetotals)
                racesused = racetotals[0:numracesused]
                byrunner[runnerid,name,age]['racesused'] = racesused[:]
                totpoints = sum(racesused)
                totpoints = int(totpoints) if totpoints == int(totpoints) else totpoints
                # tied=False may be updated in resultsiterator.tiesort()
                bypoints.append(Points(totpoints=totpoints, runnerid=runnerid, name=name, age=age, tied=False))
                
            bypoints.sort(key=lambda i: i.totpoints, reverse=True)
            return bypoints

        # collect divisions if necessary
        if self.bydiv:
            divisions = []
            for div in Divisions.query.filter_by(club_id=self.club_id,seriesid=self.series.id,active=True).order_by(Divisions.divisionlow).all():
                divisions.append((div.divisionlow, div.divisionhigh))
            if len(divisions) == 0:
                raise dbConsistencyError('series {0} indicates divisions to be calculated, but no divisions found'.format(self.series.name))

        # process each gender
        for gen in ['F','M']:
            # open file, prepare header, etc
            fh.prepare(gen, self.series, self.year)
                    
            # collect data for each race, within byrunner dict
            # track names of runners within each division
            # track results by runner
            byrunner = {}
            runnerresults = {}
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
                self.collectstandings(racesprocessed, gen, race.id, byrunner, divrunner, runnerresults)
                racesprocessed += 1
                
            # render standings
            
            # overall
            fh.setheader(gen,True)
            fh.clearline(gen)
            fh.setplace(gen,'Place','racehdr')
            fh.setname(gen,'Overall','divhdr')
            fh.setage(gen,'Div Age','divhdr')
            fh.setclubs(gen,'Club','divhdr')
            fh.setnraces(gen,'n','divhdr')
            fh.setdivision(gen,'Overall')
            fh.render(gen)
            fh.setheader(gen,False)
            
            # calculate runner total points overall
            bypoints = calcpoints(byrunner, byrunner, 'bygender')
            
            # loop through results, handling ties as defined with self.series and render
            oaawardwinners = {} 
            theseresults = resultsiterator(self.series, bypoints, byrunner, runnerresults, self.races, division=False)
            for thisbypoints in theseresults:
                # break thisbypoints apart, matching self.collectstandings() implementation
                totpoints, runnerid, name, age = thisbypoints.totpoints, thisbypoints.runnerid, thisbypoints.name, thisbypoints.age
                
                # start fresh
                fh.clearline(gen)
                        
                # get the runner's calculated place
                renderplace = theseresults.calcrenderplace(thisbypoints)
                explanation = thisbypoints.explanation if hasattr(thisbypoints, 'explanation') else None
                fh.setplace(gen, renderplace, title=explanation)
                
                # update for overall awards
                if self.series.oaawards and renderplace and renderplace <= self.series.oaawards:
                    oaawardwinners[runnerid] = {'place': renderplace, 'bypoints': thisbypoints}
                    fh.setrowclass(gen, 'row-overall-award')
                    
                # render name and total points, remember last total points
                fh.setname(gen,name,runnerid=runnerid)
                fh.setage(gen,age)
                fh.settotal(gen,totpoints)
                
                # set club affiliation, if needed
                if 'clubaffiliation' in byrunner[runnerid,name,age]:
                    fh.setclubs(gen, byrunner[runnerid,name,age]['clubaffiliation'])
                        
                # render race results
                iracenums = iter(self.racenums)
                nraces = 0
                for pts in byrunner[runnerid,name,age]['bygender']:
                    racenum = next(iracenums)
                    if pts in byrunner[runnerid,name,age]['racesused']:
                        fh.setrace(gen,racenum,pts)
                        byrunner[runnerid,name,age]['racesused'].remove(pts)
                    else:
                        fh.setrace(gen,racenum,pts,stylename='race-dropped')
                    # count number of races runner ran
                    if isinstance(pts, int) or isinstance(pts, float):
                        nraces += 1
                fh.setnraces(gen,nraces)
                fh.render(gen)

            # by division if needed
            if self.bydiv:
            # remember overall awards, so that division display can be adjusted
                fh.setheader(gen,True)
                fh.clearline(gen)
                fh.setplace(gen,'Place','racehdr')
                fh.setname(gen,'Age Group','divhdr')
                fh.setage(gen,'Div Age','divhdr')
                fh.setclubs(gen,'clubs','divhdr')
                fh.setnraces(gen,'n','divhdr')
                fh.render(gen)
                fh.setheader(gen,False)
                
                for div in divisions:
                    fh.setheader(gen,True)
                    fh.clearline(gen)
                    divlow,divhigh = div
                    if not divlow or divlow <= 1:
                        divtext = 'up to {0}'.format(divhigh)
                    elif not divhigh or divhigh >= 99: 
                        divtext = '{0} and up'.format(divlow)
                    else:
                        divtext = '{0} to {1}'.format(divlow,divhigh)
                    fh.setname(gen,divtext,'divhdr')
                    fh.setdivision(gen,divtext)
                    fh.render(gen)
                    fh.setheader(gen,False)
                    
                    # calculate runner total points for this division
                    bypoints = calcpoints(byrunner, divrunner[div], 'bydivision')
                    
                    # loop through results, handling ties as defined with self.series, and render
                    theseresults = resultsiterator(self.series, bypoints, byrunner, runnerresults, self.races, division=True)
                    for thisbypoints in theseresults:
                        # break thisbypoints apart, matching self.collectstandings() implementation
                        totpoints, runnerid, name, age = thisbypoints.totpoints, thisbypoints.runnerid, thisbypoints.name, thisbypoints.age

                        fh.clearline(gen)
                        
                        # check for overall winner
                        if runnerid in oaawardwinners:
                            renderplace = f'oa-{oaawardwinners[runnerid]["place"]}'
                            fh.setrowclass(gen, 'row-overall-award')
                        
                        # normal division placer
                        else:
                            # get the runner's calculated place
                            renderplace = theseresults.calcrenderplace(thisbypoints)

                            if self.series.divawards and renderplace and renderplace <= self.series.divawards:
                                fh.setrowclass(gen, 'row-division-award')

                        # render the place
                        explanation = thisbypoints.explanation if hasattr(thisbypoints, 'explanation') else None
                        fh.setplace(gen, renderplace, title=explanation)
                        
                        # render name and total points, remember last total points
                        fh.setname(gen,name,runnerid=runnerid)
                        fh.setage(gen,age)
                        fh.settotal(gen,totpoints)

                        # set club affiliation, if needed
                        if 'clubaffiliation' in byrunner[runnerid,name,age]:
                            fh.setclubs(gen, byrunner[runnerid,name,age]['clubaffiliation'])
                        
                        # render race results
                        iracenums = iter(self.racenums)
                        nraces = 0
                        for pts in byrunner[runnerid,name,age]['bydivision']:
                            racenum = next(iracenums)
                            if pts in byrunner[runnerid,name,age]['racesused']:
                                fh.setrace(gen,racenum,pts)
                                byrunner[runnerid,name,age]['racesused'].remove(pts)
                            else:
                                fh.setrace(gen,racenum,pts,stylename='race-dropped')
                            # count number of races runner ran
                            if isinstance(pts, int) or isinstance(pts, float):
                                nraces += 1
                        fh.setnraces(gen,nraces)
                        fh.render(gen)
                        
                    # skip line between divisions
                    fh.skipline(gen)
                        
            fh.skipline(gen)
                        
        # done with rendering
        fh.close()

class resultsiterator():
    '''
    iterate through results, handling ties if necessary
    
    :param series: Series record
    :param bypoints: sorted list [(totpoints, runnerid, name, age), ...]
    :param byrunner: dict updated from standings collection {runnerid,name,age:{'bygender':[points1,points2,...],'bydivision':[points1,points2,...]}}
    :param runnerresults: {runnerid: {RaceResult1, RaceResult2, ...}}
    :param races: ordered list of Race records, same order as byrunner[]['bygender'] and byrunner[]['bydivision']
    :param division: (optional) use SERIES_TIE_OPTION_DIV_COMPARE_OVERALL handling if configured
    '''
    def __init__(self, series, bypoints, byrunner, runnerresults, races, division=False) -> None:
        self.series = series
        self.bypoints = bypoints
        self.byrunner = byrunner
        self.runnerresults = runnerresults
        self.races = races
        self.racendx = {r.id:races.index(r) for r in self.races}
        
        self.pointstie = []
        self.thisplace = 1
        self.lastplace = 0
        self.lastpoints = -999
        self.division = division
        
        self.seriestiealgs = self.series.tieoptions.split(SERIES_TIE_OPTION_SEPARATOR)
        tiepriorities = {o['value']:o['priority'] for o in SERIES_TIE_OPTIONS}
        self.seriestiealgs.sort(key=lambda i: tiepriorities[i])
        self.tieexplain = {o['value']:o['explanation'] for o in SERIES_TIE_OPTIONS}
        
    def __iter__(self):
        self.pointsndx = 0
        return self
    
    # get next result, processing ties if necessory
    def __next__(self):
        if self.pointsndx >= len(self.bypoints):
            raise StopIteration
        
        # return the upcoming record if no ties detected
        if not self.pointstie:
            # this will be overwritten if a tie is found
            thisbypoints = self.bypoints[self.pointsndx]

            # check for ties
            tiendx = self.pointsndx
            tiefound = False
            while tiendx+1 < len(self.bypoints) and self.bypoints[tiendx].totpoints == self.bypoints[tiendx+1].totpoints:
                self.pointstie.append(self.bypoints[tiendx])
                tiendx += 1
                tiefound = True
            
            # add the last tie to the list
            if tiefound and tiendx < len(self.bypoints):
                self.pointstie.append(self.bypoints[tiendx])
            
            if tiefound:
                # sort the ties depending on tie configuration
                self.pointstie.sort(key=cmp_to_key(self.tiesort), reverse=True)
                
                # set tiebreak explanations after entries are sorted (this is side-effect of tiesort())
                for i in range(1, len(self.pointstie)):
                    self.tiesort(self.pointstie[i-1], self.pointstie[i])
                    # divoroa = 'div' if self.division else 'oa'
                    # current_app.logger.debug(f'tie resolution: {self.pointstie[i].name} {self.pointstie[i].age} {divoroa} {self.pointstie[i].explanation}')
            
        # if in the middle of processing a tie, give the next tied record
        if self.pointstie:
            thisbypoints = self.pointstie.pop(0)
        
        # bump pointsndx regardless
        self.pointsndx += 1
        
        self.totpoints, self.runnerid = thisbypoints.totpoints, thisbypoints.runnerid

        return thisbypoints
    
    def calcrenderplace(self, thisbypoints):
        '''
        calculate place to be rendered, must be called for each place to be rendered, as
        there's a side-effect of updating self.thisplace
        
        :param thisbypoints: bypoints result
        '''
        # runner needs to have run enough races to get a result
        if not self.series.minraces or len(self.runnerresults[self.runnerid]) >= self.series.minraces:
            # render place if it's different than last runner's place, else there was a tie
            renderplace = self.thisplace
            if thisbypoints.tied:
                renderplace = self.lastplace
            self.thisplace += 1
            self.lastplace = renderplace
            self.lastpoints = self.totpoints
        
        # runner hasn't run enough races to get a place
        else:
            renderplace = ''

        return renderplace
    
    def cmp(self, x, y):
        """
        Replacement for built-in function cmp that was removed in Python 3

        Compare the two objects x and y and return an integer according to
        the outcome. The return value is negative if x < y, zero if x == y
        and strictly positive if x > y.
        
        (from https://portingguide.readthedocs.io/en/latest/comparisons.html#the-cmp-function)
        """
        # current_app.logger.debug(f'cmp: x={x} y={y} (x > y) - (x < y)={(x > y) - (x < y)}')
        return (x > y) - (x < y)
    
    def tiesort(self, x, y):
        '''
        sort key function, based on series tie configuration
        '''
        # which byrunner[] field do we retrieve points from?
        if not self.division:
            rrpoints = 'bygender'
        else:
            rrpoints = 'bydivision'
        
        # NOTE: self.seriestiealgs has been sorted by priority
        # WARNING: do not change algorithm in place as this will change standings for previous years' races
        #          rather create new algorithm here and under SERIES_TIE_OPTIONS
        for algorithm in self.seriestiealgs:
            if algorithm == SERIES_TIE_OPTION_HEAD_TO_HEAD_POINTS:
                # determine common races for head to head comparison
                commonraces = {rr.race for rr in self.runnerresults[x.runnerid]} & {rr.race for rr in self.runnerresults[y.runnerid]}
                # sum genderpoints or divisionpoints as appropriate
                xrunner = (x.runnerid, x.name, x.age)
                xpoints = sum([self.byrunner[xrunner][rrpoints][self.racendx[r.race.id]] for r in self.runnerresults[x.runnerid] if r.race in commonraces])
                yrunner = (y.runnerid, y.name, y.age)
                ypoints = sum([self.byrunner[yrunner][rrpoints][self.racendx[r.race.id]] for r in self.runnerresults[y.runnerid] if r.race in commonraces])
                
                # only return comparision if not equal because if equal a later algorithm will be used
                # updating explanation works because a) top tie always has no explanation, and logic runs once again through sorted list
                if xpoints != ypoints:
                    cmp = self.cmp(xpoints, ypoints)
                    if cmp > 0:
                        y.explanation = self.tieexplain[algorithm]
                    else:
                        x.explanation = self.tieexplain[algorithm]
                    return cmp
            
            elif algorithm == SERIES_TIE_OPTION_COMPARE_AVG:
                xresults = [self.byrunner[xrunner][rrpoints][self.racendx[r.race.id]] for r in self.runnerresults[x.runnerid]]
                xresults.sort(reverse=True)
                xnraces = min(self.series.maxraces, len(xresults)) if self.series.maxraces else len(xresults)
                xpoints = mean(xresults[:xnraces])
                yresults = [self.byrunner[yrunner][rrpoints][self.racendx[r.race.id]] for r in self.runnerresults[y.runnerid]]
                yresults.sort(reverse=True)
                ynraces = min(self.series.maxraces, len(yresults)) if self.series.maxraces else len(yresults)
                ypoints = mean(yresults[:ynraces])

                # only return comparision if not equal because if equal a later algorithm will be used
                # updating explanation works because a) top tie always has no explanation, and logic runs once again through sorted list
                if xpoints != ypoints:
                    cmp = self.cmp(xpoints, ypoints)
                    if cmp > 0:
                        y.explanation = self.tieexplain[algorithm]
                    else:
                        x.explanation = self.tieexplain[algorithm]
                    return cmp
            
            elif algorithm == SERIES_TIE_OPTION_DIV_COMPARE_OVERALL:
                if self.division:
                    xresults = [self.byrunner[xrunner]['bygender'][self.racendx[r.race.id]] for r in self.runnerresults[x.runnerid]]
                    xresults.sort(reverse=True)
                    xnraces = min(self.series.maxraces, len(xresults)) if self.series.maxraces else len(xresults)
                    xpoints = mean(xresults[:xnraces])
                    yresults = [self.byrunner[yrunner]['bygender'][self.racendx[r.race.id]] for r in self.runnerresults[y.runnerid]]
                    yresults.sort(reverse=True)
                    ynraces = min(self.series.maxraces, len(yresults)) if self.series.maxraces else len(yresults)
                    ypoints = mean(yresults[:ynraces])

                    # only return comparision if not equal because if equal a later algorithm will be used
                    # updating explanation works because a) top tie always has no explanation, and logic runs once again through sorted list
                    if xpoints != ypoints:
                        cmp = self.cmp(xpoints, ypoints)
                        if cmp > 0:
                            y.explanation = self.tieexplain[algorithm]
                        else:
                            x.explanation = self.tieexplain[algorithm]
                        return cmp
                
        # these passed all algoriths, so are defined to be equal
        y.explanation = 'tied with last'
        y.tied = True
        return 0