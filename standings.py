###########################################################################################
# standings - standings views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/20/14        Lou King        Create
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
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from app import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
import xml.etree.ElementTree as ET
import urllib
from racedb import dbdate, Runner, RaceResult, RaceSeries, Race, Series, Club
from renderstandings import HtmlStandingsHandler, StandingsRenderer, addstyle
from forms import StandingsForm, ChooseStandingsForm
import loutilities.renderrun as render
from loutilities import timeu

#######################################################################
class ChooseStandings(MethodView):
#######################################################################
    CHOOSE = 'Show Standings'
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            if 'club_id' in flask.session:
                club_id = flask.session['club_id']
                club = Club.query.filter_by(id=club_id).first()
                thisclub = club.shname
                thisyear = flask.session['year']
            else:
                thisclub = None
                thisyear = None
            
            form = ChooseStandingsForm()
            
            # override club_id and thisyear if provided in url
            thisclub = request.args.get('club',thisclub)
            thisyear = request.args.get('year',thisyear)
            
            # initialize year and series choices
            form.year.choices = [(0,'Select Year')]
            form.series.choices = [('','Select Series')]
            
            # get clubs, years and series
            allclubs = Club.query.order_by('name').all()
            form.club.choices = [('','Select Club')] + [(c.shname,c.name) for c in allclubs if c.name != 'owner']
            if thisclub:
                for club in allclubs:
                    if club.shname == thisclub:
                        club_id = club.id
                        break
                form.club.data = thisclub
                allseries = Series.query.filter_by(active=True,club_id=club_id).join("results").all()
                
                # for what years do we have results?
                years = []
                for thisseries in allseries:
                    if thisseries.year not in years:
                        years.append(thisseries.year)
                years.sort()
                form.year.choices += [(y,y) for y in years]
                if thisyear:
                    thisyear = int(thisyear)
                    form.year.data = thisyear
                    form.series.choices += [(s.name,s.name) for s in allseries if s.year == thisyear]

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('choosestandings.html',thispagename='Choose Standings',form=form,action=ChooseStandings.CHOOSE,
                                         useurl=flask.url_for('choosestandings'))
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            form = ChooseStandingsForm()

            # handle Cancel
            if request.form['whichbutton'] == ChooseStandings.CHOOSE:
                # there must be input on all fields
                if not (form.club.data and form.year.data and form.series.data):
                    db.session.rollback()
                    cause =  "you must specify club, year and series"
                    app.logger.debug(cause)
                    flask.flash(cause)
                    return flask.redirect(flask.url_for('choosestandings'))

                
                # pull parameters out of form
                params = {}
                params['club'] = form.club.data
                params['year'] = form.year.data
                params['series'] = form.series.data
                thisclub = Club.query.filter_by(shname=form.club.data).first()
                clubname = thisclub.name
                params['desc'] = '{} - {} {}'.format(clubname,form.year.data,form.series.data)
                
                # commit database updates and close transaction
                db.session.commit()
                url = '{url}?{params}'.format(url=flask.url_for('viewstandings'),params=urllib.urlencode(params))
                return flask.redirect(url)
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

#----------------------------------------------------------------------
app.add_url_rule('/choosestandings/',view_func=ChooseStandings.as_view('choosestandings'),methods=['GET','POST'])
#----------------------------------------------------------------------

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

            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                app.logger.error(cause)
                return flask.redirect(flask.url_for('choosestandings'))  
            
            club_id = thisclub.id
            clubname = thisclub.name
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for '{}' club".format(series,clubname)
                flask.flash(cause)
                app.logger.error(cause)
                return flask.redirect(flask.url_for('choosestandings'))  
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(seriesid=seriesid,active=True).order_by(Race.date).all()
            racenums = range(1,len(races)+1)
            resulturls = [flask.url_for('seriesresults',raceid=r.id) for r in races]
            
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
            # division has to be beyond name, because place and name are fixed, and division has visibility turned off
            roworder = ['place','name','division','gender'] + ['race{}'.format(r) for r in racenums] + ['total']
            headerclasses = (['_rrwebapp-class-col-{}'.format(h) for h in ['division','place','name','gender']]
                                + ['_rrwebapp-class-col-race' for h in racenums]
                                + ['_rrwebapp-class-col-total'])
            tooltips = ([None,None,None,None]
                        + [r.name for r in races]
                        + [None])
            
            
            # collect standings
            standings = []
            firstheader = True
            for gen in ['F','M']:
                rows = fh.iter(gen)
                for row in rows:
                    row['gender'] = addstyle(row['header'],gen,'gender')
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
            headingdata = zip(headings,headerclasses,tooltips)
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headingdata=headingdata,
                                         racerows=racerows,standings=standings,description=description,
                                         inhibityear=True,inhibitclub=True)
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('choosestandings'))  
#----------------------------------------------------------------------
app.add_url_rule('/viewstandings/',view_func=ViewStandings.as_view('viewstandings'),methods=['GET'])
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
            
            allseries = Series.query.filter_by(active=True,club_id=club_id).join("results").all()

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
        
        except Exception,e:
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
                app.logger.error(cause)
                return failure_response(cause=cause)
                
            club = Club.query.filter_by(shname=clubsh).first()
            if not club:
                db.session.rollback()
                cause = 'Unexpected Error: club {} does not exist'.format(clubsh)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            club_id = club.id
            
            allseries = Series.query.filter_by(active=True,club_id=club_id,year=year).join("results").all()
            theseseries = [(s.name,s.name) for s in allseries]
            theseseries.sort()
            choices = [('','Select Series')] + theseseries

            # commit database updates and close transaction
            db.session.commit()
            return success_response(choices=choices)
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}\n{}'.format(e,traceback.format_exc())
            app.logger.error(cause)
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/standings/_getseries',view_func=AjaxGetSeries.as_view('standings/_getseries'),methods=['POST'])
#----------------------------------------------------------------------

