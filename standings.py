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
from racedb import dbdate, Runner, RaceResult, RaceSeries, Race, Series
from renderstandings import HtmlStandingsHandler, StandingsRenderer
from forms import StandingsForm
import loutilities.renderrun as render
from loutilities import timeu

#######################################################################
class ViewStandings(MethodView):
#######################################################################
    #----------------------------------------------------------------------
    def get(self,club,year,series):
    #----------------------------------------------------------------------
        try:
            thisclub = Club.query.filter_by(shname=club).first()
            if not thisclub:
                db.session.rollback()
                cause = "Error: club '{}' does not exist".format(club)
                flask.flash(cause)
                app.logger.error(cause)
                flask.redirect(url_for('manageraces'))  # TODO: maybe this isn't the best place to go
                
            thisseries = Series.query.filter_by(club_id=club_id,name=series).first()
            if not thisseries:
                db.session.rollback()
                cause = "Error: series '{}' does not exist for club '{}' does not exist".format(series,club)
                flask.flash(cause)
                app.logger.error(cause)
                flask.redirect(url_for('manageraces'))  # TODO: maybe this isn't the best place to go
            
            club_id = thisclub.id
            seriesid = thisseries.id
            thisyear = year
            
            form = StandingsForm()
    
            # get races for this series, in date order
            races = Race.query.join("series").filter_by(club_id=self.club_id,seriesid=series.id,active=True).order_by(Race.date).all()
            racenums = range(1,len(races)+1)
            # number of rows is set based on whether len(races) is even or odd
            even = len(races) / 2 == len(races) / 2.0
            numrows = len(races) / 2 if even else len(races) / 2 + 1
            
            racerows = []
            for rownum in range(numrows):
                leftracenum = (rownum * 2) + 1
                rightracenum = (rownum * 2) + numrows + 1 
                if rightracenum not in racenums:
                    rightracenum = None
                thisrow = [{'num':leftracenum,'race':races[leftracenum].name + ': ' + races[leftracenum].date}]
                if rightracenum:
                    thisrow.append({'num':rightracenum,'race':races[rightracenum].name + ': ' + races[rightracenum].date})
                else:
                    thisrow.append({'num':None,'race':''})
                racerows.append(thisrow)
                
            # prepare to collect all the results for this series which have any results
            rr = StandingsRenderer(club_id,thisyear,thisseries,races,racenums)
                
            # declare "file" handler for HTML file type
            fh = HtmlStandingsHandler(racenums)
            rr.renderseries(fh)
            roworder = ['division','place','name','gender'] + racenums + ['total']
            
            # collect standings
            racerows = []
            for gen in ['F','M']:
                rows = fh.iter(gen)
                firstheader = True
                for row in rows:
                    row['gender'] = gen
                    if row['header']:
                        if firstheader:
                            headings = [row[k] for k in roworder]
                            firstheader = False
                        else:
                            continue    # skip extra headers in dataset
                    racerows.append([row[k] for k in roworder])

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('viewstandings.html',form=form,headings=headings,racerows=racerows)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            flask.flash(cause)
            app.logger.error(cause)
            flask.redirect(url_for('manageraces'))  # TODO: maybe this isn't the best place to go
#----------------------------------------------------------------------
app.add_url_rule('/viewstandings',view_func=ViewStandings.as_view('viewstandings'),methods=['GET'])
#----------------------------------------------------------------------

