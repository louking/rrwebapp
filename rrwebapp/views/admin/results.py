"""
result - result views for result results web application
==============================================================
"""

# standard
import os.path
import os
import sys
from time import time
import traceback
from urllib.parse import urlencode
from copy import copy
from re import search
from traceback import format_exc, format_exception_only
from csv import DictWriter, reader, writer
from tempfile import TemporaryDirectory
from datetime import datetime

# pypi
import flask
from flask import request, jsonify, url_for, current_app, render_template, abort
from flask.helpers import send_file
from flask_login import login_required
from flask.views import MethodView
from werkzeug.utils import secure_filename
from sqlalchemy import func, cast
from attrdict import AttrDict
from dominate.tags import a, button, div
import loutilities.renderrun as render
from loutilities import timeu, agegrade
from loutilities.filters import filtercontainerdiv, filterdiv, yadcfoption
from loutilities.tables import DataTables, ColumnDT
from loutilities.timeu import asctime
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
from requests import get as requests_get
from running.runsignup import RunSignUp

# home grown
from . import bp
from ...model import insert_or_update
from ...accesscontrol import UpdateClubDataPermission, ViewClubDataPermission, viewer_permission
from ...model import db   # this is ok because this module only runs under flask
from ...apicommon import failure_response, success_response
from ...request_helpers import addscripts, crossdomain, annotatescripts
from ...appldirs import UPLOAD_TEMP_DIR
from ...settings import productname
from ...raceresults import RaceResults, headerError, dataError, normalizeracetime
from ...clubmember import DbClubMember
from ...crudapi import CrudApi
from ...model import Runner, ManagedResult, RaceResult, Race, Exclusion, Series, Divisions, Club, dbdate
from ...model import rendertime, renderfloat, rendermember, renderlocation, renderseries
from ...resultsutils import ServiceAttributes, LocationServer, get_distance
from ...resultsutils import DIFF_CUTOFF, DISP_MATCH, DISP_CLOSE, DISP_MISSED
from ...resultsutils import ImportResults, tYmd, getrunnerchoices
from ...model import RaceResultService, ApiCredentials
from ...model import SERIES_OPTION_PROPORTIONAL_SCORING
from ...datatables_utils import DataTablesEditor, dt_editor_response, get_request_action, get_request_data
from ...forms import SeriesResultForm
from ...tasks import importresultstask

# support age grade
ag = agegrade.AgeGrade(agegradewb='config/wavacalc15.xls')

class BooleanError(Exception): pass
class ParameterError(Exception): pass

dbdate = asctime('%Y-%m-%d')

def getmembertype(runnerid):
    '''
    determine member type based on runner field values
    
    :param runnerid: runnerid or None
    
    :rtype: 'member', 'inactive', 'nonmember', ''
    '''
    
    runner = Runner.query.filter_by(id=runnerid).first()

    if not runner:
        return 'nonmember'
    
    elif runner.member:
        if runner.active:
            return 'member'
    
        else:
            return 'inactive'
        
    else:
        return 'nonmember'


class FixupResult():

    def __init__(self, race, pool, result, timeprecision):
        '''
        fix up result
        
        fix up the following:
          * time gets converted from seconds
          * determine member matching, set runnerid choices and initially selected choice
          * based on matching, set disposition

        :param race: race record
        :param pool: pool from which candidates come from
        :param result: record from runner table or None
        :param timeprecision: precision for time rendering
        
        :rtype: runner, time, disposition, runnerchoice, runnerid
        '''

        self.result = result
        club_id = flask.session['club_id']

        # make time renderable
        self.time = render.rendertime(result.time,timeprecision)

        # get choices for this result
        self.runnerchoice = getrunnerchoices(club_id, race, pool, result)

    def renderable_result(self):
        # make renderable result
        # include all the metadata for this result
        return {
            'id' : self.result.id,
            'place' : self.result.place,
            'resultname' : self.result.name,
            'gender' : self.result.gender,
            'age' : self.result.age,
            'disposition' : self.result.initialdisposition,
            'confirm' : self.result.confirmed,
            'runnerid' : self.result.runnerid,
            'hometown' : self.result.hometown,
            'club' : self.result.club,
            'time' : self.time,
        }


class EditParticipants(MethodView):
    decorators = [login_required]
    def get(self,raceid):
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            # TODO: maybe readcheck is ok, but javascript needs to be reviewed carefully
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' not found for this club".format(race.name)
                current_app.logger.error(cause)
                flask.flash(cause)
                return flask.redirect(url_for('manageraces'))

            # active is ClubMember object for active members; if race isn't for members only nonmember is ClubMember object for nonmembers
            membersonly = race.series[0].membersonly
            if membersonly:
                pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

            # convert members for page select
            memberrecs = pool.getmembers()
            membernames = []
            memberages = {}
            memberagegens = {}
            for thismembername in memberrecs:
                # get names and ages associated with each name
                for thismember in memberrecs[thismembername]:
                    racedate = tYmd.asc2dt(race.date)
                    try:
                        dob = tYmd.asc2dt(thismember['dob'])
                        age = timeu.age(racedate,dob)
                        nameage = '{} ({})'.format(thismember['name'], age)
                    # maybe no dob
                    except ValueError:
                        age = ''    
                        nameage = thismember['name']

                    # memberages is used for picklist on missed and similar dispositions
                    memberages[thismember['id']] = nameage

                    # set up to retrieve age, gender for this member
                    memberagegens.setdefault(thismembername,[])
                    memberagegens[thismembername].append({'age': age, 'gender':thismember['gender']})

                    # note only want to save the names for use on the name select
                    # annotate for easy sort
                    # TODO: is this an issue if two with the same name have different capitalization?
                    thismemberoption = {'label':thismember['name'],'value':thismember['name']}
                    if thismemberoption not in membernames:
                        membernames.append(thismemberoption)

            # sort membernames
            membernames.sort(key=lambda i: i['label'].lower())

            # start with empty data
            tabledata = []
            tableselects = {}

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('editparticipants.html', 
                                         race=race, 
                                         data=url_for('._editparticipants',raceid=raceid), 
                                         selects=tableselects,
                                         membernames=membernames, 
                                         memberages=memberages, 
                                         memberagegens=memberagegens,
                                         crudapi=url_for('._editparticipantscrud',raceid=0)[0:-1],  
                                         fieldapi=url_for('._updatemanagedresult',resultid=0)[0:-1],
                                         membersonly=membersonly, 
                                         inhibityear=True,inhibitclub=True,
                                         pagejsfiles=annotatescripts(['editparticipants.js']),
                                         writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/editparticipants/<int:raceid>',view_func=EditParticipants.as_view('editparticipants'),methods=['GET'])


class AjaxEditParticipants(MethodView):
    def get(self,raceid):
        try:

            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id) 
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            # TODO: maybe readcheck is ok, but javascript needs to be reviewed carefully
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # determine precision for rendered output, race is needed to fix up result as well
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
            
            # mData must match columns in RaceResults[.js].editparticipants
            columns = [
                ColumnDT(ManagedResult.id,                 mData='id',          search_method='none'),
                ColumnDT(ManagedResult.place,              mData='place'),
                ColumnDT(ManagedResult.name,               mData='resultname'),
                ColumnDT(ManagedResult.gender,             mData='gender',      search_method='none'),
                ColumnDT(ManagedResult.age,                mData='age',         search_method='none'),
                ColumnDT(ManagedResult.initialdisposition, mData='disposition', search_method='yadcf_multi_select'),

                # ColumnDT(rendermember(Runner.member), mData='membertype', search_method='none'),
                ColumnDT(rendermember(ManagedResult.runnerid), mData='membertype', search_method='none'),

                # the odd confirmed lambda filter prevents a string 'True' or 'False' from being sent
                ColumnDT(ManagedResult.confirmed,           mData='confirm',            search_method='none'),
                ColumnDT(ManagedResult.runnerid,            mData='runnerid'),
                # next two, suppress 'None' rendering
                ColumnDT(ManagedResult.hometown,            mData='hometown'),
                ColumnDT(ManagedResult.club,                mData='club'),
                ColumnDT(rendertime(ManagedResult.time), mData='time'),
            ]

            def set_yadcf_data():
                getcol = lambda colname: [col.mData for col in columns].index(colname)

                # add yadcf filter
                matches = [row.initialdisposition for row in db.session.query(ManagedResult.initialdisposition)
                    .filter_by(club_id=club_id, raceid=raceid).distinct().all()]
                yadcf_data = [('yadcf_data_{}'.format(getcol('disposition')), matches)]

                return yadcf_data

            params = request.args.to_dict()
            query = db.session.query().select_from(ManagedResult).filter_by(club_id=club_id,raceid=raceid)
            rowTable = DataTables(params, query, columns, set_yadcf_data=set_yadcf_data)

            # prepare for match filter
            # need to use db.session to access query function
            # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
            # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
            # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
            # format depends on type of select

            # add to returned output
            output_result = rowTable.output_result()

            # determine if race is for members only
            # then get appropriate pool of runners for possible inclusion in tableselects
            membersonly = race.series[0].membersonly
            if membersonly:
                pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id,member=True,active=True)
            else:
                pool = DbClubMember(cutoff=DIFF_CUTOFF,club_id=club_id)

            # determine possible choices for this runner if not definite
            tableselects = {}
            for result in output_result['data']:
                # use select field unless 'definite', or membersonly and '' (means definitely didn't find)
                r = AttrDict(result)    # for convenience because getrunnerchoices assumes object not dict
                if writecheck.can() and ((r.disposition == DISP_MISSED or r.disposition == DISP_CLOSE) 
                                         or (not membersonly and r.disposition != DISP_MATCH)):
                    tableselects[r.id] = getrunnerchoices(club_id, race, pool, r)

            # add standings name selects and names
            output_result['tableselects'] = tableselects

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/_editparticipants/<int:raceid>',view_func=AjaxEditParticipants.as_view('_editparticipants'),methods=['GET'])


class AjaxEditParticipantsCRUD(MethodView):
    decorators = [login_required]
    formfields = 'age,club,confirm,disposition,gender,hometown,id,place,resultname,runnerid,time'.split(',')
    dbfields   = 'age,club,confirmed,initialdisposition,gender,hometown,id,place,name,runnerid,time'.split(',')

    def post(self, raceid):
        # prepare for possible errors
        error = ''
        fielderrors = []

        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                cause = 'operation not permitted for user'
                return dt_editor_response(error=cause)
            
            # handle create, edit, remove
            action = get_request_action(request.form)

            # get data from form
            data = get_request_data(request.form)
            current_app.logger.debug('action={}, data={}, form={}'.format(action, data, request.form))

            if action not in ['create','edit','remove']:
                db.session.rollback()
                cause = 'unknown action "{}"'.format(action)
                current_app.logger.warning(cause)
                return dt_editor_response(error=cause)

            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if not race:
                db.session.rollback()
                cause = 'race id={} does not exist for this club'.format(raceid)
                current_app.logger.warning(cause)
                return dt_editor_response(error=cause)

            if len(race.series) == 0:
                db.session.rollback()
                cause =  'Race needs to be included in at least one series to import results'
                current_app.logger.error(cause)
                return dt_editor_response(error=cause)
            
            # determine precision for time output
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)

            # dataTables Editor helper
            dbmapping = dict(list(zip(self.dbfields,self.formfields)))
            dbmapping['time']     = lambda inrow: normalizeracetime(inrow['time'], race.distance)

            formmapping = dict(list(zip(self.formfields,self.dbfields)))
            formmapping['time'] = lambda dbrow: render.rendertime(dbrow.time,timeprecision)
            formmapping['membertype'] = lambda dbrow: getmembertype(dbrow.runnerid)

            # prepare to import results to database
            importresults = ImportResults(club_id, raceid, dbmapping)

            # prepare to send database results to browser
            # dbmapping is not needed for this
            dte = DataTablesEditor({}, formmapping)
            
            # loop through data, determining best match
            responsedata = []
            runnerchoices = {}
            for resultid in data:
                thisdata = data[resultid]
                # create of update
                if action!='remove':
                    # check gender
                    if thisdata['gender'].upper() not in ['M','F']:
                        fielderrors.append({'name' : 'gender', 'status' : 'Gender must be chosen'})

                    # check for hh:mm:ss time field error
                    try:
                        dbtime = timeu.timesecs(thisdata['time'])
                    except ValueError:
                        fielderrors.append({'name' : 'time', 'status' : 'Time must be in format [hh:]mm:ss'})

                    # verify age is a number
                    try:
                        age = int(thisdata['age'])
                    except:
                        fielderrors.append({'name' : 'age', 'status' : 'Age must be a number'})

                    # get or create database entry
                    if action=='edit':
                        dbresult = ManagedResult.query.filter_by(id=resultid).first()
                    # create
                    else:
                        dbresult = ManagedResult(club_id,race.id)
                    
                    # fill in the data from the form
                    runner_choices = importresults.update_dbresult(thisdata, dbresult)

                    # save the new result to force dbresult.id assignment
                    if action=='create':
                        db.session.add(dbresult)
                        db.session.flush()  # needed to update id

                    # set up response object
                    thisrow = dte.get_response_data(dbresult)
                    responsedata.append(thisrow)
                    current_app.logger.debug('thisrow={}'.format(thisrow))

                    # update thisresult.runnerchoice for resultid
                    runnerchoices[dbresult.id] = runner_choices
                    current_app.logger.debug('resultid={} runnerchoices={}'.format(dbresult.id, runner_choices))

                # remove
                else:
                    resultid = thisdata['id']
                    dbresult = ManagedResult.query.filter_by(id=resultid).first()
                    current_app.logger.debug('deleting id={}, name={}'.format(resultid,dbresult.name))
                    db.session.delete(dbresult)

            # commit database updates and close transaction
            db.session.commit()
            return dt_editor_response(data=responsedata, choices=runnerchoices)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            if fielderrors:
                cause = 'please check indicated fields'
            elif error:
                cause = error
            else:
                cause = traceback.format_exc()
                current_app.logger.error(traceback.format_exc())
            return dt_editor_response(data=[], error=cause, fieldErrors=fielderrors)

bp.add_url_rule('/_editparticipantscrud/<int:raceid>',view_func=AjaxEditParticipantsCRUD.as_view('_editparticipantscrud'),methods=['POST'])

###########################################################################################
# editexclusions endpoint
###########################################################################################

editexclusions_dbattrs = 'id,club_id,foundname,runner'.split(',')
editexclusions_formfields = 'rowid,club_id,foundname,runner'.split(',')
editexclusions_dbmapping = dict(list(zip(editexclusions_dbattrs, editexclusions_formfields)))
editexclusions_formmapping = dict(list(zip(editexclusions_formfields, editexclusions_dbattrs)))

editexclusions = CrudApi(
    app=bp,
    pagename='edit exclusions',
    endpoint='admin.editexclusions',
    rule='/editexclusions',
    dbmapping=editexclusions_dbmapping,
    formmapping=editexclusions_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable=Exclusion,
    clientcolumns=[
        {'data': 'foundname', 'name': 'foundname', 'label': 'Result Name',
            },
        {'data': 'runner', 'name': 'runner', 'label': 'Member Name', 'type': 'select2',
            '_treatment': {'relationship':
                {
                    'dbfield': 'runner',
                    'fieldmodel': Runner,
                    'labelfield': 'name',
                    'formfield': 'runner',
                    'uselist': False,
                    'queryparams': lambda: {'club_id': flask.session['club_id']}
                }
            },
            },
    ],
    serverside=False,
    byclub=True,
    addltemplateargs={'inhibityear': True},
    idSrc='rowid',
    buttons=['remove', 'csv',
                ],
    )
editexclusions.register()


#######################################################################
# following functions used to set up pretablehtml
#######################################################################

def indent(elem, level=0):
# in-place prettyprint formatter
# see http://effbot.org/zone/element-lib.htm#prettyprint
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class RunnerResults(MethodView):

    def get(self):
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)
            # NOTE: session variables are updated in nav.py

            # filter on valid runnerid, if present
            resultfilter = {}
            name = None
            pagename = 'Results'
            if runnerid:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    resultfilter['runnerid'] = runnerid
                    name = runner.name
                    pagename = '{} Results'.format(name)

            # limit results to those recorded by rrwebapp
            resultfilter['source'] = productname()

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [
                    { 'data': 'name',           'name': 'name',             'label': 'Name' },
                    { 'data': 'series',         'name': 'series',           'label': 'Series' }, 
                    { 'data': 'date',           'name': 'date',             'label': 'Date',        'className': 'dt-body-center' },
                    { 'data': 'race',           'name': 'race',             'label': 'Race'},
                    { 'data': 'miles',          'name': 'miles',            'label': 'Miles',       'className': 'dt-body-center' },
                    { 'data': 'gender',         'name': 'gender',           'label': 'Gen',         'className': 'dt-body-center' },
                    { 'data': 'age',            'name': 'age',              'label': 'Age',         'className': 'dt-body-center' },
                    { 'data': 'genderplace',    'name': 'genderplace',      'label': 'Gen Place',   'className': 'dt-body-center' },
                    { 'data': 'division',       'name': 'division',         'label': 'Div',         'className': 'dt-body-center' },
                    { 'data': 'divisionplace',  'name': 'divisionplace',    'label': 'Div Place',   'className': 'dt-body-center' },
                    { 'data': 'time',           'name': 'time',             'label': 'Time',        'className': 'dt-body-center' },
                    { 'data': 'pace',           'name': 'pace',             'label': 'Pace',        'className': 'dt-body-center' },
                    { 'data': 'agtime',         'name': 'agtime',           'label': 'AG Time',     'className': 'dt-body-center' },
                    { 'data': 'agpercent',      'name': 'agpercent',        'label': 'AG %age',     'className': 'dt-body-center' },
                ],
                'ordering': True,
                'serverSide': True,
                'order': [[0,'asc']],
                # 'search' : { 'regex' : True },   # to test sqlalchemy-datatables global search feature
            }

            buttons = [ 'csv' ]

            # no external filters if a runner was specified
            if runnerid:
                pretablehtml = ''
                options = {'dtopts': dt_options}

            # no runner was specified, yes we should be filtering
            else:
                pretablehtml = '''
                    <div class="TextLeft W7emLabel">
                      <div>
                        <label class="Label">Name:</label><span id="_rrwebapp_filtername" class="_rrwebapp-filter"></span>
                        <label class="Label">Series:</label><span id="_rrwebapp_filterseries" class="_rrwebapp-filter"></span>
                        <label class="Label">Gender:</label><span id="_rrwebapp_filtergender" class="_rrwebapp-filter"></span>
                      </div>
                    </div>
                '''
                # set up yadcf
                getcol = lambda name: [col['name'] for col in dt_options['columns']].index(name)
                yadcf_options = [
                    {
                        'column_selector': 'name:name',
                        'filter_container_id':"_rrwebapp_filtername",
                        'filter_type':"multi_select",
                        'select_type': 'select2',
                        'select_type_options': {
                            'width': '30em',
                        },
                        'filter_reset_button_text': 'all',
                    },{
                        'column_number':getcol('series'),
                        'filter_container_id':"_rrwebapp_filterseries",
                        'filter_reset_button_text': 'all',
                    },{
                        'column_number':getcol('gender'),
                        'filter_container_id':"_rrwebapp_filtergender",
                        'filter_reset_button_text': 'all',
                    }
                ]
                options = {'dtopts': dt_options, 'yadcfopts': yadcf_options}

          
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html',
                                         pagename=pagename,
                                         pretablehtml=pretablehtml,
                                         # serverSide must be True to pass url
                                         # add the request args to the ajax function
                                         tabledata=url_for('._results')+'?'+urlencode(request.args),
                                         tablebuttons= buttons,
                                         tablefiles=None,
                                         options = options,
                                         inhibityear=True,inhibitclub=True,
                                         )

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/results',view_func=RunnerResults.as_view('results'),methods=['GET'])

def renderage(result):
    '''
    render age string for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
    except:
        thisage = ''

    return thisage

def renderagtime(result):
    '''
    render age grade time for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
        agpercent, agtime, agfactor = ag.agegrade(thisage, result.runner.gender, result.race.distance, result.time)
        agtime = render.rendertime(agtime,0)
    except:
        agtime = ''

    return agtime

def renderagpercent(result):
    '''
    render age grade percentage for result
    any exceptions returns empty string - probably bad dateofbirth

    :param result: result from RaceResult joined with Runner, Race
    :rtype: string for rendering
    '''

    try:
        thisage = timeu.age(tYmd.asc2dt(result.race.date),tYmd.asc2dt(result.runner.dateofbirth))
        agpercent, agtime, agfactor = ag.agegrade(thisage, result.runner.gender, result.race.distance, result.time)
        agpercent = '{:.2f}%'.format(agpercent)
    except:
        agpercent = ''

    return agpercent

def renderintstr(cell):
    '''
    render int string for cell
    any exceptions returns 0

    :param cell: cell with int probably
    :rtype: int (hopefully)
    '''

    try:
        this = int(cell)
    except:
        this = 0

    return this

def rendermembertype(result):
    '''
    render membertype

    :param result: result from ManagedResult
    :rtype: string for rendering
    '''

    # if runner is indicated, find out whether runner is a member
    if result.runnerid:
        runner = Runner.query.filter_by(id=result.runnerid).first()
        if runner.member:
            this = 'member'
        else:
            this = 'nonmember'
    else:
        this = ''

    return this


class AjaxRunnerResults(MethodView):

    @crossdomain(origin='*')
    def get(self):
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)

            # filter on valid runnerid, if present
            resultfilter = []
            runnerfilter = []
            seriesfilter = []
            name = None
            pagename = 'Results'
            if runnerid:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    resultfilter.append(RaceResult.runnerid == runnerid)
                    runnerfilter.append(Runner.id == runnerid)
                    name = runner.name
                    pagename = '{} Results'.format(name)

            # filter on club, if present
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    resultfilter.append(RaceResult.club_id == club.id)
                    runnerfilter.append(Runner.club_id == club.id)
                    seriesfilter.append(Series.club_id == club.id)

            # need to filter after the fact for series, because the seriesid is different for different years
            if seriesarg:
                series = Series.query.filter_by(name=seriesarg).first()
                if series:
                    seriesfilter.append(Series.name == series.name)
                    current_app.logger.debug('filter by series {}'.format(seriesarg))

            # limit results to that recorded by rrwebapp
            resultfilter.append(RaceResult.source == productname())

            columns = [
                ColumnDT(Runner.name,                mData='name'),
                ColumnDT(Series.name,                mData='series'),
                ColumnDT(Race.date,                  mData='date'),
                ColumnDT(Race.name,                  mData='race'),
                ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='none'),
                ColumnDT(Runner.gender,              mData='gender',             search_method='none'),
                ColumnDT(RaceResult.agage,           mData='age',                search_method='none'),
                ColumnDT(RaceResult.genderplace,     mData='genderplace',        search_method='none'),
                ColumnDT(func.concat(RaceResult.divisionlow, '-', RaceResult.divisionhigh), mData='division', search_method='none'),
                ColumnDT(RaceResult.divisionplace, mData='divisionplace', search_method='none'),
                ColumnDT(rendertime(RaceResult.time), mData='time', search_method='none'),
                ColumnDT(rendertime(RaceResult.time / Race.distance), mData='pace', search_method='none'),
                ColumnDT(rendertime(RaceResult.agtime), mData='agtime', search_method='none'),
                ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 1), '%'), mData='agpercent', search_method='none'),
            ]

            params = request.args.to_dict()
            query = db.session.query().select_from(RaceResult).filter(*resultfilter).join(Runner).join(Series).filter(*seriesfilter).join(Race)
            rowTable = DataTables(params, query, columns)

            # prepare for name, series and gender filter
            # need to use db.session to access query function
            # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
            # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
            # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
            # format depends on type of select
            names = [row.name for row in db.session.query(Runner.name).filter(*runnerfilter).distinct().all()]
            series = [row.name for row in db.session.query(Series.name).filter(*seriesfilter).distinct().all()]
            genders = ['M','F']

            # add yadcf filter
            getcol = lambda name: [col.mData for col in columns].index(name)
            output_result = rowTable.output_result()
            output_result['yadcf_data_{}'.format(getcol('name'))] = names
            output_result['yadcf_data_{}'.format(getcol('series'))] = series
            output_result['yadcf_data_{}'.format(getcol('gender'))] = genders

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/_results',view_func=AjaxRunnerResults.as_view('_results'),methods=['GET'])


class RunnerResultsChart(MethodView):

    def get(self):
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('participant',None)
            seriesarg = request.args.get('series',None)

            # filter on club, if present
            club_id = None
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    club_id = club.id

            elif 'club_id' in flask.session:
                club_id = flask.session['club_id']

            if club_id is not None:
                readcheck = ViewClubDataPermission(club_id)
                adminuser = readcheck.can()

            else:
                adminuser = False

            # filter on valid runnerid, if present
            resultfilter = {}
            name = None
            pagename = 'Results Analysis'

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"dt-chart-table dt-chart-tabledisplay dt-hide"<"H"lBpr>t<"F"i>>',
                'columns': [
                    { 'data': 'date',           'name': 'date',             'label': 'Date',        'className': 'dt-body-center dt-chart-nowrap'},
                    { 'data': 'runnerid',       'name': 'runnerid',         'label': 'Runner ID',   'visible': False },
                    { 'data': 'name',           'name': 'name',             'label': 'Name',        'visible': False },
                    { 'data': 'series',         'name': 'series',           'label': 'Series',      'className': 'dt-chart-nowrap' }, 
                    { 'data': 'race',           'name': 'race',             'label': 'Race',        'className': 'dt-chart-nowrap'},
                    { 'data': 'miles',          'name': 'miles',            'label': 'Miles',       'className': 'dt-body-center' },
                    { 'data': 'age',            'name': 'age',              'label': 'Age',         'className': 'dt-body-center' },
                    { 'data': 'time',           'name': 'time',             'label': 'Time',        'className': 'dt-body-center' },
                    { 'data': 'pace',           'name': 'pace',             'label': 'Pace',        'className': 'dt-body-center' },
                    { 'data': 'agtime',         'name': 'agtime',           'label': 'AG Time',     'className': 'dt-body-center' },
                    { 'data': 'agpercent',      'name': 'agpercent',        'label': 'AG %age',     'className': 'dt-body-center' },
                ],
                'language' : {
                    'emptyTable': 'no results found for current selection',
                    'zeroRecords': 'no results found for current selection',
                },
                'ordering': True,
                'serverSide': True,
                'order': [[0,'asc']],
                # NOTE: cannot use paging because we need to display all points on the chart
                'paging': False,
            }

            # some columns only available if user is logged in and has visibility to this club
            if adminuser:
                dt_options['columns'] += [
                            { 'data': 'location',    'name': 'location',      'label': 'Location'},
                            { 'data': 'source',      'name': 'source',        'label': 'Source',     'className': 'dt-body-center' },
                            { 'data': 'sourceid',    'name': 'sourceid',      'label': 'Source ID',  'className': 'dt-body-center' },
                        ]

            # set up pretablehtml
            pretable = div(_class='TextLeft PL20pxLabel')
            with pretable:
                filterlines = filtercontainerdiv()
                with filterlines:
                    button('table', _class='dt-chart-display-button', _type='button')
                    filterdiv('_rrwebapp_filtername', 'Name (age):')
                    filterdiv('_rrwebapp_filterseries', 'Series:')
                    filterdiv('_rrwebapp_filterdate', 'Date (yyyy-mm-dd):')
                    filterdiv('_rrwebapp_filterdistance', 'Dist (miles):')
                    filterdiv('_rrwebapp_filteragpercent', 'Age Grade %age:')
                    if adminuser:
                        filterdiv('_rrwebapp_filtersource', 'Source:')
                        filterdiv('_rrwebapp_filtersourceid', 'Source ID:')
                    # this seems a bit unnecessary
                    # a('learn about age grading', href='https://usatfmasters.org/wp/2018/08/age-grading/', target='_blank', _class='dt-chart-age-grade-link')
                    div(id='progressbar')

            ## render the html 
            pretablehtml = pretable.render()

            # set up yadcf
            getcol = lambda name: [col['name'] for col in dt_options['columns']].index(name)
            filterdelay = 500
            yadcf_options = [
                {
                    'column_selector': 'runnerid:name',
                    'filter_container_id':"_rrwebapp_filtername",
                    'filter_type':"select",
                    'select_type': 'select2',
                    'filter_reset_button_text': 'clear',
                    'sort_as': 'none',
                    'select_type_options': {
                        'width': '200px',
                    },
                },{
                    'column_selector': 'date:name',
                    'filter_container_id':"_rrwebapp_filterdate",
                    'filter_type':'range_date',
                    'date_format':'yyyy-mm-dd',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_selector': 'miles:name',
                    'filter_container_id':"_rrwebapp_filterdistance",
                    'filter_type': 'range_number',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_selector': 'agpercent:name',
                    'filter_container_id':"_rrwebapp_filteragpercent",
                    'filter_type': 'range_number',
                    'filter_delay': filterdelay,
                    'filter_reset_button_text': 'all',
                },{
                    'column_selector': 'series:name',
                    'filter_container_id':"_rrwebapp_filterseries",
                    'filter_reset_button_text': 'all',
                    'filter_type': "select",
                    'select_type': 'select2',
                    'select_type_options': {
                        'width': '150px',
                    },
                }
            ]

            # add admin columns
            if adminuser:
                yadcf_options += [
                    {
                        'column_selector': 'source:name',
                        'filter_container_id':"_rrwebapp_filtersource",
                        'filter_type':"select",
                        'select_type': 'select2',
                        'filter_reset_button_text': 'all',
                    },{
                        'column_selector': 'sourceid:name',
                        'filter_container_id':"_rrwebapp_filtersourceid",
                        'filter_type':'select',
                        'select_type': 'select2',
                        'filter_reset_button_text': 'all',
                    },
                ]
            options = {'dtopts': dt_options, 'yadcfopts': yadcf_options}

            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html',
                                         pagename=pagename,
                                         pretablehtml=pretablehtml,
                                         chartloc='beforetable',
                                         pagejsfiles=addscripts(['dt_chart.js', 'd3.legend.js', 'results_scatterplot.js']),
                                         pagecssfiles=addscripts(['d3.legend.css', 'dt_chart.css']),
                                         # serverSide must be True to pass url
                                         # add the request args to the ajax function
                                         tabledata=url_for('._resultschart')+'?'+urlencode(request.args),
                                         tablebuttons= ['csv'],
                                         tablefiles=None,
                                         options = options,
                                         inhibityear=True,inhibitclub=True,
                                         )

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

bp.add_url_rule('/resultschart',view_func=RunnerResultsChart.as_view('resultschart'),methods=['GET'])


class AjaxRunnerResultsChart(MethodView):

    def get(self):
        try:
            club_shname = request.args.get('club',None)
            runnerid = request.args.get('runnerid',None)
            seriesarg = request.args.get('series',None)
            datefromarg = request.args.get('begindate','')
            datetoarg = request.args.get('enddate','')

            # filter on valid runnerid, if present
            namesfilter = {'member':True, 'active':True}   # only support active members because this means dateofbirth is known
            resultfilter = {}
            seriesfilter = {}
            name = None
            pagename = 'Results'

            # filter on club, if present
            club_id =None
            club = None         # should fix #344
            if club_shname:
                club = Club.query.filter_by(shname=club_shname).first()
                if club:
                    namesfilter['club_id'] = club.id
                    resultfilter['club_id'] = club.id
                    club_id = club.id

            elif 'club_id' in flask.session:
                club_id = flask.session['club_id']
                club = Club.query.filter_by(id=club_id).first()

            if club_id is not None:
                readcheck = ViewClubDataPermission(club_id)
                adminuser = readcheck.can()

            else:
                adminuser = False


            # if not admin, limit source to rrwebapp product name
            if not adminuser:
                resultfilter['source'] = productname()

            getcol = lambda name: [col.mData for col in columns].index(name)

            # create columns dynamically because full results have seriesid = None, and this returns empty list
            ## trick here is to to the following when series is not filtered
            ##    retrieve seriesid and do not join('series') [filter disabled]
            ## otherwise
            ##    retrieve series.name and join('series') [filter enabled]
            columns = [
                ColumnDT(Race.date, mData='date', search_method='yadcf_range_date'),
                ColumnDT(RaceResult.runnerid, mData='runnerid', search_method='numeric'),
                ColumnDT(Runner.name, mData='name'),
                ColumnDT(renderseries(RaceResult.seriesid), mData='series', search_method='none'),
            ]

            # set up columns differently if series is being searched for, as if so it's ok to join('series') in query
            seriesfield = 'columns[{}][search][value]'.format(getcol('series'))
            seriessearch = request.args.get(seriesfield, None)
            if seriesarg or seriessearch:
                # give preference to seriesarg
                seriesname = seriesarg or seriessearch

                if club_shname:
                    seriesfilter['club_id'] = club.id

                # pop the last element (mData='series') off the end, as we're replacing it
                columns.pop()
                columns += [
                    ColumnDT(Series.name,        mData='series'),
                ]

            columns += [
                ColumnDT(Race.name, mData='race', search_method='none'),
                ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='yadcf_range_number'),
                # ColumnDT(renderfloat(Race.distance, 2), mData='miles', search_method='none'),
                ColumnDT(RaceResult.agage, mData='age', search_method='none'),
                ColumnDT(rendertime(RaceResult.time), mData='time', search_method='none'),
                ColumnDT(rendertime(RaceResult.time / Race.distance), mData='pace', search_method='none'),
                ColumnDT(rendertime(RaceResult.agtime), mData='agtime', search_method='none'),
                ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 2), '%'), mData='agpercent', search_method='yadcf_range_number'),
                # ColumnDT(func.concat(renderfloat(RaceResult.agpercent, 2), '%'), mData='agpercent', search_method='none'),
            ]

            # give extra columns to the admin
            if adminuser:
                columns += [
                        # ColumnDT('race.location.name',   mData='location',        search_method='none',   filter=lambda c: c if c else ' '),
                        ColumnDT(renderlocation(Race.locationid),   mData='location', search_method='none'),
                        ColumnDT(RaceResult.source,          mData='source'),
                        ColumnDT(RaceResult.sourceid,        mData='sourceid'),
                    ]

            # make copy of args as request.args is immutable and we might want to update
            args = request.args.to_dict()

            # if no search for runnerid, we return no records, expecting user to make a selection later
            # kludge this by setting resultsfilter to -1
            runneridfield = 'columns[{}][search][value]'.format(getcol('runnerid'))
            runneridsearch = args[runneridfield]
            if not runneridsearch:
                resultfilter['runnerid'] = -1

            # delimiter for string operations 
            delim = '-yadcf_delim-'

            # preprocess date range to assure proper format
            datefield = 'columns[{}][search][value]'.format(getcol('date'))
            # if min or max is missing, prepare to fill in
            nulldate = [tYmd.epoch2asc(0),tYmd.epoch2asc(time())]
            datesearch = args[datefield]
            if datesearch:
                daterange = datesearch.split(delim)
                # sure hope len(daterange) == 2
                for i in range(2):
                    if daterange[i] == '':
                        daterange[i] = nulldate[i]
                    try:
                        daterange[i] = tYmd.epoch2asc(tYmd.asc2epoch(daterange[i]))
                    # if incorrect format, act as if null
                    except ValueError:
                        daterange[i] = nulldate[i]
                args[datefield] = delim.join(daterange)

            def set_yadcf_data():
                # preprocess range for some fields to allow min only or max only
                statranges = {'miles': [0,100], 'agpercent': [0,100]}

                # prepare for page filters
                # see http://stackoverflow.com/questions/2175355/selecting-distinct-column-values-in-sqlalchemy-elixir
                # see http://stackoverflow.com/questions/22275412/sqlalchemy-return-all-distinct-column-values
                # see http://stackoverflow.com/questions/11175519/how-to-query-distinct-on-a-joined-column
                # format depends on type of select
                namesq = Runner.query.filter_by(**namesfilter)
                resultnames = [{'value': row.id, 'label': '{} ({})'.format(row.name, timeu.age(timeu.epoch2dt(time()),
                                                                                               tYmd.asc2dt(
                                                                                                   row.dateofbirth)))}
                               for row in namesq.all()]

                # only return distinct names, sorted
                names = []
                for name in resultnames:
                    if name not in names:
                        names.append(name)
                names.sort(key=lambda item: item['label'].lower())
                # current_app.logger.debug('after names sort')

                # avoid exception if club not specified in query
                if club:
                    series = [row.name for row in db.session.query(Series.name).filter_by(club_id=club.id).distinct().all()]
                else:
                    series = []

                # add yadcf filters
                yadcf_data = []
                yadcf_data.append(('yadcf_data_{}'.format(getcol('runnerid')), names))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('series')), series))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('miles')), statranges['miles']))
                yadcf_data.append(('yadcf_data_{}'.format(getcol('agpercent')), statranges['agpercent']))

                # send back yadcf_data
                return yadcf_data

            # add series filters to query
            q = db.session.query().select_from(RaceResult).filter_by(**resultfilter).join(Runner).join(Race)
            if seriesfilter:
                # q = q.join(Series).filter_by(**seriesfilter)
                q = q.join(RaceResult.series).filter_by(**seriesfilter)
            # q = q.join(Race).join(Location)
            # current_app.logger.debug('resultfilter = {}, seriesfilter = {}'.format(resultfilter, seriesfilter))
            # current_app.logger.debug('query = \n{}'.format(q))

            # note there's no paging (see RunnerResultsChart) so can do some filtering after retrieval of all results from database
            rowTable = DataTables(args, q, columns, set_yadcf_data=set_yadcf_data)
            output_result = rowTable.output_result()

            # current_app.logger.debug('after race results filtered query')

            # filter by service / maxdistance
            ## get maxdistance by service
            if adminuser:
                services = RaceResultService.query.filter_by(club_id=club_id).join(ApiCredentials).all()
                maxdistance = {}
                for service in services:
                    attrs = ServiceAttributes(club_id, service.apicredentials.name)
                    if attrs.maxdistance:
                        maxdistance[service.apicredentials.name] = attrs.maxdistance
                    else:
                        maxdistance[service.apicredentials.name] = None
                maxdistance[productname()] = None

                ## update data
                locsvr = LocationServer()
                clublocation = locsvr.getlocation(club.location)
                if 'data' in output_result:
                    rows = copy(output_result['data'])
                    output_result['data'] = []
                    for row in rows:
                        if maxdistance[row['source']]:
                            distance = get_distance(clublocation, locsvr.getlocation(row['location']))
                            if distance == None or distance > maxdistance[row['source']]: continue
                        output_result['data'].append(row)

            # add select options to admin fields source and sourceid, from runner's data
            if adminuser:
                # only fill in these selects if runner is being shown, from runner's results
                if runneridsearch:
                    sources = [row.source for row in db.session.query(RaceResult.source).filter_by(club_id=club.id, runnerid=runneridsearch).distinct().all()]
                    sourceids = [row.sourceid for row in db.session.query(RaceResult.sourceid).filter_by(club_id=club.id, runnerid=runneridsearch).distinct().all()]
                    # current_app.logger.debug('after source and source id queries')
                    output_result['yadcf_data_{}'.format(getcol('source'))] = sources
                    # output_result['yadcf_data_{}'.format(getcol('sourceid'))] = sourceids
                else:
                    output_result['yadcf_data_{}'.format(getcol('source'))] = []
                    # output_result['yadcf_data_{}'.format(getcol('sourceid'))] = []



            # initialize filters from server side, 
            # but only if we don't already have the filter
            # else there will be infinite loop
            ## for runnerid
            if runnerid and not runneridsearch:
                runner = Runner.query.filter_by(id=runnerid).first()
                if runner:
                    output_result['yadcf_default_{}'.format(getcol('runnerid'))] = runnerid
                else:
                    current_app.logger.warning('runnerid {} not found'.format(runnerid))

            ## for date
            if (datefromarg or datetoarg) and not datesearch:
                output_result['yadcf_default_{}'.format(getcol('date'))] = {'from':datefromarg, 'to':datetoarg}

            return jsonify(output_result)

        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

bp.add_url_rule('/_resultschart',view_func=AjaxRunnerResultsChart.as_view('_resultschart'),methods=['GET'])

def allowed_file(filename):
    return '.' in filename and filename.split('.')[-1] in ['xls','xlsx','txt','csv']


class AjaxImportResults(MethodView):
    decorators = [login_required]
    
    def post(self,raceid):
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            # see http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
            resultfile = request.files['file']

            # get file extention
            root,ext = os.path.splitext(resultfile.filename)
            
            # make sure valid file
            if not resultfile:
                db.session.rollback()
                cause = 'Unexpected Error: Missing file'
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            if not allowed_file(resultfile.filename):
                db.session.rollback()
                cause = 'Invalid file type {} for file {}'.format(ext,resultfile.filename)
                current_app.logger.warning(cause)
                return failure_response(cause=cause)

            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if not race:
                db.session.rollback()
                cause = 'race id={} does not exist for this club'.format(raceid)
                current_app.logger.warning(cause)
                return failure_response(cause=cause)

            if len(race.series) == 0:
                db.session.rollback()
                cause =  'Race needs to be included in at least one series to import results'
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            # do we have any results yet?  If so, make sure it is ok to overwrite them
            dbresults = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).all()

            # if some results exist, verify user wants to overwrite
            if dbresults:
                # verify overwrite
                if not request.args.get('force')=='true':
                    db.session.rollback()
                    return failure_response(cause='Overwrite results?',confirm=True)
                # force is true.  delete all the current results for this race
                else:
                    current_app.logger.debug('editparticipants overwrite started')
                    nummrdeleted = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
                    numrrdeleted = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
                    current_app.logger.debug('{} managedresults deleted; {} raceresults deleted'.format(nummrdeleted,numrrdeleted))
                    # also delete any nonmembers who do not have results, as these were most likely brought in by past version of this race
                    nonmembers = Runner.query.filter_by(club_id=club_id,member=False)
                    for nonmember in nonmembers:
                        nonmemberresults = RaceResult.query.filter_by(club_id=club_id,runnerid=nonmember.id).all()
                        nonmembemresults = ManagedResult.query.filter_by(club_id=club_id,runnerid=nonmember.id).all()
                        # current_app.logger.debug(f'nonmember={nonmember.name}/{nonmember.id} nonmemberresults={nonmemberresults} nonmembermrresults={nonmembemresults}')
                        if len(nonmemberresults) == 0 and len(nonmembemresults) == 0:
                            db.session.delete(nonmember)
                    # pick up any deletes for later processing
                    db.session.flush()
            
            # save file for import
            tempdir = UPLOAD_TEMP_DIR
            resultfilename = secure_filename(resultfile.filename)
            resultpathname = os.path.join(tempdir,resultfilename)
            if os.path.exists(resultpathname): os.remove(resultpathname)
            resultfile.save(resultpathname)            

            try:
                rr = RaceResults(resultpathname,race.distance)
                rr.close()
            
            # format not good enough
            except headerError as e:
                db.session.rollback()
                cause = '{}'.format(e)
                current_app.logger.warning(cause)
                return failure_response(cause=cause)
                
            # how did this happen?  check allowed_file() for bugs
            except dataError as e:
                db.session.rollback()
                cause =  'Program Error: {}'.format(e)
                current_app.logger.error(cause)
                return failure_response(cause=cause)

            # start task to import results
            task = importresultstask.apply_async((club_id, raceid, resultpathname))
            
            # commit database updates and close transaction
            db.session.commit()
            return jsonify({'success': True, 'current': 0, 'total':100, 'location': url_for('.importresultsstatus', task_id=task.id)}), 202, {}
            #return success_response(redirect=url_for('.editparticipants',raceid=raceid))
        
        except Exception as e:
            # close rr if created, otherwise NOP
            try:
                rr.close()
            except UnboundLocalError:
                pass
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)

bp.add_url_rule('/_importresults/<int:raceid>',view_func=AjaxImportResults.as_view('_importresults'),methods=['POST'])


class ImportResultsStatus(MethodView):

    def get(self, task_id):
        task = importresultstask.AsyncResult(task_id)
        current_app.logger.debug(f'task.state: {task.state}, task.info {task.info}')

        if task.state == 'PENDING':
            # job did not start yet
            response = {
                'state': task.state,
                'current': 0,
                'total': 100,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            
            # task is finished, check for traceback, which indicates an error occurred
            if task.state == 'SUCCESS':
                # check for traceback, which indicates an error occurred
                response['cause'] = task.info.get('traceback','')
                if response['cause'] == '':
                    response['redirect'] = url_for('.editparticipants',raceid=task.info.get('raceid'))
                try:
                    task.forget()
                except NotImplementedError:
                    # some backends don't implement forget
                    pass

        # doesn't seem like this can happen, but just in case
        else:
            # something went wrong in the background job
            response = {
                'state': task.state,
                'current': 100,
                'total': 100,
                'cause': str(task.info),  # this is the exception raised
            }
        return jsonify(response)

bp.add_url_rule('/importresultsstatus/<task_id>',view_func=ImportResultsStatus.as_view('importresultsstatus'), methods=['GET',])


class AjaxUpdateManagedResult(MethodView):
    decorators = [login_required]
    
    def post(self,resultid):
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # make sure result exists
            result = ManagedResult.query.filter_by(club_id=club_id,id=resultid).first()
            if not result:
                db.session.rollback()
                cause = 'Unexpected Error: result id {} not found'.format(resultid)
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            # which field changed?  if not allowed, return failure response
            field = flask.request.args.get('field','[not supplied]')
            if field not in ['runnerid','confirmed']:
                db.session.rollback()
                cause = 'Unexpected Error: field {} not supported'.format(field)
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            # is value ok? if not allowed, return failure response
            value = flask.request.args.get('value','')
            if value == '':
                db.session.rollback()
                cause = 'Unexpected Error: value must be supplied'
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            # handle argmuments provided if nonmember is to be added or removed from runner table
            # note: (newname,newgen) and (removeid) are mutually exclusive
            newname  = flask.request.args.get('newname',None)
            newgen   = flask.request.args.get('newgen',None)
            removeid = flask.request.args.get('removeid',None)
            if newgen and (newgen not in ['M','F'] or not newname):
                db.session.rollback()
                cause = 'Unexpected Error: invalid gender'
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            # verify exclusivity of newname and removeid
            # let exception handler catch if removeid not an integer
            if removeid:
                if newname:
                    db.session.rollback()
                    cause = 'Unexpected Error: cannot have newname and removeid in same request'
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)
                removeid = int(removeid)
            
            # try to make update, handle exception
            try:
                # maybe response needs arguments
                respargs = {}
                
                #current_app.logger.debug("field='{}', value='{}'".format(field,value))
                if field == 'runnerid':
                    # newname present means that this name is a new nonmember to be put in the database
                    if newname:
                        # the admin has already decided this is a new entry, based on the possiblities offered (see clubmember.ClubMember.findmember)
                        # estimate this non-member's birth date to be date of race in the year indicated by age
                        racedatedt = dbdate.asc2dt(result.race.date)
                        dobdt = datetime(racedatedt.year-result.age, racedatedt.month, racedatedt.day)

                        runner = Runner(
                            club_id, 
                            name=newname, 
                            gender=newgen, 
                            member=False, 
                            dateofbirth=dbdate.dt2asc(dobdt), 
                            estdateofbirth=True
                        )
                        
                        db.session.add(runner)
                        db.session.flush()

                        respargs['action'] = 'newname'
                        respargs['actionsuccess'] = True
                        respargs['id'] = runner.id
                        respargs['name'] = runner.name
                        value = runner.id
                        current_app.logger.debug('new member value={}'.format(value))
                    
                    # removeid present means that this id should be removed from the database, if possible
                    if removeid:
                        runner = Runner.query.filter_by(club_id=club_id,id=removeid).first()
                        if not runner:
                            db.session.rollback()
                            cause = 'Unexpected Error: member with id={} not found for club'.format(removeid)
                            current_app.logger.error(cause)
                            return failure_response(cause=cause)
                            
                        # make sure no results for member
                        results = RaceResult.query.filter_by(club_id=club_id,runnerid=removeid).all()
                        if len(results) == 0:
                            # no results, ok to remove member
                            db.session.delete(runner)
                            respargs['action'] = 'removeid'
                            respargs['id'] = removeid
                            respargs['name'] = runner.name
                            respargs['actionsuccess'] = True
                        else:
                            #respargs['action'] = 'removeid'
                            #respargs['actionsuccess'] = False
                            #respargs['removefailcause'] = 'Could not remove id={}.  Had results'.format(removeid)
                            db.session.rollback()
                            cause = 'Unexpected Error: Could not remove id={}.  Had results'.format(removeid)
                            current_app.logger.error(cause)
                            return failure_response(cause=cause)

                    if value != 'None':
                        result.runnerid = int(value)

                        # may have to update dob if nonmember, and this race is earlier in the year than previous races
                        runner = Runner.query.filter_by(id=result.runnerid).one()
                        if not runner.member:
                            # estimate this non-member's birth date to be date of race in the year indicated by age
                            racedatedt = dbdate.asc2dt(result.race.date)
                            dobdt = datetime(racedatedt.year-result.age, racedatedt.month, racedatedt.day)
                            # this assumes previously recorded age was correct, probably ok for most series
                            if not runner.dateofbirth or dobdt < dbdate.asc2dt(runner.dateofbirth):
                                # handle legacy entries which may need to indicate dob is estimate
                                runner.estdateofbirth = True
                                runner.dateofbirth = dbdate.dt2asc(dobdt)

                    else:
                        result.runnerid = None

                elif field == 'confirmed':
                    if value in ['true','false']:
                        result.confirmed = (value == 'true')
                    else:
                        raise BooleanError("invalid literal for boolean: '{}'".format(value))
                else:
                    pass    # this was handled above
                
                # handle exclusions
                # if user is confirming, items get *added* to exclusions table
                # however, if user is removing confirmation, items get *removed* from exclusions table
                exclude = flask.request.args.get('exclude')
                include = flask.request.args.get('include')
                # remove included entry from exclusions, add excluded entries
                if include:
                    #current_app.logger.debug("include='{}'".format(include))
                    if include not in ['None','new']:
                        incl = Exclusion.query.filter_by(club_id=club_id,foundname=result.name,runnerid=int(include)).first()
                        if incl:
                            # not excluded from future results any more
                            db.session.delete(incl)
                
                # exclude contains a list of runnerids which should be excluded
                if exclude:
                    #current_app.logger.debug("exclude='{}'".format(exclude))
                    exclude = eval(exclude) 
                    for thisexcludeid in exclude:
                        # None might get passed in as well as runnerids, so skip that item
                        if thisexcludeid in ['None','new']: continue
                        thisexcludeid = int(thisexcludeid)
                        excl = Exclusion.query.filter_by(club_id=club_id,foundname=result.name,runnerid=thisexcludeid).first()
                        # user is confirming entry -- if not already in table, add exclusion
                        if result.confirmed and not excl:
                            # now excluded from future results
                            newexclusion = Exclusion(
                                club_id=club_id,
                                foundname=result.name,
                                runnerid=thisexcludeid
                            )
                            db.session.add(newexclusion)
                        # user is removing confirmation -- if exclusion exists, remove it
                        elif not result.confirmed and excl:
                            db.session.delete(excl)
                        

                    
            except Exception as e:
                db.session.rollback()
                cause = "Unexpected Error: value '{}' not allowed for field {}, {}".format(value,field,e)
                current_app.logger.error(traceback.format_exc())
                return failure_response(cause=cause)
                
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response(**respargs)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)

bp.add_url_rule('/_updatemanagedresult/<int:resultid>',view_func=AjaxUpdateManagedResult.as_view('_updatemanagedresult'),methods=['POST'])


class AjaxTabulateResults(MethodView):
    decorators = [login_required]

    def post(self,raceid):
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can at least read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                flask.abort(403)
                
            # do we have any series results yet?  If so, make sure it is ok to overwrite them
            dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).all()

            # if some results exist, verify user wants to overwrite
            if dbresults:
                # verify overwrite
                if not request.args.get('force')=='true':
                    db.session.rollback()
                    return failure_response(cause='Overwrite results?',confirm=True)
                # force is true.  delete all the current results for this race
                else:
                    numdeleted = RaceResult.query.filter_by(club_id=club_id,raceid=raceid).delete()
    
            # # get all the results, and the race record
            # results = []
            # results = ManagedResult.query.filter_by(club_id=club_id,raceid=raceid).order_by('overallplace').all()

            # get race and list of runners who should be included in this race, based on membersonly
            race = Race.query.filter_by(club_id=club_id,id=raceid).first()
            if len(race.series) == 0:
                db.session.rollback()
                cause =  "Race '{}' is not included in any series".format(race.name)
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            
            # need race date division date later for age calculation
            racedate = dbdate.asc2dt(race.date)

            # get precision for time rendering
            timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)

            # for each series for this race - 'series' describes how to tabulate the results
            theseseries = race.series
            for series in theseseries:
                # get divisions for this series, if appropriate
                if series.divisions:
                    alldivs = Divisions.query.filter_by(club_id=club_id,seriesid=series.id,active=True).all()
                    
                    if len(alldivs) == 0:
                        cause = "Series '{0}' indicates divisions to be calculated, but no divisions found".format(series.name)
                        db.session.rollback()
                        current_app.logger.error(cause)
                        return failure_response(cause=cause)
                    
                    divisions = []
                    for div in alldivs:
                        divisions.append((div.divisionlow,div.divisionhigh))

                # collect results from database
                # NOTE: filter() method requires fully qualified field names (e.g., *ManagedResult.*club_id)
                results = ManagedResult.query.filter(ManagedResult.club_id==club_id, ManagedResult.raceid==race.id, ManagedResult.runnerid!=None).order_by('time').all()
                
                # loop through result entries, collecting overall, bygender, division and agegrade results
                for thisresult in results:
                    # get runner information
                    runner = Runner.query.filter_by(club_id=club_id,id=thisresult.runnerid).first()
                    runnerid = runner.id
                    gender = runner.gender
            
                    # we don't have dateofbirth for non-members
                    if runner.dateofbirth:
                        try:
                            dob = dbdate.asc2dt(runner.dateofbirth)
                        except ValueError:
                            dob = None      # should not really happen, but this runner does not get division placement
                    else:
                        dob = None
            
                    # set agegrade age (race date based)
                    # set division age (based on Jan 1 if we know dob, based on earliest race this year if we don't)
                    if dob:
                        agegradeage = timeu.age(racedate,dob)
                        # if we know dob, date for division's age calculation is Jan 1 of year race was run
                        if not runner.estdateofbirth:
                            divdate = racedate.replace(month=1,day=1)
                            divage = timeu.age(divdate, dob)
                        
                        # if we have estimated dob, date for division's age calculation is earliest race run this year by this runner
                        else:
                            results = ManagedResult.query.filter_by(runnerid=runner.id).join(Race).order_by(Race.date.desc()).all()
                            divdate = racedate
                            for divresult in results:
                                resultdate = dbdate.asc2dt(divresult.race.date)
                                if racedate.year > resultdate.year: break
                                if resultdate < divdate:
                                    divdate = resultdate
                            divage = timeu.age(divdate, dob)

                    else:
                        try:
                            agegradeage = int(thisresult.age)
                        except:
                            agegradeage = None
                        divage = None
            
                    # at this point, there should always be a runnerid in the database, even if non-member
                    # create RaceResult entry
                    # save overallplace for possible sort later (series.orderby)
                    resulttime = thisresult.time
                    raceresult = RaceResult(club_id, runnerid, race.id, series.id, resulttime, gender, agegradeage, overallplace=thisresult.place)

                    # set source fields
                    raceresult.source = productname()
                    raceresult.sourceid = runnerid
            
                    # always add age grade to result if we know the age
                    # we will decide whether to render, later based on series.agegrade, in another script
                    if agegradeage:
                        timeprecision,agtimeprecision = render.getprecision(race.distance,surface=race.surface)
                        adjtime = render.adjusttime(resulttime,timeprecision)    # ceiling for adjtime
                        raceresult.agpercent,raceresult.agtime,raceresult.agfactor = ag.agegrade(agegradeage,gender,race.distance,adjtime)
            
                    if series.divisions:
                        # member's age to determine division is the member's age on Jan 1
                        # if member doesn't give date of birth for membership list, member is not eligible for division awards
                        # if non-member, also no division awards, because age as of Jan 1 is not known
                        age = divage    # None if not available
                        if age:
                            # linear search for correct division
                            for thisdiv in divisions:
                                divlow = thisdiv[0]
                                divhigh = thisdiv[1]
                                if age in range(divlow,divhigh+1):
                                    raceresult.divisionlow = divlow
                                    raceresult.divisionhigh = divhigh
                                    break
            
                    # make result persistent
                    db.session.add(raceresult)
                
                # flush the results so they show up below
                db.session.flush()
                
                # process bygender and division results, sorted by time or overallplace
                # TODO: is series.overall vs. series.orderby=='time' redundant?  same question for series.agegrade vs. series.orderby=='agtime'
                if series.orderby in ['time', 'overallplace']:
                    # get all the results which have been stored in the database for this race/series
                    dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id).order_by(series.orderby).all()
                    # this is easier, code-wise, than using sqlalchemy desc() function
                    if series.hightolow:
                        dbresults.reverse()
                    numresults = len(dbresults)

                    ### code below deleted because overallplace is definitely set in loop through ManagedResults above, 
                    ### and no ties are rendered in standings for overallplace anyway
                    # for rrndx in range(numresults):
                    #     raceresult = dbresults[rrndx]
                        
                    #     # set place if it has not been set before
                    #     # place may have been determined at previous iteration, if a tie was detected
                    #     if not raceresult.overallplace:
                    #         thisplace = rrndx+1
                    #         tieindeces = [rrndx]
                            
                    #         # detect tie in subsequent results based on rendering,
                    #         # which rounds to a specific precision based on distance
                    #         # but do this only if averaging ties
                    #         if series.has_series_option(SERIES_OPTION_AVERAGETIE):
                    #             # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
                    #             time = render.rendertime(raceresult.time,timeprecision)
                    #             for tiendx in range(rrndx+1,numresults):
                    #                 if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                    #                     break
                    #                 tieindeces.append(tiendx)
                    #             lasttie = tieindeces[-1] + 1
                    #         for tiendx in tieindeces:
                    #             numsametime = len(tieindeces)
                    #             if numsametime > 1 and series.has_series_option(SERIES_OPTION_AVERAGETIE):
                    #                 dbresults[tiendx].overallplace = (thisplace+lasttie) / 2.0
                    #             else:
                    #                 dbresults[tiendx].overallplace = thisplace
            
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
                        numresults = len(dbresults)
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                        
                            # set place if it has not been set before
                            # place may have been determined at previous iteration, if a tie was detected
                            if not raceresult.genderplace:
                                thisplace = rrndx+1
                                tieindeces = [rrndx]
                                
                                # detect tie in subsequent results based on rendering,
                                # which rounds to a specific precision based on distance
                                # but do this only if averaging ties
                                if series.averagetie:
                                    # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
                                    time = render.rendertime(raceresult.time,timeprecision)
                                    for tiendx in range(rrndx+1,numresults):
                                        if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                                            break
                                        tieindeces.append(tiendx)
                                    lasttie = tieindeces[-1] + 1
                                for tiendx in tieindeces:
                                    numsametime = len(tieindeces)
                                    if numsametime > 1 and series.averagetie:
                                        dbresults[tiendx].genderplace = (thisplace+lasttie) / 2.0
                                    else:
                                        dbresults[tiendx].genderplace = thisplace
            
                    if series.divisions:
                        for gender in ['F','M']:
                            
                            # linear search for correct division
                            for thisdiv in divisions:
                                divlow = thisdiv[0]
                                divhigh = thisdiv[1]
            
                                dbresults = RaceResult.query  \
                                              .filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender,divisionlow=divlow,divisionhigh=divhigh) \
                                              .order_by(series.orderby).all()
                                # this is easier, code-wise, than using sqlalchemy desc() function
                                if series.hightolow:
                                    dbresults.reverse()
                    
                                numresults = len(dbresults)
                                for rrndx in range(numresults):
                                    raceresult = dbresults[rrndx]
            
                                    # set place if it has not been set before
                                    # place may have been determined at previous iteration, if a tie was detected
                                    if not raceresult.divisionplace:
                                        thisplace = rrndx+1
                                        tieindeces = [rrndx]
                                        
                                        # detect tie in subsequent results based on rendering,
                                        # which rounds to a specific precision based on distance
                                        # but do this only if averaging ties
                                        if series.averagetie:
                                            # TODO: need to change this code to support orderby=='overallplace' and averagetie==True
                                            time = render.rendertime(raceresult.time,timeprecision)
                                            for tiendx in range(rrndx+1,numresults):
                                                if render.rendertime(dbresults[tiendx].time,timeprecision) != time:
                                                    break
                                                tieindeces.append(tiendx)
                                            lasttie = tieindeces[-1] + 1
                                        for tiendx in tieindeces:
                                            numsametime = len(tieindeces)
                                            if numsametime > 1 and series.averagetie:
                                                dbresults[tiendx].divisionplace = (thisplace+lasttie) / 2.0
                                            else:
                                                dbresults[tiendx].divisionplace = thisplace
            
                # process age grade results, ordered by agtime
                elif series.orderby == 'agtime':
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
                        numresults = len(dbresults)
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                        
                            # set place if it has not been set before
                            # place may have been determined at previous iteration, if a tie was detected
                            if not raceresult.agtimeplace:
                                thisplace = rrndx+1
                                tieindeces = [rrndx]
                                
                                # detect tie in subsequent results based on rendering,
                                # which rounds to a specific precision based on distance
                                # but do this only if averaging ties
                                if series.averagetie:
                                    time = render.rendertime(raceresult.agtime,agtimeprecision)
                                    for tiendx in range(rrndx+1,numresults):
                                        if render.rendertime(dbresults[tiendx].agtime,agtimeprecision) != time:
                                            break
                                        tieindeces.append(tiendx)
                                    lasttie = tieindeces[-1] + 1
                                for tiendx in tieindeces:
                                    numsametime = len(tieindeces)
                                    if numsametime > 1 and series.averagetie:
                                        dbresults[tiendx].agtimeplace = (thisplace+lasttie) / 2.0
                                    else:
                                        dbresults[tiendx].agtimeplace = thisplace

                # process age grade results, ordered by agpercent
                elif series.orderby == 'agpercent':
                    for gender in ['F','M']:
                        dbresults = RaceResult.query.filter_by(club_id=club_id,raceid=race.id,seriesid=series.id,gender=gender).order_by(series.orderby).all()
                        # this is easier, code-wise, than using sqlalchemy desc() function
                        if series.hightolow:
                            dbresults.reverse()
            
                        numresults = len(dbresults)
                        #current_app.logger.debug('orderby=agpercent, club_id={}, race.id={}, series.id={}, gender={}, numresults={}'.format(club_id,race.id,series.id,gender,numresults))
                        for rrndx in range(numresults):
                            raceresult = dbresults[rrndx]
                            thisplace = rrndx+1                                
                            dbresults[rrndx].agtimeplace = thisplace

            # commit database updates and close transaction
            db.session.commit()
            return success_response(redirect=url_for('frontend.seriesresults',raceid=raceid))
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = 'Unexpected Error: {}'.format(e)
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)

bp.add_url_rule('/_tabulateresults/<int:raceid>',view_func=AjaxTabulateResults.as_view('_tabulateresults'),methods=['POST'])

###########################################################################################
# downloadresults endpoint
###########################################################################################

class DownloadResultsForm(FlaskForm):
    service = StringField('Service')    # hidden
    url = StringField('Results URL')
    rsu_year = SelectField('Year')
    rsu_distance = SelectField('Distance')
    rsu_resultsset = SelectField('Result Set')


class DownloadResults(MethodView):
    def permission(self):
        return viewer_permission.can()

    def get(self):
        if not self.permission():
            return abort(403)

        form = DownloadResultsForm()
        return render_template(
            'downloadresults.jinja2', 
            form=form, 
            pagename='Download Results', 
            action='Download Results'
        )
    
    def post(self):
        service = request.form.get('service', None)
        if service == 'runsignup':
            resultssets = request.form.getlist('rsu_resultsset')
            headers = {}
            results = []
            race = None

            # use credentials for home club's children's full names
            with RunSignUp() as rsu:
                for resultsset in resultssets:
                    race_id, event_id, resultsset_id = resultsset.split('/')
                    if not race:
                        race = rsu.getrace(race_id)
                    resultsmeta = rsu.geteventresults(race_id, event_id, resultsset_id)
                    headers.update(resultsmeta['headers'])
                    results += resultsmeta['results']
            
            # write file and send to browser, not sure how/whether temporary directory gets deleted
            td = TemporaryDirectory(prefix='rrwebapp_results_')
            csvfilepath = os.path.join(td.name, 'runsignupresults.csv')
            with open(csvfilepath, 'w', newline='') as csvfile:
                # skipping custom and division columns for now, these are the RunSignUp standard headers
                fileheaders = 'result_id,place,bib,first_name,last_name,gender,age,city,state,' \
                            'country_code,clock_time,chip_time,pace,age_percentage'.split(',')
                dw = DictWriter(csvfile, fieldnames=fileheaders, extrasaction='ignore')
                dw.writeheader()
                dw.writerows(results)

            # convert file heading
            updfilepath = os.path.join(td.name, 'runsignupresults_updated.csv')
            with open(csvfilepath, newline='') as infile, open(updfilepath, 'w', newline='') as outfile:
                r = reader(infile)
                w = writer(outfile)
                rsuheading = next(r)
                newheading = [headers[r] for r in rsuheading]
                w.writerow(newheading)
                for row in r:
                    w.writerow(row)

            return send_file(updfilepath, as_attachment=True, attachment_filename=f"results-{race['name']}.csv")

        else:
            return jsonify(error='unknown service')

bp.add_url_rule('/downloadresults',view_func=DownloadResults.as_view('downloadresults'),methods=['GET', 'POST'])

class AjaxDownloadResults(MethodView):
    def permission(self):
        return viewer_permission.can()

    def get(self):
        if not self.permission():
            return abort(403)

        url = request.args.get('url', None)
        
        # url was supplied. that's good as we need it
        if url:
            try:
                # retrieve indicated page
                resultspage = requests_get(url)

                # check for errors, exception if problems
                resultspage.raise_for_status()

                # if this is runsignup page
                if search('cdnjs\.runsignup\.com', resultspage.text):
                    respdata = {'service': 'runsignup', 'options': {}}
                    # convenience handle
                    options = respdata['options']

                    rsuraceurl = search('\/Race\/Results\/([0-9]*)\/', resultspage.text)
                    if not rsuraceurl:
                        return jsonify(error='could not find downloadable results in page')

                    race_id = rsuraceurl.group(1)
                
                    # get result set information from race
                    with RunSignUp() as rsu:
                        raceevents = rsu.getraceevents(race_id)
                        rsutime = asctime('%m/%d/%Y %H:%M')
                        for event in raceevents:
                            event_id = event['event_id']
                            year = rsutime.asc2dt(event['start_time']).year
                            distance = event['distance']
                            options.setdefault(year, {})
                            options[year].setdefault(distance, [])
                            event_name = event['name']
                            resultsets = rsu.getresultsets(race_id, event_id)
                            for resultset in resultsets:
                                result_set_id = resultset['individual_result_set_id']
                                result_set_name = resultset['individual_result_set_name']
                                options[year][distance].append({'text': result_set_name, 'id': f'{race_id}/{event_id}/{result_set_id}'})

                    return jsonify(**respdata)

                # we don't handle this type of page yet
                else:
                    return jsonify(error='could not find downloadable results in page')
        
            except Exception as e:
                cause = format_exc()
                current_app.logger.error(cause)
                return jsonify(error=cause)

        # url not supplied
        else:
            return jsonify(error='url required')

bp.add_url_rule('/_downloadresults',view_func=AjaxDownloadResults.as_view('_downloadresults'),methods=['GET'])
