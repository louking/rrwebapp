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
import csv

# pypi
import flask
from flask import make_response,request
from flask.ext.login import login_required
from flask.views import MethodView

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response

# module specific needs
from racedb import Race, Club, Series, RaceSeries
from forms import RaceForm, SeriesForm, RaceSettingsForm
#from runningclub import racefile   # required for xlsx support
from loutilities.csvu import DictReaderStr2Num

#######################################################################
class ManageRaces(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self):
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
            supportedseries = []
            theseseries = Series.query.filter_by(club_id=club_id,active=True,year=year).order_by('name').all()
            for thisseries in theseseries:
                serieselect = (thisseries.id,thisseries.name)
                seriesl.append(serieselect)
                supportedseries.append(thisseries.id)
            form.filterseries.choices = seriesl
            
            # not quite sure why this comes in GET method, but make sure this series is supported
            seriesid = request.args.get('filterseries')
            
            if seriesid and int(seriesid) not in supportedseries:
                return flask.redirect(flask.url_for('manageraces'))    # without any form info
            form.filterseries.data = seriesid if seriesid else '%'
            
            races = []
            raceseries = []
            for race in Race.query.filter_by(club_id=club_id,year=year,active=True).order_by('date').all():
                thisraceseries = [s.series.id for s in race.series if s.active]
                if not seriesid or seriesid == '%' or int(seriesid) in thisraceseries:
                    races.append(race)
                    raceseries.append(thisraceseries)
    
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('manageraces.html',form=form,races=races,series=theseseries,raceseries=raceseries,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/manageraces',view_func=ManageRaces.as_view('manageraces'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class RaceSettings(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,raceid):
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
            
            race = Race.query.filter_by(club_id=club_id,year=year,active=True,id=raceid).first()
    
            form = RaceSettingsForm(name=race.name, date=race.date, distance=race.distance, surface=race.surface)
    
            # get series for this club,year
            seriesl = []
            theseseries = Series.query.filter_by(active=True,club_id=club_id,year=year).order_by('name').all()
            for thisseries in theseseries:
                serieselect = (thisseries.id,thisseries.name)
                seriesl.append(serieselect)
            form.series.choices = seriesl

            form.surface.choices = [('road','road'),('track','track'),('trail','trail')]
            form.series.data = [rs.series.id for rs in race.series if rs.active]

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('racesettings.html',thispagename='Edit Race', action=flask.escape('Update'),form=form,race=race,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,raceid):
    #----------------------------------------------------------------------
        form = RaceSettingsForm()

        # handle Cancel
        if request.form['whichbutton'] == 'Cancel':
            db.session.rollback() # throw out any changes which have been made
            return flask.redirect(flask.url_for('manageraces'))

        # TODO add handle 'Delete'
        elif request.form['whichbutton'] == 'Delete':
            pass
        
        # handle 'Update'
        elif request.form['whichbutton'] == 'Update':
            try:    
                club_id = flask.session['club_id']
                year = flask.session['year']
        
                # get series for this club,year
                seriesl = []
                theseseries = Series.query.filter_by(club_id=club_id,active=True,year=year).order_by('name').all()
                for thisseries in theseseries:
                    serieselect = (thisseries.id,thisseries.name)
                    seriesl.append(serieselect)
                form.series.choices = seriesl
                form.surface.choices = [('road','road'),('track','track'),('trail','trail')]

                if not form.validate_on_submit():
                    return 'error occurred on form submit -- update error message and display form again'
                    
                readcheck = ViewClubDataPermission(club_id)
                writecheck = UpdateClubDataPermission(club_id)
                
                # verify user can at write the data, otherwise abort
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                    
                year = flask.session['year']
                
                race = Race.query.filter_by(club_id=club_id,year=year,active=True,id=raceid).first()
                race.name = form.data['name']
                race.date = form.data['date']
                race.distance = form.data['distance']
                race.surface = form.data['surface']
                
                # get series for this race
                allraceseries = RaceSeries.query.filter_by(active=True,raceid=raceid).all()
                inactiveraceseries = {}
                for d in allraceseries:
                    inactiveraceseries[(d.raceid,d.seriesid)] = d
    
                for seriesid in [int(s) for s in form.series.data]:
                    # add or update raceseries in database
                    raceseries = RaceSeries(raceid,seriesid)
                    added = racedb.insert_or_update(db.session,RaceSeries,raceseries,skipcolumns=['id'],raceid=raceid,seriesid=seriesid)

                    # remove this series from collection of series which should be deleted in database
                    if (raceid,seriesid) in inactiveraceseries:
                        inactiveraceseries.pop((raceid,seriesid))

                # any race/series remaining in 'inactiveraceraceseries' should be deactivated
                for raceid,seriesid in inactiveraceseries:
                    thisraceseries = RaceSeries.query.filter_by(raceid=raceid,seriesid=seriesid).first() # should be only one returned by filter
                    thisraceseries.active = False

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('manageraces'))
            
            except:
                # roll back database updates and close transaction
                db.session.rollback()
                raise
#----------------------------------------------------------------------
app.add_url_rule('/racesettings/<int:raceid>',view_func=RaceSettings.as_view('racesettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#----------------------------------------------------------------------
#######################################################################
class AjaxImportRaces(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        def allowed_file(filename):
            # TODO: add xlsx support
            return '.' in filename and filename.split('.')[-1] in ['csv']
    
        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            thisfile = request.files['file']
            
            # get file extention
            thisfileext = thisfile.filename.split('.')[-1]
            
            # make sure valid file
            if not thisfile:
                db.session.rollback()
                cause = 'Unexpected Error: Missing file'
                print cause
                return failure_response(cause=cause)
            if not allowed_file(thisfile.filename):
                db.session.rollback()
                cause = 'Invalid file type "{}"'.format(thisfileext)
                print cause
                return failure_response(cause=cause)
            
            # get all the races currently in the database for the indicated year
            # hash them into dict by (name,year)
            allraces = Race.query.filter_by(active=True,year=flask.session['year']).all()
            
            # if some races exist, verify user wants to overwrite
            #print 'force = ' + request.args.get('force')
            if allraces and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite races for this year?',confirm=True)
            
            # handle csv file
            if thisfileext == 'csv':
                thisfilecsv = DictReaderStr2Num(thisfile.stream)
                fileraces = []
                for row in thisfilecsv:
                    # make sure all races are within correct year
                    if int(row['year']) != flask.session['year']:
                        db.session.rollback()
                        cause = 'File year {} does not match session year {}'.format(row['year'],flask.session['year'])
                        print cause
                        return failure_response(cause=cause)
                    fileraces.append(row)
                    
            # TODO: add xlsx support -- need to save file in tmpfile to pass to racefile.RaceFile()
            #elif thisfileext == 'xlsx':
            #    tmpfile = xxx
            #    thisfile.save(tmpfile)
            #    thisfilexlsx = racefile.RaceFile(tmpfile)
            #    fileraces = thisfilexlsx.getraces()
            
            # how did this happen?  see allowed_file() for error
            else:
                db.session.rollback()
                cause = 'Unexpected Error: Invalid file extention encountered "{}"'.format(thisfileext)
                print cause
                return failure_response(cause=cause)
            
            # prepare to invalidate any races which are currently there, but not in the file
            inactiveraces = {}
            for thisrace in allraces:
                inactiveraces[thisrace.name,thisrace.year] = thisrace
            
            # process each name in race list
            for thisrace in fileraces:
                # add or update race in database
                race = Race(club_id,thisrace['race'],thisrace['year'],thisrace['racenum'],thisrace['date'],thisrace['time'],thisrace['distance'],thisrace['surface'])
                added = racedb.insert_or_update(db.session,Race,race,skipcolumns=['id'],name=race.name,year=race.year)
                
                # remove this race from collection of races which should be deleted in database
                if (race.name,race.year) in inactiveraces:
                    inactiveraces.pop((race.name,race.year))
                    
            # any races remaining in 'inactiveraces' should be deactivated
            for (name,year) in inactiveraces:
                thisrace = Race.query.filter_by(name=name,year=year).first() # should be only one returned by filter
                thisrace.active = False
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_importraces',view_func=AjaxImportRaces.as_view('_importraces'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class SeriesAPI(MethodView):
#######################################################################
    decorators = [login_required]
    def post(self, club_id, year):
        """
        Handle a POST request at /_series/<club_id>/ or /_series/<club_id>/<year>/
        Return a list of 2-tuples (<series_id>, <series_name>)
        """
        try:
            if year == -1:
                allseries = Series.query.filter_by(active=True,club_id=club_id).order_by('name').all()
            else:
                allseries = Series.query.filter_by(active=True,club_id=club_id,year=year).order_by('name').all()
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
series_api_view = SeriesAPI.as_view('series_api')
app.add_url_rule('/_series/<int:club_id>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
app.add_url_rule('/_series/<int:club_id>/','/_series/<int:club_id>/<int:year>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class ManageSeries(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            year = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            form = SeriesForm()
    
            seriesl = []
            copyyear = []
            for series in Series.query.filter_by(club_id=club_id,active=True).order_by('name').all():
                if series.year == year:
                    seriesl.append(series)
                if (series.year,series.year) not in copyyear:
                    copyyear.append((series.year,series.year))
            copyyear.sort()
            form.copyyear.choices = copyyear
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('manageseries.html',form=form,series=seriesl,copyyear=copyyear,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            year = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            form = SeriesForm()
    
            seriesl = []
            for series in Series.query.filter_by(club_id=club_id,active=True,year=year).order_by('name').all():
                seriesl.append(series)
    
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('manageseries.html',form=form,series=seriesl,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/manageseries',view_func=ManageSeries.as_view('manageseries'),methods=['GET','POST'])
#----------------------------------------------------------------------


