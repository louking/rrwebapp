###########################################################################################
# standings - standings views for race results web application
#
# this appears to be obsolete, and can probably be deleted, all views 
# moved to frontend/userviews.py
#
###########################################################################################

# standard
import json
import csv
import os.path
import time
import tempfile
import os
from datetime import timedelta
import traceback

# pypi
import flask
from flask import request, current_app
from flask.views import MethodView

# home grown
from . import bp
from ...accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from ...model import db   # this is ok because this module only runs under flask
from ...apicommon import failure_response, success_response

# module specific needs
import urllib.request, urllib.parse, urllib.error
from ...model import dbdate, Runner, RaceResult, RaceSeries, Race, Series, Club
from ...renderstandings import HtmlStandingsHandler, StandingsRenderer, addstyle
from ...forms import StandingsForm
import loutilities.renderrun as render
from loutilities import timeu
from ...request_helpers import addscripts


#######################################################################
class TestStandings(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club = 'fsrc'
            year = '2015'
            series = 'grandprix'
            description = 'test page for debugging'
            division = 'Overall'
            gender = ''
            printerarg = 'false'
            printerfriendly = (printerarg == 'true')

            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                current_app.logger.error(cause)
                return flask.redirect(flask.url_for('home'))  
            
            club_id = thisclub.id
            clubname = thisclub.name
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for '{}' club".format(series,clubname)
                flask.flash(cause)
                current_app.logger.error(cause)
                return flask.redirect(flask.url_for('home'))  
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(id=seriesid,active=True).order_by(Race.date).all()
            racenums = list(range(1,len(races)+1))
            resulturls = [flask.url_for('frontend.seriesresults',raceid=r.id) for r in races]
            
            # number of rows is set based on whether len(races) is even or odd
            numcols = 2
            even = len(races) / numcols == len(races) / (numcols*1.0)
            numrows = len(races) / numcols if even else len(races) / numcols + 1
            
            racerows = []
            racenum = {}
            for rownum in range(numrows):
                thisrow = []
                for col in range(numcols):
                    racenum[col] = rownum + numrows*col + 1
                    if racenum[col] in racenums:
                        rndx = racenum[col]-1
                        thisrow.append({'num':racenum[col],
                                        'resultsurl':resulturls[rndx],
                                        'race':'{} ({})'.format(races[rndx].name,races[rndx].date)})
                    else:
                        racenum[col] = None
                        thisrow.append({'num':None,'resultsurl':'','race':''})
                racerows.append(thisrow)
                
            # prepare to collect all the results for this series which have any results
            rr = StandingsRenderer(club_id,thisyear,thisseries,races,racenums)
                
            # declare "file" handler for HTML file type
            fh = HtmlStandingsHandler(racenums)
            rr.renderseries(fh)

            roworder = ['division','place','name','gender','age','nraces'] + ['race{}'.format(r) for r in racenums] + ['total']
            headerclasses = (['_rrwebapp-class-col-{}'.format(h) for h in ['division','place','name','gender','age','nraces']]
                                + ['_rrwebapp-class-col-race' for h in racenums]
                                + ['_rrwebapp-class-col-total'])
            tooltips = ([None,None,None,None,None,'Number of races']
                        + [r.name for r in races]
                        + [None])
            
            
            # collect standings
            standings = []
            firstheader = True
            for gen in ['F','M']:
                rows = fh.iter(gen)
                for row in rows:
                    row['gender'] = addstyle(row['header'],gen,'gender')
                    #row['name'] = '<a href="{}?{}">{}</a>'.format(flask.url_for('runnerresults'),urllib.urlencode({'name':row['name'],'series':thisseries.name}),row['name'])
                    if row['header']:
                        row['gender'] = addstyle(row['header'],'Gen','gender')
                        if firstheader:
                            headings = [row[k] for k in roworder]
                            firstheader = False
                        else:
                            continue    # skip extra headers in dataset
                    else:
                        standings.append({'_class': row['_class'], 'data': [row[k] for k in roworder]})

            # headings, headerclasses, tooltips are used together
            headingdata = list(zip(headings,headerclasses,tooltips))
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headingdata=headingdata,
                                         racerows=racerows,standings=standings,description=description,
                                         division=division,gender=gender,printerfriendly=printerfriendly,
                                         pagejsfiles=addscripts(['TestStandings.js']),
                                         inhibityear=True,inhibitclub=True)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            current_app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('home'))  
#----------------------------------------------------------------------
bp.add_url_rule('/_teststandings/',view_func=TestStandings.as_view('teststandings'),methods=['GET'])
#----------------------------------------------------------------------

