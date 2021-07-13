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
import traceback

# pypi
import flask
from flask import request, url_for, current_app
from flask_login import login_required
from flask.views import MethodView

# home grown
from . import bp
from ...accesscontrol import UpdateClubDataPermission, ViewClubDataPermission
from ...model import ClubAffiliation, insert_or_update
from ...model import db   # this is ok because this module only runs under flask
from ...model import Race, Series, Divisions, ClubAffiliation
from ...model import getclubid, getyear
from ...model import SERIES_OPTIONS, SERIES_OPTION_SEPARATOR
from ...apicommon import failure_response, success_response, check_header
from ...crudapi import CrudApi
from ...resultsutils import race_fixeddist

from ...forms import RaceForm, SeriesForm, RaceSettingsForm, DivisionForm
#from runningclub import racefile   # required for xlsx support
from loutilities.csvu import DictReaderStr2Num
from loutilities.filters import filtercontainerdiv, filterdiv

# acceptable surfaces -- must match model.SurfaceType
from ...model import SURFACES, CLUBAFFILIATION_ALTERNATES_SEPARATOR


###########################################################################################
# manageraces endpoint
###########################################################################################

filters = filtercontainerdiv()
filters += filterdiv('external-filter-series', 'Series')

dt_options = {
    'order': [[2, 'asc']],
}
yadcf_options = [
    {
        'column_selector': 'series.name:name',
        'select_type': 'select2',
        'select_type_options': {
            'width': '200px',
            'allowClear': True,  # show 'x' (remove) next to selection inside the select itself
            'placeholder': {
                'id': -1,
                'text': 'Select series',
            },
        },
        'filter_type': 'multi_select',
        'filter_container_id': 'external-filter-series',
        'column_data_type': 'text',
        'text_data_delimiter': ', ',
        'filter_reset_button_text': False,  # hide yadcf reset button
    },
]

def races_results_to_form(race):
    # there are some results
    if len(race.results) > 0:
        return '''
            <td align=center>
              <button class='_rrwebapp-importResultsButton _rrwebapp-needswidget' _rrwebapp-raceid='{raceid}'
                _rrwebapp-formaction='{importresults}' _rrwebapp-importdoc='{doc_importresults}' _rrwebapp-formid='_rrwebapp-form-results-{raceid}'
                _rrwebapp-editaction='{editparticipants}' 
                _rrwebapp-seriesresultsaction='{seriesresults}' 
                _rrwebapp-imported='true'>
              </button>
            </td>
        '''.format(raceid=race.id,
                   importresults=url_for("._importresults",raceid=race.id),
                   doc_importresults=url_for("doc_importresults"),
                   editparticipants=url_for(".editparticipants",raceid=race.id),
                   seriesresults=url_for("frontend.seriesresults",raceid=race.id)
                   )
    else:
        return '''
            <td align=center>
              <button class='_rrwebapp-importResultsButton _rrwebapp-needswidget' _rrwebapp-raceid='{raceid}'
                      _rrwebapp-formaction='{importresults}' _rrwebapp-importdoc='{doc_importresults}' _rrwebapp-formid='_rrwebapp-form-results-{raceid}'
                      _rrwebapp-editaction='{editparticipants}' 
                      >
              </button>
            </td>
        '''.format(raceid=race.id,
                   importresults=url_for("._importresults",raceid=race.id),
                   doc_importresults=url_for("doc_importresults"),
                   editparticipants=url_for(".editparticipants",raceid=race.id),
                   )

races_dbattrs = 'id,club_id,year,results,name,date,distance,surface,series'.split(',')
races_formfields = 'rowid,club_id,year,results,name,date,distance,surface,series'.split(',')
races_dbmapping = dict(list(zip(races_dbattrs, races_formfields)))
races_formmapping = dict(list(zip(races_formfields, races_dbattrs)))

# transform race results for fancy buttons
races_formmapping['results'] = races_results_to_form

# force default of club id and year for new or updated records
races_dbmapping['club_id'] = getclubid
races_dbmapping['year'] = getyear

races = CrudApi(
    app=bp,
    pagename='Races',
    template='manageraces.html',
    endpoint='.manageraces',
    rule='/manageraces',
    dbmapping=races_dbmapping,
    formmapping=races_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable=Race,
    queryparams={'external': False, 'active': True},
    checkrequired=True,
    clientcolumns=[
        {'data': 'results', 'name': 'results', 'label': 'Results', 'type': 'readonly',
         'class': 'column-center',
         'ed': {'type': 'hidden', 'submit': False}  # don't display or allow update in edit form
         },
        {'data': 'name', 'name': 'name', 'label': 'Race Name', '_unique': True,
         'className': 'field_req',
         },
        {'data': 'date',
         'name': 'date', 'label': 'Date', 'type': 'datetime',
         'className': 'field_req',
         'class': 'column-center',
         'ed': {'label': 'Date (yyyy-mm-dd)', 'format': 'YYYY-MM-DD',
                # first day of week for date picker is Sunday, strict date format required
                'opts': {'momentStrict': True, 'firstDay': 0}},
         },
        {'data': 'distance', 'name': 'distance', 'label': 'Miles',
         'className': 'field_req',
         'class': 'column-center',
         },
        {'data': 'surface', 'name': 'surface', 'label': 'Surface', 'type': 'select2',
         'className': 'field_req',
         'class': 'column-center',
         'options': SURFACES,
         },
        {'data': 'series', 'name': 'series', 'label': 'Series', 'type': 'select2',
         '_treatment': {'relationship':
             {
                 'dbfield': 'series',
                 'fieldmodel': Series,
                 'labelfield': 'name',
                 'formfield': 'series',
                 'uselist': True,
                 'queryparams': lambda: {'club_id': flask.session['club_id'], 'year': flask.session['year']}
             }
         }
         },
    ],
    serverside=False,
    byclub=True,
    byyear=True,
    idSrc='rowid',
    buttons=['create', 'edit', 'remove', 'csv',
             {'name': 'tools', 'text': 'Tools'}
             ],
    addltemplateargs={'inhibityear': False},
    pretablehtml=lambda: filters.render(),
    dtoptions=dt_options,
    yadcfoptions=yadcf_options,
    )
races.register()

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
                current_app.logger.error(cause)
                return failure_response(cause=cause)
            if not allowed_file(thisfile.filename):
                db.session.rollback()
                cause = 'Invalid file type "{}"'.format(thisfileext)
                current_app.logger.warning(cause)
                return failure_response(cause=cause)

            # handle csv file
            if thisfileext == 'csv':
                decoded = thisfile.stream.read().decode('utf-8').splitlines()
                thisfilecsv = DictReaderStr2Num(decoded)

                # verify file has required fields
                requiredfields = 'year,race,date,distance,surface'.split(',')
                if not check_header(requiredfields, thisfilecsv.fieldnames):
                    db.session.rollback()
                    cause = "invalid races file - one or more header fields missing, must have all of '{}'".format("', '".join(requiredfields))
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)

                fileraces = []
                for row in thisfilecsv:
                    # make sure all races are within correct year
                    if int(row['year']) != flask.session['year']:
                        db.session.rollback()
                        cause = 'File year {} does not match session year {}'.format(row['year'],flask.session['year'])
                        current_app.logger.warning(cause)
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
                current_app.logger.error(cause)
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
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)

                # time field is optional
                if 'time' not in thisrace:
                    thisrace['time'] = ''

                # add or update race in database
                race = Race(
                    club_id=club_id,
                    year=thisrace['year'],
                    name=thisrace['race'],
                    date=thisrace['date'],
                    starttime=thisrace['time'],
                    distance=thisrace['distance'],
                    surface=thisrace['surface'],
                    active=True,
                    external=False,
                )
                race.fixeddist = race_fixeddist(race.distance)
                added = insert_or_update(db.session,Race,race,skipcolumns=['id'],club_id=club_id,name=race.name,year=race.year)
                
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
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
bp.add_url_rule('/_importraces',view_func=AjaxImportRaces.as_view('_importraces'),methods=['POST'])
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
#bp.add_url_rule('/_series/<int:club_id>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
#bp.add_url_rule('/_series/<int:club_id>/','/_series/<int:club_id>/<int:year>/',defaults={'year':-1},view_func=series_api_view,methods=['POST'])
##----------------------------------------------------------------------

###########################################################################################
# manageseries endpoint
###########################################################################################

dt_options = {
    'order': [[0, 'asc']],
}

series_dbattrs = 'id,club_id,year,name,membersonly,calcoverall,calcdivisions,calcagegrade,orderby,'\
    'hightolow,allowties,averagetie,maxraces,multiplier,maxgenpoints,maxdivpoints,maxbynumrunners,races,options'.split(',')
series_formfields = 'rowid,club_id,year,name,membersonly,calcoverall,calcdivisions,calcagegrade,orderby,'\
    'hightolow,allowties,averagetie,maxraces,multiplier,maxgenpoints,maxdivpoints,maxbynumrunners,races,options'.split(',')
series_dbmapping = dict(list(zip(series_dbattrs, series_formfields)))
series_formmapping = dict(list(zip(series_formfields, series_dbattrs)))

# force default of club id and year for new or updated records
series_dbmapping['club_id'] = getclubid
series_dbmapping['year'] = getyear

series = CrudApi(
    app=bp,
    pagename='series',
    endpoint='.manageseries',
    rule='/manageseries',
    dbmapping=series_dbmapping,
    formmapping=series_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable=Series,
    queryparams={'active': True},
    checkrequired=True,
    clientcolumns=[
        {'data': 'name', 'name': 'name', 'label': 'Series Name', '_unique': True,
         'className': 'field_req',
         },
        {'data': 'maxraces', 'name': 'maxraces', 'label': 'Max Races',
         'class': 'column-center',
         },
        {'data': 'multiplier', 'name': 'multiplier', 'label': 'Multiplier',
         'class': 'column-center',
         },
        {'data': 'maxgenpoints', 'name': 'maxgenpoints', 'label': 'Max Gen Pts',
         'class': 'column-center',
         },
        {'data': 'maxdivpoints', 'name': 'maxdivpoints', 'label': 'Max Div Pts',
         'class': 'column-center',
         },
        {'data': 'maxbynumrunners', 'name': 'maxbynumrunners', 'label': 'Max by Num Rnrs',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'maxbynumrunners', 'dbfield': 'maxbynumrunners', 'truedisplay': 'yes', 'falsedisplay': 'no'}},
         },
        {'data': 'orderby', 'name': 'orderby', 'label': 'Order By', 'type': 'select2',
         'className': 'field_req',
         'class': 'column-center',
         'options': ['agtime','agpercent','time','overallplace'],
         },
        {'data': 'hightolow', 'name': 'hightolow', 'label': 'Order', 'type': 'select2',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'hightolow', 'dbfield': 'hightolow', 'truedisplay': 'descending', 'falsedisplay': 'ascending'}},
         },
        {'data': 'membersonly', 'name': 'membersonly', 'label': 'Members Only',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'membersonly', 'dbfield': 'membersonly', 'truedisplay': 'yes', 'falsedisplay': 'no'}}},
        {'data': 'averagetie', 'name': 'averagetie', 'label': 'Avg Ties',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'averagetie', 'dbfield': 'averagetie', 'truedisplay': 'yes', 'falsedisplay': 'no'}}},
        {'data': 'calcoverall', 'name': 'calcoverall', 'label': 'Overall',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'calcoverall', 'dbfield': 'calcoverall', 'truedisplay': 'yes', 'falsedisplay': 'no'}}},
        {'data': 'calcdivisions', 'name': 'calcdivisions', 'label': 'Divisions',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'calcdivisions', 'dbfield': 'calcdivisions', 'truedisplay': 'yes', 'falsedisplay': 'no'}}},
        {'data': 'calcagegrade', 'name': 'calcagegrade', 'label': 'Age Grade',
         'className': 'field_req',
         'class': 'column-center',
         '_treatment': {'boolean': {'formfield': 'calcagegrade', 'dbfield': 'calcagegrade', 'truedisplay': 'yes', 'falsedisplay': 'no'}}},
        {'data': 'options', 'name': 'options', 'label': 'Other Series Options',
         'type': 'checkbox',
         'ed': {
             'options': SERIES_OPTIONS,
             'separator': SERIES_OPTION_SEPARATOR,
         }
         },
        {'data': 'races', 'name': 'races', 'label': 'Races', 'type': 'select2',
         '_treatment': {'relationship':
             {
                 'dbfield': 'races',
                 'fieldmodel': Race,
                 'labelfield': 'name',
                 'formfield': 'races',
                 'uselist': True,
                 'queryparams': lambda: {'club_id': flask.session['club_id'], 'year': flask.session['year']}
             }
         },
         'render': '$.fn.dataTable.render.ellipsis( 20 )',
         },
    ],
    serverside=False,
    byclub=True,
    byyear=True,
    addltemplateargs={'inhibityear': False},
    idSrc='rowid',
    buttons=['create', 'edit', 'remove',
             {
                 'extend': 'csv',
                 'exportOptions': {'orthogonal': 'export'},
             },
             ],
    dtoptions=dt_options,
    )
series.register()


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
                # seriesparms = series.__dict__
                # # remove params which we'll set manually
                # seriesparms.pop('id')
                # seriesparms.pop('club_id')
                # seriesparms.pop('year')
                # seriesparms.pop('active')
                # # remove any non-class attributes
                # keys = seriesparms.keys()
                # for key in keys:
                #     if key[0] == "_": seriesparms.pop(key)
                # # some params need to be renamed
                # seriesparms['overall'] = seriesparms.pop('calcoverall')
                # seriesparms['divisions'] = seriesparms.pop('calcdivisions')
                # seriesparms['agegrade'] = seriesparms.pop('calcagegrade')
                # current_app.logger.debug('seriesparms={}'.format(seriesparms))
                # newseries = Series(series.club_id, thisyear, **seriesparms)
                newseries = Series(series.club_id, thisyear, 
                                   series.name, series.membersonly, 
                                   series.calcoverall, series.calcdivisions, series.calcagegrade, 
                                   series.orderby, series.hightolow, series.allowties, series.averagetie, 
                                   series.maxraces, series.multiplier, series.maxgenpoints, series.maxdivpoints, 
                                   series.maxbynumrunners, series.description)
                insert_or_update(db.session,Series,newseries,name=newseries.name,year=thisyear,club_id=club_id,skipcolumns=['id'])
                
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
bp.add_url_rule('/_copyseries',view_func=AjaxCopySeries.as_view('_copyseries'),methods=['POST'])
#----------------------------------------------------------------------

###########################################################################################
# managedivisions endpoint
###########################################################################################

divisions_dbattrs = 'id,club_id,year,series,divisionlow,divisionhigh'.split(',')
divisions_formfields = 'rowid,club_id,year,series,divisionlow,divisionhigh'.split(',')
divisions_dbmapping = dict(list(zip(divisions_dbattrs, divisions_formfields)))
divisions_formmapping = dict(list(zip(divisions_formfields, divisions_dbattrs)))

# force default of club id and year for new or updated records
divisions_dbmapping['club_id'] = getclubid
divisions_dbmapping['year'] = getyear

divisions = CrudApi(
    app=bp,
    pagename='divisions',
    endpoint='.managedivisions',
    rule='/managedivisions',
    dbmapping=divisions_dbmapping,
    formmapping=divisions_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable=Divisions,
    queryparams={'active': True},
    checkrequired=True,
    clientcolumns=[
        {'data': 'series', 'name': 'series', 'label': 'Series', 'type': 'select2',
         'className': 'field_req',
         '_treatment': {'relationship':
             {
                 'dbfield': 'series',
                 'fieldmodel': Series,
                 'labelfield': 'name',
                 'formfield': 'series',
                 'uselist': False,
                 'queryparams': lambda: {'club_id': flask.session['club_id'], 'year': flask.session['year']}
             }
         },
         },
        {'data': 'divisionlow', 'name': 'divisionlow', 'label': 'Low Age',
         'className': 'field_req',
         'class': 'column-center',
         },
        {'data': 'divisionhigh', 'name': 'divisionhigh', 'label': 'High Age',
         'className': 'field_req',
         'class': 'column-center',
         },
    ],
    serverside=False,
    byclub=True,
    byyear=True,
    addltemplateargs={'inhibityear': False},
    idSrc='rowid',
    buttons=['create', 'edit', 'remove', 'csv',
             ],
    )
divisions.register()


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
                    insert_or_update(db.session,Divisions,newdivision,year=thisyear,club_id=club_id,
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
bp.add_url_rule('/_copydivisions',view_func=AjaxCopyDivisions.as_view('_copydivisions'),methods=['POST'])
#----------------------------------------------------------------------


###########################################################################################
# clubaffiliation_view endpoint
###########################################################################################

clubaffiliations_dbattrs = 'id,club_id,year,shortname,title,alternates'.split(',')
clubaffiliations_formfields = 'rowid,club_id,year,shortname,title,alternates'.split(',')
clubaffiliations_dbmapping = dict(list(zip(clubaffiliations_dbattrs, clubaffiliations_formfields)))
clubaffiliations_formmapping = dict(list(zip(clubaffiliations_formfields, clubaffiliations_dbattrs)))

def get_clubaffiliations_alternates(dbrow):
    if not dbrow.alternates:
        return []
    else:
        return dbrow.alternates.split(CLUBAFFILIATION_ALTERNATES_SEPARATOR)

clubaffiliations_formmapping['alternates'] = get_clubaffiliations_alternates

# force default of club id and year for new or updated records
clubaffiliations_dbmapping['club_id'] = getclubid
clubaffiliations_dbmapping['year'] = getyear


class ClubAffiliationsView(CrudApi):
    def update_alternates(self, formdata):
        """
        make sure title is first choice in alternates
        """
        alternateitems = formdata['alternates'].split(CLUBAFFILIATION_ALTERNATES_SEPARATOR) if formdata['alternates'] else []
        if formdata['title'] not in alternateitems:
            alternateitems.insert(0, formdata['title'])
            formdata['alternates'] = CLUBAFFILIATION_ALTERNATES_SEPARATOR.join(alternateitems)

    def createrow(self, formdata):
        self.update_alternates(formdata)
        return super().createrow(formdata)

    def updaterow(self, thisid, formdata):
        self.update_alternates(formdata)
        return super().updaterow(thisid, formdata)

clubaffiliations = ClubAffiliationsView(
    app=bp,
    template='clubaffiliations.jinja2',
    pagename='Club Affiliations',
    endpoint='.clubaffiliations',
    rule='/clubaffiliations',
    dbmapping=clubaffiliations_dbmapping,
    formmapping=clubaffiliations_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable=ClubAffiliation,
    checkrequired=True,
    clientcolumns=[
        {'data': 'shortname', 'name': 'shortname', 'label': 'Display Name', 
         },
        {'data': 'title', 'name': 'title', 'label': 'Official Name',
         'className': 'field_req',
         },
        # see clubaffiliations_formmapping and RaceResults.js clubaffiliations() editor.on('initEdit', ...
        {'data': 'alternates', 'name': 'alternates', 'label': 'Alternate Names',
         'dt': {
             'render': {'eval': f'render_select_as_tags()'},
         },
         'type': 'select2', 
         'separator': CLUBAFFILIATION_ALTERNATES_SEPARATOR,
         'options': [],
         'opts': {
             'multiple': 'multiple',
             'tags': True,
         }
         },
    ],
    serverside=False,
    byclub=True,
    byyear=True,
    addltemplateargs={'inhibityear': False},
    idSrc='rowid',
    buttons=['create', 'edit', 'remove', 'csv',
             ],
    )
clubaffiliations.register()

class AjaxCopyClubAffiliations(MethodView):
    decorators = [login_required]
    
    def post(self):
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
            
            # if some items exists for this year, verify user wants to overwrite
            thisyearitems = ClubAffiliation.query.filter_by(club_id=club_id, year=thisyear).all()
            if thisyearitems and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite club affiliations for this year?', confirm=True)

            # user has agreed to overwrite any items -- assume all are obsolete until overwritten
            obsoleteitems = {}
            for item in thisyearitems:
                obsoleteitems[item.shortname] = item
            
            # copy each entry from "copyyear"
            for item in ClubAffiliation.query.filter_by(club_id=club_id, year=copyyear).all():
                newitem = ClubAffiliation(club_id=club_id, year=thisyear)
                insert_or_update(db.session, ClubAffiliation, newitem, year=thisyear, club_id=club_id, skipcolumns=['id'])
                
                # any items we updated is not obsolete
                if newitem.shortname in obsoleteitems:
                    obsoleteitems.pop(newitem.shortname)
                    
            # remove obsolete items
            for shortname in obsoleteitems:
                db.session.delete(obsoleteitems[shortname])
                
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
bp.add_url_rule('/_copyclubaffiliations',view_func=AjaxCopyClubAffiliations.as_view('_copyclubaffiliations'),methods=['POST'])

