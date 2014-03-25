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
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
import xml.etree.ElementTree as ET
from racedb import dbdate, Runner, RaceResult, RaceSeries, Race, Series, Club
from renderstandings import HtmlStandingsHandler, StandingsRenderer, addstyle
from forms import StandingsForm
import loutilities.renderrun as render
from loutilities import timeu

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

            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                app.logger.error(cause)
                flask.redirect(url_for('manageraces'))  # TODO: maybe this isn't the best place to go
            
            club_id = thisclub.id
            thisseries = Series.query.filter_by(club_id=club_id,name=series,year=year).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for club '{}' does not exist".format(series,club)
                flask.flash(cause)
                app.logger.error(cause)
                flask.redirect(url_for('manageraces'))  # TODO: maybe this isn't the best place to go
            
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(seriesid=seriesid,active=True).order_by(Race.date).all()
            racenums = range(1,len(races)+1)
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
                        thisrow.append({'num':racenum[col],'race':'{} ({})'.format(races[racenum[col]-1].name,races[racenum[col]-1].date)})
                    else:
                        racenum[col] = None
                        thisrow.append({'num':None,'race':''})
                racerows.append(thisrow)
                
            # prepare to collect all the results for this series which have any results
            rr = StandingsRenderer(club_id,thisyear,thisseries,races,racenums)
                
            # declare "file" handler for HTML file type
            fh = HtmlStandingsHandler(racenums)
            rr.renderseries(fh)
            roworder = ['division','place','name','gender'] + ['race{}'.format(r) for r in racenums] + ['total']
            headerclasses = (['_rrwebapp-class-col-{}'.format(h) for h in ['division','place','name','gender']]
                                + ['_rrwebapp-class-col-race' for h in racenums]
                                + ['_rrwebapp-class-col-total'])
            
            
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

            # headings and headerclasses are used together
            headingdata = zip(headings,headerclasses)
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headingdata=headingdata,racerows=racerows,standings=standings)
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            app.logger.error(traceback.format_exc())
            raise
            return flask.redirect(flask.url_for('manageraces'))  # TODO: maybe this isn't the best place to go
#----------------------------------------------------------------------
app.add_url_rule('/viewstandings/',view_func=ViewStandings.as_view('viewstandings'),methods=['GET'])
#----------------------------------------------------------------------

