###########################################################################################
# standings - standings views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/20/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
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
from flask import request
from flask.views import MethodView

# home grown
from . import app
from .accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from .model import db   # this is ok because this module only runs under flask
from .apicommon import failure_response, success_response

# module specific needs
import urllib.request, urllib.parse, urllib.error
from .model import dbdate, Runner, RaceResult, RaceSeries, Race, Series, Club
from .renderstandings import HtmlStandingsHandler, StandingsRenderer, addstyle
from .forms import StandingsForm
import loutilities.renderrun as render
from loutilities import timeu
from .request_helpers import addscripts


#######################################################################
class ViewStandings(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club = request.args.get('club')
            year = request.args.get('year')
            series = request.args.get('series')
            description = request.args.get('desc')
            division = request.args.get('div','Overall')
            gender = request.args.get('gen','')
            printerarg = request.args.get('printerfriendly','false')
            printerfriendly = (printerarg == 'true')

            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                app.logger.error(cause)
                return flask.redirect(flask.url_for('index'))
            
            club_id = thisclub.id
            clubname = thisclub.name
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for '{}' club".format(series,clubname)
                flask.flash(cause)
                app.logger.error(cause)
                return flask.redirect(flask.url_for('index'))
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(id=seriesid,active=True).order_by(Race.date).all()
            racenums = list(range(1,len(races)+1))
            resulturls = [flask.url_for('.seriesresults',raceid=r.id) for r in races]
            
            # number of rows is set based on whether len(races) is even or odd
            numcols = 2
            even = len(races) // numcols == len(races) / (numcols*1.0)
            numrows = len(races) // numcols if even else len(races) // numcols + 1
            
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
                        standings.append([row[k] for k in roworder])

            # headings, headerclasses, tooltips are used together
            headingdata = list(zip(headings,headerclasses,tooltips))
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headingdata=headingdata,
                                         racerows=racerows,standings=standings,description=description,
                                         division=division,gender=gender,printerfriendly=printerfriendly,
                                         inhibityear=True,inhibitclub=True)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('index'))
#----------------------------------------------------------------------
app.add_url_rule('/viewstandings/',view_func=ViewStandings.as_view('viewstandings'),methods=['GET'])
#----------------------------------------------------------------------

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
                app.logger.error(cause)
                return flask.redirect(flask.url_for('home'))  
            
            club_id = thisclub.id
            clubname = thisclub.name
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for '{}' club".format(series,clubname)
                flask.flash(cause)
                app.logger.error(cause)
                return flask.redirect(flask.url_for('home'))  
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(id=seriesid,active=True).order_by(Race.date).all()
            racenums = list(range(1,len(races)+1))
            resulturls = [flask.url_for('.seriesresults',raceid=r.id) for r in races]
            
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
                        standings.append([row[k] for k in roworder])

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
            app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('home'))  
#----------------------------------------------------------------------
app.add_url_rule('/_teststandings/',view_func=TestStandings.as_view('teststandings'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class AjaxGetYears(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            clubsh = request.args.get('club',None)
            
            if not clubsh:
                db.session.rollback()
                cause = 'Unexpected Error: both club and year must be specified'
                app.logger.error(cause)
                return failure_response(cause=cause)
                
            club = Club.query.filter_by(shname=clubsh).first()
            if not club:
                db.session.rollback()
                cause = 'Unexpected Error: club {} does not exist'.format(clubsh)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            club_id = club.id
            
            allseries = Series.query.filter_by(active=True,club_id=club_id).all()

            years = []
            for thisseries in allseries:
                if thisseries.year not in years:
                    years.append(thisseries.year)
            years.sort()
            theseyears = [(y,y) for y in years]

            choices = [(0,'Select Year')] + theseyears

            # commit database updates and close transaction
            db.session.commit()
            return success_response(choices=choices)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            app.logger.error(cause)
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/standings/_getyears',view_func=AjaxGetYears.as_view('standings/_getyears'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxGetSeries(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            clubsh = request.args.get('club',None)
            year = request.args.get('year',None)
            
            if not clubsh or not year:
                db.session.rollback()
                cause = 'Unexpected Error: both club and year must be specified'
                # this can happen if user has no cookie initialized when the popup is initially brought up
                # app.logger.error(cause)
                return failure_response(cause=cause)
                
            club = Club.query.filter_by(shname=clubsh).first()
            if not club:
                db.session.rollback()
                cause = 'Unexpected Error: club {} does not exist'.format(clubsh)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            club_id = club.id
            
            allseries = Series.query.filter_by(active=True,club_id=club_id,year=year).all()
            # see https://editor.datatables.net/plug-ins/field-type/editor.select2
            theseseries = sorted([{'label':s.name, 'value':s.name} for s in allseries], key=lambda s: s['label'])
            # choices = [{'label':'Select Series', 'value':''}] + theseseries
            choices = theseseries

            # commit database updates and close transaction
            db.session.commit()
            return success_response(choices=choices)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            app.logger.error(cause)
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/standings/_getseries',view_func=AjaxGetSeries.as_view('standings/_getseries'),methods=['POST'])
#----------------------------------------------------------------------

