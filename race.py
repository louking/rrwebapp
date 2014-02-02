###########################################################################################
# rrwebapp.race - race views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/15/14        Lou King        Create
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

# pypi
import flask
from flask import make_response
from flask.ext.login import login_required
from flask.views import MethodView

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask

# module specific needs
from racedb import Race, Club, Series
from rrwebapp.forms import RaceForm

#----------------------------------------------------------------------
@app.route('/manageraces')
@login_required
def manageraces():
#----------------------------------------------------------------------
    try:
        club_id = flask.session['club_id']
        
        readcheck = ViewClubDataPermission(club_id)
        writecheck = UpdateClubDataPermission(club_id)
        
        # verify user can at least read the data, otherwise abort
        if not readcheck.can():
            db.session.rollback()
            flask.abort(403)
            
        year = flask.session['year']
        
        form = RaceForm()

        seriesl = [('%','all series')]
        theseseries = Series.query.filter_by(club_id=club_id,active=True,year=year).order_by('name').all()
        for thisseries in theseseries:
            serieselect = (thisseries.id,thisseries.name)
            seriesl.append(serieselect)
        form.filterseries.choices = seriesl
        seriesid = flask.request.args.get('filterseries')
        form.filterseries.data = seriesid if seriesid else '%'
        
        races = []
        for race in Race.query.filter_by(club_id=club_id,year=year,active=True).order_by('date').all():
            raceseries = [s.series.id for s in race.series if s.active]
            if not seriesid or seriesid == '%' or int(seriesid) in raceseries:
                races.append(race)

        # commit database updates and close transaction
        db.session.commit()
        return flask.render_template('manageraces.html',form=form,races=races,writeallowed=writecheck.can())
    
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

#----------------------------------------------------------------------
@app.route('/importraces')
@login_required
def importraces():
#----------------------------------------------------------------------
    try:
        club_id = session.club_id
        
        readcheck = ViewClubDataPermission(club_id)
        writecheck = UpdateClubDataPermission(club_id)
        
        # verify user can at least read the data, otherwise abort
        if not readcheck.can():
            db.session.rollback()
            flask.abort(403)
            
        # TODO: add some code here
        
        # commit database updates and close transaction
        db.session.commit()
        return flask.redirect(flask.url_for('manageraces'))
    
    except:
        # roll back database updates and close transaction
        db.session.rollback()
        raise

#######################################################################
class SeriesAPI(MethodView):
#######################################################################
    decorators = [login_required]
    def get(self, club_id):
        """
        Handle a GET request at /_series/<club_id>/
        Return a list of 2-tuples (<series_id>, <series_name>)
        """
        try:
            allseries = Series.query.filter_by(club_id=club_id,active=True).order_by('name').all()
            data = [(s.id, s.name) for s in allseries]
            response = make_response(json.dumps(data))
            response.content_type = 'application/json'

            # commit database updates and close transaction
            db.session.commit()
            return response
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

#----------------------------------------------------------------------
app.add_url_rule('/_series/<int:club_id>',view_func=SeriesAPI.as_view('series_api'),methods=['GET'])
#----------------------------------------------------------------------

