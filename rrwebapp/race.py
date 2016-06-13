###########################################################################################
# rrwebapp.race - race views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       01/15/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import json
import csv
import traceback

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
from apicommon import failure_response, success_response, check_header

# module specific needs
from racedb import Race, Club, Series, RaceSeries, Divisions, ManagedResult
from forms import RaceForm, SeriesForm, RaceSettingsForm, DivisionForm
#from runningclub import racefile   # required for xlsx support
from loutilities.csvu import DictReaderStr2Num

# acceptable surfaces
SURFACES = 'road,track,trail'.split(',')

#######################################################################
class ManageRaces(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            
            form = RaceForm()
    
            seriesl = [('','all series')]
            supportedseries = []
            theseseries = Series.query.filter_by(club_id=club_id,active=True,year=thisyear).order_by('name').all()
            for thisseries in theseseries:
                serieselect = (thisseries.id,thisseries.name)
                seriesl.append(serieselect)
                supportedseries.append(thisseries.id)
            form.filterseries.choices = seriesl
            
            # not quite sure why this comes in GET method, but make sure this series is supported
            seriesid = request.args.get('filterseries')
            
            if seriesid and int(seriesid) not in supportedseries:
                return flask.redirect(flask.url_for('manageraces'))    # without any form info
            
            # select is set to what url indicated
            form.filterseries.data = seriesid if seriesid else ''
            
            races = []
            raceseries = []
            rawresults = []
            tabresults = []
            for race in Race.query.filter_by(club_id=club_id,year=thisyear,active=True).order_by('date').all():
                thisraceseries = [s.series.id for s in race.series if s.active]
                if not seriesid or int(seriesid) in thisraceseries:
                    races.append(race)
                    racerawresults = ManagedResult.query.filter_by(club_id=club_id,raceid=race.id).first()
                    rawresults.append(True if racerawresults else False)        # raw results were imported
                    tabresults.append(True if len(race.results) > 0 else False) # results were tabulated
                    raceseries.append(thisraceseries)

            # combine parallel lists for processing in form
            raceresultsseries = zip(races,rawresults,tabresults,raceseries)
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('manageraces.html',form=form,raceresultsseries=raceresultsseries,series=theseseries,
                                         writeallowed=writecheck.can())
        
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
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # raceid == 0 means add
            if raceid == 0:
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                race = Race(club_id,thisyear)
                form = RaceSettingsForm()
                action = 'Add'
                pagename = 'Add Race'
            
            # raceid != 0 means update
            else:
                race = Race.query.filter_by(club_id=club_id,year=thisyear,active=True,id=raceid).first()
    
                # copy source attributes to form
                params = {}
                for field in vars(race):
                    params[field] = getattr(race,field)
                
                form = RaceSettingsForm(**params)
                action = 'Update'
                pagename = 'Edit Race'
    
            # get series for this club,year
            seriesl = []
            theseseries = Series.query.filter_by(active=True,club_id=club_id,year=thisyear).order_by('name').all()
            for thisseries in theseseries:
                serieselect = (thisseries.id,thisseries.name)
                seriesl.append(serieselect)
            form.series.choices = seriesl

            form.series.data = [rs.series.id for rs in race.series if rs.active]

            form.surface.choices = [(s,s) for s in SURFACES]

            # commit database updates and close transaction
            db.session.commit()
            # delete button only for edit (raceid != 0)
            return flask.render_template('racesettings.html',thispagename=pagename,
                                         action=action,deletebutton=(raceid!=0),
                                         form=form,race=race,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,raceid):
    #----------------------------------------------------------------------
        form = RaceSettingsForm()

        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            # handle Cancel
            if request.form['whichbutton'] == 'Cancel':
                db.session.rollback() # throw out any changes which have been made
                return flask.redirect(flask.url_for('manageraces'))
    
            # handle Delete
            elif request.form['whichbutton'] == 'Delete':
                race = Race.query.filter_by(club_id=club_id,year=thisyear,active=True,id=raceid).first()
                db.session.delete(race)

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('manageraces'))

            # handle Update and Add
            elif request.form['whichbutton'] in ['Update','Add']:
                # get series for this club,year
                seriesl = []
                theseseries = Series.query.filter_by(club_id=club_id,active=True,year=thisyear).order_by('name').all()
                for thisseries in theseseries:
                    serieselect = (thisseries.id,thisseries.name)
                    seriesl.append(serieselect)
                form.series.choices = seriesl
                form.surface.choices = [(s,s) for s in SURFACES]

                if not form.validate_on_submit():
                    return 'error occurred on form submit -- update error message and display form again'
                    
                readcheck = ViewClubDataPermission(club_id)
                writecheck = UpdateClubDataPermission(club_id)
                
                # verify user can at write the data, otherwise abort
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                
                # add
                if request.form['whichbutton'] == 'Add':
                    race = Race(club_id,thisyear)
                # update
                else:
                    race = Race.query.filter_by(club_id=club_id,year=thisyear,active=True,id=raceid).first()
                
                # copy fields from form to db object
                for field in vars(race):
                    # only copy attributes which are in the form class already
                    if field in form.data:
                        setattr(race,field,form.data[field])
                
                # add
                if request.form['whichbutton'] == 'Add':
                    db.session.add(race)
                    db.session.flush()  # needed to update race.id
                    raceid = race.id

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

                # any race/series remaining in 'inactiveraceraceseries' should be deleted
                for raceid,seriesid in inactiveraceseries:
                    thisraceseries = RaceSeries.query.filter_by(raceid=raceid,seriesid=seriesid).first() # should be only one returned by filter
                    db.session.delete(thisraceseries)

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
            thisyear = flask.session['year']
            
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
                app.logger.error(cause)
                return failure_response(cause=cause)
            if not allowed_file(thisfile.filename):
                db.session.rollback()
                cause = 'Invalid file type "{}"'.format(thisfileext)
                app.logger.warning(cause)
                return failure_response(cause=cause)

            # handle csv file
            if thisfileext == 'csv':
                thisfilecsv = DictReaderStr2Num(thisfile.stream)

                # verify file has required fields
                requiredfields = 'year,race,date,distance,surface'.split(',')
                if not check_header(requiredfields, thisfilecsv.fieldnames):
                    db.session.rollback()
                    cause = "invalid races file - one or more header fields missing, must have all of '{}'".format("', '".join(requiredfields))
                    app.logger.error(cause)
                    return failure_response(cause=cause)

                fileraces = []
                for row in thisfilecsv:
                    # make sure all races are within correct year
                    if int(row['year']) != flask.session['year']:
                        db.session.rollback()
                        cause = 'File year {} does not match session year {}'.format(row['year'],flask.session['year'])
                        app.logger.warning(cause)
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
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # get all the races currently in the database for the indicated club,year
            allraces = Race.query.filter_by(club_id=club_id,active=True,year=thisyear).all()
            
            # if some races exist, verify user wants to overwrite
            if allraces and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite races for this year?',confirm=True)
            
            # prepare to invalidate any races which are currently there, but not in the file
            inactiveraces = {}
            for thisrace in allraces:
                inactiveraces[thisrace.name,thisrace.year] = thisrace
            
            # process each name in race list
            for thisrace in fileraces:
                # make sure surface is acceptable
                if thisrace['surface'] not in SURFACES:
                    db.session.rollback()
                    cause = 'Bad surface "{}" encountered for race "{}". Must be one of {}'.format(thisrace['surface'],thisrace['race'],SURFACES)
                    app.logger.error(cause)
                    return failure_response(cause=cause)

                # time field is optional
                if 'time' not in thisrace:
                    thisrace['time'] = ''

                # add or update race in database
                race = Race(club_id,thisrace['year'],thisrace['race'],None,thisrace['date'],thisrace['time'],thisrace['distance'],thisrace['surface'])
                added = racedb.insert_or_update(db.session,Race,race,skipcolumns=['id'],club_id=club_id,name=race.name,year=race.year)
                
                # remove this race from collection of races which should be deleted in database
                if (race.name,race.year) in inactiveraces:
                    inactiveraces.pop((race.name,race.year))
                    
            # any races remaining in 'inactiveraces' should be deactivated # TODO: should these be deleted?  That's pretty dangerous
            for (name,year) in inactiveraces:
                thisrace = Race.query.filter_by(club_id=club_id,name=name,year=year).first() # should be only one returned by filter
                thisrace.active = False
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except Exception,e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_importraces',view_func=AjaxImportRaces.as_view('_importraces'),methods=['POST'])
#----------------------------------------------------------------------

########################################################################
#class SeriesAPI(MethodView):
########################################################################
#    decorators = [login_required]
#    def post(self, club_id, year):
#        """
#        Handle a POST request at /_series/<club_id>/ or /_series/<club_id>/<year>/
#        Return a list of 2-tuples (<series_id>, <series_name>)
#        """
#        try:
#            if year == -1:
#                allseries = Series.query.filter_by(active=True,club_id=club_id).order_by('name').all()
#            else:
#                allseries = Series.query.filter_by(active=True,club_id=club_id,year=year).order_by('name').all()
#            data = [(s.id, s.name) for s in allseries]
#            response = make_response(json.dumps(data))
#            response.content_type = 'application/json'
#
#            # commit database updates and close transaction
#            db.session.commit()
#            return response
#        
#        except:
#            # roll back database updates and close transaction
#            db.session.rollback()
#            raise
##----------------------------------------------------------------------
#series_api_view = SeriesAPI.as_view('series_api')
#app.add_url_rule('/_series/<int:club_id>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
#app.add_url_rule('/_series/<int:club_id>/','/_series/<int:club_id>/<int:year>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
##----------------------------------------------------------------------

#######################################################################
class ManageSeries(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
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
                # show all series from this year
                if series.year == thisyear:
                    seriesl.append(series)
                # options for copy do not include this year
                elif (series.year,series.year) not in copyyear:
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
app.add_url_rule('/manageseries',view_func=ManageSeries.as_view('manageseries'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class SeriesSettings(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,seriesid):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
            
            # seriesid == 0 means add
            if seriesid == 0:
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                series = Series(club_id, thisyear)
                form = SeriesForm()
                action = 'Add'
                pagename = 'Add Series'
 
            # seriesid != 0 means update
            else:
                series = Series.query.filter_by(club_id=club_id,year=thisyear,active=True,id=seriesid).first()
        
                # copy source attributes to form
                params = {}
                for field in vars(series):
                    # only copy attributes which are in the form class already
                    params[field] = getattr(series,field)
                
                form = SeriesForm(**params)
                action = 'Update'
                pagename = 'Edit Series'
            
            # get races for this club,year
            races = []
            theseraces = Race.query.filter_by(active=True,club_id=club_id,year=thisyear).order_by('date').all()
            for thisrace in theseraces:
                raceselect = (thisrace.id,thisrace.name)
                races.append(raceselect)
            form.races.choices = races
            form.races.data = [rs.race.id for rs in series.races if rs.active]

            # commit database updates and close transaction
            db.session.commit()
            # delete button only for edit (seriesid != 0)
            return flask.render_template('seriessettings.html',thispagename=pagename,action=action,deletebutton=(seriesid!=0),
                                         form=form,series=series,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,seriesid):
    #----------------------------------------------------------------------
        form = SeriesForm()

        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            # handle Cancel
            if request.form['whichbutton'] == 'Cancel':
                db.session.rollback() # throw out any changes which have been made
                return flask.redirect(flask.url_for('manageseries'))
    
            # handle Delete
            elif request.form['whichbutton'] == 'Delete':
                series = Series.query.filter_by(club_id=club_id,year=thisyear,active=True,id=seriesid).first()
                db.session.delete(series)
    
                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('manageseries'))
    
            # handle 'Update'
            elif request.form['whichbutton'] in ['Update','Add']:
                # get the indicated series
                # add
                if request.form['whichbutton'] == 'Add':
                    series = Series(club_id,thisyear)
                # update
                else:
                    series = Series.query.filter_by(club_id=club_id,year=thisyear,active=True,id=seriesid).first()

                # get races for this club,year
                races = []
                theseraces = Race.query.filter_by(active=True,club_id=club_id,year=thisyear).order_by('date').all()
                for thisrace in theseraces:
                    raceselect = (thisrace.id,thisrace.name)
                    races.append(raceselect)
                form.races.choices = races  # this has to be before form validation

                if not form.validate():
                    app.logger.warning(form.errors)
                    return 'error occurred on form submit -- update error message and display form again'
                    
                readcheck = ViewClubDataPermission(club_id)
                writecheck = UpdateClubDataPermission(club_id)
                
                # verify user can at write the data, otherwise abort
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                    
                for field in vars(series):
                    # only copy attributes which are in the form class already
                    if field in form.data:
                        setattr(series,field,form.data[field])

                # add
                if request.form['whichbutton'] == 'Add':
                    db.session.add(series)
                    db.session.flush()  # needed to update series.id
                    seriesid = series.id

                # get races for this series
                allraceseries = RaceSeries.query.filter_by(active=True,seriesid=seriesid).all()
                inactiveraceseries = {}
                for d in allraceseries:
                    inactiveraceseries[(d.raceid,d.seriesid)] = d
    
                for raceid in [int(r) for r in form.races.data]:
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
                return flask.redirect(flask.url_for('manageseries'))
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/seriessettings/<int:seriesid>',view_func=SeriesSettings.as_view('seriessettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxCopySeries(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            # get requested year to copy and current year
            if not request.args.get('copyyear'):
                db.session.rollback()
                return failure_response(cause='Unexpected Error: copyyear argument missing')
            copyyear = int(request.args.get('copyyear'))
            thisyear = flask.session['year']
            
            # if some series exists for this year, verify user wants to overwrite
            thisyearseries = Series.query.filter_by(club_id=club_id,active=True,year=thisyear).all()
            if thisyearseries and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite series for this year?',confirm=True)

            # user has agreed to overwrite any series -- assume all are obsolete until overwritten
            obsoleteseries = {}
            for series in thisyearseries:
                obsoleteseries[series.name] = series
            
            # copy each entry from "copyyear"
            for series in Series.query.filter_by(club_id=club_id,active=True,year=copyyear).all():
                newseries = Series(series.club_id,thisyear,series.name,series.membersonly,
                                   series.calcoverall,series.calcdivisions,series.calcagegrade,
                                   series.orderby,series.hightolow,series.averagetie,
                                   series.maxraces,series.multiplier,series.maxgenpoints,series.maxdivpoints, series.maxbynumrunners)
                racedb.insert_or_update(db.session,Series,newseries,name=newseries.name,year=thisyear,club_id=club_id,skipcolumns=['id'])
                
                # any series we updated is not obsolete
                if newseries.name in obsoleteseries:
                    obsoleteseries.pop(newseries.name)
                    
            # remove obsolete series
            # TODO: is there any reason these should not be deleted?
            for seriesname in obsoleteseries:
                obsoleteseries[seriesname].active = False
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_copyseries',view_func=AjaxCopySeries.as_view('_copyseries'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class ManageDivisions(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            form = DivisionForm()
    
            divisions = []
            copyyear = []
            for division in Divisions.query.filter_by(club_id=club_id,active=True).order_by('seriesid','divisionlow').all():
                # show all division from this year
                if division.year == thisyear:
                    divisions.append(division)
                # options for copy do not include this year
                elif (division.year,division.year) not in copyyear:
                    copyyear.append((division.year,division.year))
            copyyear.sort()
            form.copyyear.choices = copyyear
            
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('managedivisions.html',form=form,divisions=divisions,copyyear=copyyear,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/managedivisions',view_func=ManageDivisions.as_view('managedivisions'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class DivisionSettings(MethodView):
#######################################################################
    decorators = [login_required]
    #----------------------------------------------------------------------
    def get(self,divisionid):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # divisionid == 0 means add
            if divisionid == 0:
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                division = Divisions(club_id,thisyear)
                form = DivisionForm()
                action = 'Add'
                pagename = 'Add Division'
            
            # divisionid != 0 means update
            else:
                division = Divisions.query.filter_by(club_id=club_id,year=thisyear,active=True,id=divisionid).first()
    
                # copy source attributes to form
                params = {}
                for field in vars(division):
                    # only copy attributes which are in the form class already
                    params[field] = getattr(division,field)
                
                form = DivisionForm(**params)
                action = 'Update'
                pagename = 'Edit Division'
           
            # get series for this club,year
            series = []
            theseseries = Series.query.filter_by(active=True,club_id=club_id,year=thisyear).order_by('name').all()
            for thisseries in theseseries:
                serieselect = (thisseries.id,thisseries.name)
                series.append(serieselect)
            form.seriesid.choices = series

            # commit database updates and close transaction
            db.session.commit()
            # delete button only for edit (divisionid != 0)
            return flask.render_template('divisionsettings.html',thispagename=pagename,
                                         action=action,deletebutton=(divisionid!=0),
                                         form=form,divisions=division,writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
        
    #----------------------------------------------------------------------
    def post(self,divisionid):
    #----------------------------------------------------------------------
        form = DivisionForm()

        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']

            # handle Cancel
            if request.form['whichbutton'] == 'Cancel':
                db.session.rollback() # throw out any changes which have been made
                return flask.redirect(flask.url_for('managedivisions'))
    
            # TODO add handle 'Delete'
            elif request.form['whichbutton'] == 'Delete':
                    division = Divisions.query.filter_by(club_id=club_id,year=thisyear,active=True,id=divisionid).first()
                    db.session.delete(division)
                
                    # commit database updates and close transaction
                    db.session.commit()
                    return flask.redirect(flask.url_for('managedivisions'))
    
            # handle Update and Add
            elif request.form['whichbutton'] in ['Update','Add']:
                # add
                if request.form['whichbutton'] == 'Add':
                    division = Divisions(club_id,thisyear)
                else:
                    # get the indicated division
                    division = Divisions.query.filter_by(club_id=club_id,year=thisyear,active=True,id=divisionid).first()

                # get series for this club,year
                series = []
                theseseries = Series.query.filter_by(active=True,club_id=club_id,year=thisyear).order_by('name').all()
                for thisseries in theseseries:
                    serieselect = (thisseries.id,thisseries.name)
                    series.append(serieselect)
                form.seriesid.choices = series  # this has to be before form validation

                if not form.validate():
                    app.logger.warning(form.errors)
                    return 'error occurred on form submit -- update error message and display form again'
                    
                readcheck = ViewClubDataPermission(club_id)
                writecheck = UpdateClubDataPermission(club_id)
                
                # verify user can at write the data, otherwise abort
                if not writecheck.can():
                    db.session.rollback()
                    flask.abort(403)
                    
                for field in vars(division):
                    # only copy attributes which are in the form class already
                    if field in form.data:
                        setattr(division,field,form.data[field])

                # add
                if request.form['whichbutton'] == 'Add':
                    db.session.add(division)
                    db.session.flush()  # needed to update division.id
                    divisionid = division.id
                    # well this isn't really needed at this time, but is done for consistency with other views

                # commit database updates and close transaction
                db.session.commit()
                return flask.redirect(flask.url_for('managedivisions'))
            
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/divisionsettings/<int:divisionid>',view_func=DivisionSettings.as_view('divisionsettings'),methods=['GET','POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxCopyDivisions(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            # get requested year to copy and current year
            if not request.args.get('copyyear'):
                db.session.rollback()
                return failure_response(cause='Unexpected Error: copyyear argument missing')
            copyyear = int(request.args.get('copyyear'))
            thisyear = flask.session['year']
            
            # if some divisions exists for this year, verify user wants to overwrite
            thisyeardivisions = Divisions.query.filter_by(club_id=club_id,active=True,year=thisyear).all()
            if thisyeardivisions and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite divisions for this year?',confirm=True)

            # user has agreed to overwrite any divisions -- assume all are obsolete until overwritten
            obsoletedivisions = {}
            for division in thisyeardivisions:
                obsoletedivisions[(division.seriesid,division.divisionlow,division.divisionhigh)] = division
            
            # copy each entry from "copyyear"
            for division in Divisions.query.filter_by(club_id=club_id,active=True,year=copyyear).all():
                series = Series.query.filter_by(club_id=club_id,active=True,year=thisyear,name=division.series.name).first()
                if series:
                    newdivision = Divisions(club_id,thisyear,series.id,division.divisionlow,division.divisionhigh)
                    racedb.insert_or_update(db.session,Divisions,newdivision,year=thisyear,club_id=club_id,
                                            seriesid=newdivision.seriesid,divisionlow=newdivision.divisionlow,divisionhigh=newdivision.divisionhigh,
                                            skipcolumns=['id'])
                
                # any divisions we updated is not obsolete
                if (newdivision.seriesid,newdivision.divisionlow,newdivision.divisionhigh) in obsoletedivisions:
                    obsoletedivisions.pop((newdivision.seriesid,newdivision.divisionlow,newdivision.divisionhigh))
                    
            # remove obsolete divisions
            for (seriesid,divisionlow,divisionhigh) in obsoletedivisions:
                db.session.delete(obsoletedivisions[(seriesid,divisionlow,divisionhigh)])
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/_copydivisions',view_func=AjaxCopyDivisions.as_view('_copydivisions'),methods=['POST'])
#----------------------------------------------------------------------


