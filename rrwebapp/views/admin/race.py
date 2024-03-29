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
from traceback import format_exception_only, format_exc

# pypi
import flask
from flask import request, url_for, current_app, jsonify
from flask_login import login_required
from flask.views import MethodView
from loutilities.tables import rest_url_for
from loutilities.csvu import DictReaderStr2Num
from loutilities.filters import filtercontainerdiv, filterdiv
from loutilities.tables import get_request_data

# home grown
from . import bp
from ...accesscontrol import UpdateClubDataPermission, ViewClubDataPermission
from ...model import ClubAffiliation, insert_or_update
from ...model import db   # this is ok because this module only runs under flask
from ...model import Race, Series, Divisions, Club
from ...model import getclubid, getyear
from ...model import SERIES_OPTIONS, SERIES_OPTION_SEPARATOR, SERIES_TIE_OPTIONS, SERIES_TIE_OPTION_SEPARATOR
from ...apicommon import failure_response, success_response, check_header
from ...crudapi import CrudApi
from ...resultsutils import race_fixeddist

from ...forms import RaceForm, SeriesForm, RaceSettingsForm, DivisionForm
#from runningclub import racefile   # required for xlsx support

# acceptable surfaces -- must match model.SurfaceType
from ...model import SURFACES, CLUBAFFILIATION_ALTERNATES_SEPARATOR

# admin guide
from ...version import __docversion__
adminguide = f'https://docs.scoretility.com/en/{__docversion__}/scoring-admin-guide.html'

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
                   doc_importresults=f'https://docs.scoretility.com/en/{__docversion__}/scoring-file-formats.html#results-file-format',
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
                   doc_importresults=f'https://docs.scoretility.com/en/{__docversion__}/scoring-file-formats.html#results-file-format',
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

races_view = CrudApi(
    app=bp,
    pagename='Races',
    template='manageraces.html',
    templateargs={'adminguide': adminguide, 'docversion': __docversion__},
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
races_view.register()

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

series_dbattrs = 'id,club_id,year,name,membersonly,calcoverall,calcdivisions,calcagegrade,orderby,minraces,'\
    'oaawards,divawards,tieoptions,'\
    'hightolow,allowties,averagetie,maxraces,multiplier,maxgenpoints,maxdivpoints,maxbynumrunners,races,options'.split(',')
series_formfields = 'rowid,club_id,year,name,membersonly,calcoverall,calcdivisions,calcagegrade,orderby,minraces,'\
    'oaawards,divawards,tieoptions,'\
    'hightolow,allowties,averagetie,maxraces,multiplier,maxgenpoints,maxdivpoints,maxbynumrunners,races,options'.split(',')
series_dbmapping = dict(list(zip(series_dbattrs, series_formfields)))
series_formmapping = dict(list(zip(series_formfields, series_dbattrs)))

# force default of club id and year for new or updated records
series_dbmapping['club_id'] = getclubid
series_dbmapping['year'] = getyear

class SeriesView(CrudApi):
   
    def setbuttons(self):
        buttons = ['create', 'edit', 'remove', 'csv',
                    {
                        'text': 'Copy From Year',
                        'name': 'series-copy-button',
                        'editor': {'eval': 'series_copy_saeditor.saeditor'},
                        'url': url_for('admin._copyseries'),
                        'action': {
                            'eval': f"series_copy_button(\"{url_for('admin._copyseries')}\")"
                        }
                    }
                  ]

        return buttons

series_view = SeriesView(
    app=bp,
    pagename='series',
    endpoint='.manageseries',
    rule='/manageseries',
    template='series.jinja2',
    templateargs={'adminguide': adminguide},
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
        {'data': 'minraces', 'name': 'minraces', 'label': 'Place Min Races',
         'class': 'column-center',
         },
        {'data': 'oaawards', 'name': 'oaawards', 'label': '# OA Awards',
         'class': 'column-center',
         },
        {'data': 'divawards', 'name': 'divawards', 'label': '# Div Awards',
         'class': 'column-center',
         },
        {'data': 'tieoptions', 'name': 'tieoptions', 'label': 'Tiebreaker Options',
         'type': 'checkbox',
         'ed': {
             'options': SERIES_TIE_OPTIONS,
             'separator': SERIES_TIE_OPTION_SEPARATOR,
         }
         },
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
    buttons=lambda: series_view.setbuttons(),
    dtoptions={
        'order': [['name:name', 'asc']],
    },
    )
series_view.register()


class AjaxCopySeries(MethodView):
    
    def get(self):
        try:
            # verify user can write the data, otherwise abort (adapted from loutilities.tables._editormethod)
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            clubs = [c for c in Club.query.all() if ViewClubDataPermission(c.id)]
            options = {}
            for club in clubs:
                # Series.query... returns like [(2021,), (2020,)]
                years = [y[0] for y in Series.query.filter_by(club_id=club.id).with_entities(Series.year).distinct().all()]
                if years:
                    years.sort()
                    options[club.name] = {'option': {'label':club.name, 'value':club.id}, 'years': years}


            # return select options
            return jsonify(options=options, values={})

        except Exception as e:
            exc = ''.join(format_exception_only(type(e), e))
            output_result = {'status': 'fail', 'error': 'exception occurred:<br>{}'.format(exc)}
            # roll back database updates and close transaction
            db.session.rollback()
            current_app.logger.error(format_exc())
            return jsonify(output_result)

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
            requestdata = get_request_data(request.form)
            fromclubid = requestdata['keyless']['club']
            fromyear = requestdata['keyless']['year']
            force = requestdata['keyless']['force']
            thisyear = flask.session['year']
            
            # if some series exists for this year, verify user wants to overwrite
            thisyearseries = Series.query.filter_by(club_id=club_id,active=True,year=thisyear).all()
            if thisyearseries and not force=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite series for this year?',confirm=True)

            # user has agreed to overwrite any series -- assume all are obsolete until overwritten
            obsoleteseries = {}
            for series in thisyearseries:
                obsoleteseries[series.name] = series
            
            # copy each entry from requested club/year
            for series in Series.query.filter_by(club_id=fromclubid,active=True,year=fromyear).all():
                newseries = Series(
                    club_id = series.club_id, 
                    year = thisyear, 
                    name = series.name, 
                    membersonly = series.membersonly, 
                    calcoverall = series.calcoverall, 
                    calcdivisions = series.calcdivisions, 
                    calcagegrade = series.calcagegrade,
                    orderby = series.orderby, 
                    hightolow = series.hightolow, 
                    allowties = series.allowties, 
                    averagetie = series.averagetie, 
                    options = series.options, 
                    maxraces = series.maxraces, 
                    multiplier = series.multiplier, 
                    maxgenpoints = series.maxgenpoints, 
                    maxdivpoints = series.maxdivpoints, 
                    maxbynumrunners = series.maxbynumrunners, 
                    active = series.active, 
                    description = series.description,
                    oaawards = series.oaawards,
                    divawards = series.divawards,
                    minraces = series.minraces,
                    tieoptions = series.tieoptions,
                )
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
bp.add_url_rule('/_copyseries',view_func=AjaxCopySeries.as_view('_copyseries'),methods=['GET', 'POST'])

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

class DivisionsView(CrudApi):
   
    def setbuttons(self):
        buttons = ['create', 'edit', 'remove', 'csv',
                    {
                        'text': 'Copy From Year',
                        'name': 'division-copy-button',
                        'editor': {'eval': 'divisions_copy_saeditor.saeditor'},
                        'url': url_for('admin._copydivisions'),
                        'action': {
                            'eval': f"divisions_copy_button(\"{url_for('admin._copydivisions')}\")"
                        }
                    }
                  ]

        return buttons

divisions_view = DivisionsView(
    app=bp,
    pagename='divisions',
    endpoint='.managedivisions',
    rule='/managedivisions',
    template='divisions.jinja2',
    templateargs={'adminguide': adminguide},
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
    buttons=lambda: divisions_view.setbuttons(),
    dtoptions={
        'order': [['series.name:name', 'asc'], ['divisionlow:name',  'asc']],
    },
    )
divisions_view.register()


class AjaxCopyDivisions(MethodView):
    
    def get(self):
        try:
            # verify user can write the data, otherwise abort (adapted from loutilities.tables._editormethod)
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            clubs = [c for c in Club.query.all() if ViewClubDataPermission(c.id)]
            options = {}
            for club in clubs:
                # Divisions.query... returns like [(2021,), (2020,)]
                years = [y[0] for y in Divisions.query.filter_by(club_id=club.id).with_entities(Divisions.year).distinct().all()]
                if years:
                    years.sort()
                    options[club.name] = {'option': {'label':club.name, 'value':club.id}, 'years': years}


            # return select options
            return jsonify(options=options, values={})

        except Exception as e:
            exc = ''.join(format_exception_only(type(e), e))
            output_result = {'status': 'fail', 'error': 'exception occurred:<br>{}'.format(exc)}
            # roll back database updates and close transaction
            db.session.rollback()
            current_app.logger.error(format_exc())
            return jsonify(output_result)

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
            requestdata = get_request_data(request.form)
            fromclubid = requestdata['keyless']['club']
            fromyear = requestdata['keyless']['year']
            force = requestdata['keyless']['force']
            thisyear = flask.session['year']
            
            # if some divisions exists for this year, verify user wants to overwrite
            thisyeardivisions = Divisions.query.filter_by(club_id=club_id,active=True,year=thisyear).all()
            if thisyeardivisions and not force=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite divisions for this year?',confirm=True)

            # user has agreed to overwrite any divisions -- assume all are obsolete until overwritten
            obsoletedivisions = {}
            for division in thisyeardivisions:
                obsoletedivisions[(division.seriesid,division.divisionlow,division.divisionhigh)] = division
            
            # check if series exist
            seriesfound = False
            
            # copy each entry from requested club/year
            for division in Divisions.query.filter_by(club_id=fromclubid,active=True,year=fromyear).all():
                series = Series.query.filter_by(club_id=club_id,active=True,year=thisyear,name=division.series.name).first()
                if series:
                    seriesfound = True
                    newdivision = Divisions(
                        club_id=club_id,
                        year=thisyear,
                        seriesid=series.id,
                        divisionlow=division.divisionlow,
                        divisionhigh=division.divisionhigh,
                        active=division.active,
                    )
                    insert_or_update(db.session,Divisions,newdivision,year=thisyear,club_id=club_id,
                        seriesid=newdivision.seriesid, divisionlow=newdivision.divisionlow, divisionhigh=newdivision.divisionhigh,
                        skipcolumns=['id'])
                
                    # any divisions we updated is not obsolete
                    if (newdivision.seriesid,newdivision.divisionlow,newdivision.divisionhigh) in obsoletedivisions:
                        obsoletedivisions.pop((newdivision.seriesid,newdivision.divisionlow,newdivision.divisionhigh))
                    
            if not seriesfound:
                db.session.rollback()
                return failure_response(cause='No divisions copied -- did you copy or create series first?')

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
bp.add_url_rule('/_copydivisions',view_func=AjaxCopyDivisions.as_view('_copydivisions'),methods=['GET', 'POST'])


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
        # return lower case alternates, removing duplicates
        alternates = []
        for alternate in [a.lower() for a in dbrow.alternates.split(CLUBAFFILIATION_ALTERNATES_SEPARATOR)]:
            if alternate not in alternates:
                alternates.append(alternate)
        return alternates

clubaffiliations_formmapping['alternates'] = get_clubaffiliations_alternates

# force default of club id and year for new or updated records
clubaffiliations_dbmapping['club_id'] = getclubid
clubaffiliations_dbmapping['year'] = getyear

def clubaffiliations_validate(action, formdata):
    results = []

    club_id = getclubid(formdata)
    allclubs = ClubAffiliation.query.filter_by(club_id=club_id).filter(ClubAffiliation.shortname != formdata['shortname']).all()
    clubalternates = set()
    for club in allclubs:
        if club.alternates:
            thosealternates = set([a.lower() for a in club.alternates.split(CLUBAFFILIATION_ALTERNATES_SEPARATOR)])
            clubalternates |= thosealternates
    thesealternates = []
    if formdata['title']:
        thesealternates += [formdata['title']]
    if formdata['alternates']:
        thesealternates += [a for a in formdata['alternates'].split(CLUBAFFILIATION_ALTERNATES_SEPARATOR) if a not in thesealternates]
    badalternates = [a for a in thesealternates if a.lower() in clubalternates]

    if badalternates:
        badaltrender = ', '.join(badalternates)
        results.append({'name': 'shortname', 'status': f'conflicting official name / alternates: {badaltrender}'})

    return results


class ClubAffiliationsView(CrudApi):
    def update_alternates(self, formdata):
        """
        make sure title, shortname are in alternates
        """
        alternateitems = formdata['alternates'].split(CLUBAFFILIATION_ALTERNATES_SEPARATOR) if formdata['alternates'] else []
        if formdata['title'].lower() not in alternateitems:
            alternateitems.insert(0, formdata['title'].lower())
        # be careful not to include shortname == None
        if formdata['shortname'] and formdata['shortname'].lower() not in alternateitems:
            alternateitems.insert(0, formdata['shortname'].lower())
        formdata['alternates'] = CLUBAFFILIATION_ALTERNATES_SEPARATOR.join(alternateitems) if alternateitems else None

    def createrow(self, formdata):
        self.update_alternates(formdata)
        return super().createrow(formdata)

    def updaterow(self, thisid, formdata):
        self.update_alternates(formdata)
        return super().updaterow(thisid, formdata)
    
    def setbuttons(self):
        buttons = ['create', 'edit', 'remove', 'csv',
                    {
                        'text': 'Copy From Year',
                        'name': 'clubaffiliations-copy-button',
                        'editor': {'eval': 'clubaffiliations_copy_saeditor.saeditor'},
                        'url': url_for('admin._copyclubaffiliations'),
                        'action': {
                            'eval': f"clubaffiliations_copy_button(\"{url_for('admin._copyclubaffiliations')}\")"
                        }
                    }
                  ]

        return buttons


clubaffiliations_view = ClubAffiliationsView(
    app=bp,
    template='clubaffiliations.jinja2',
    templateargs={'adminguide': adminguide},
    pagename='Club Affiliations',
    endpoint='.clubaffiliations',
    rule='/clubaffiliations',
    dbmapping=clubaffiliations_dbmapping,
    formmapping=clubaffiliations_formmapping,
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    validate=clubaffiliations_validate,
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
    buttons=lambda: clubaffiliations_view.setbuttons()
    )
clubaffiliations_view.register()

class AjaxCopyClubAffiliations(MethodView):
    
    def get(self):
        try:
            # verify user can write the data, otherwise abort (adapted from loutilities.tables._editormethod)
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            clubs = [c for c in Club.query.all() if ViewClubDataPermission(c.id)]
            options = {}
            for club in clubs:
                # ClubAffiliation.query... returns like [(2021,), (2020,)]
                years = [y[0] for y in ClubAffiliation.query.filter_by(club_id=club.id).with_entities(ClubAffiliation.year).distinct().all()]
                if years:
                    years.sort()
                    options[club.name] = {'option': {'label':club.name, 'value':club.id}, 'years': years}


            # return select options
            return jsonify(options=options, values={})

        except Exception as e:
            exc = ''.join(format_exception_only(type(e), e))
            output_result = {'status': 'fail', 'error': 'exception occurred:<br>{}'.format(exc)}
            # roll back database updates and close transaction
            db.session.rollback()
            current_app.logger.error(format_exc())
            return jsonify(output_result)

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
            requestdata = get_request_data(request.form)
            fromclubid = requestdata['keyless']['club']
            fromyear = requestdata['keyless']['year']
            force = requestdata['keyless']['force']
            thisyear = flask.session['year']
            
            # if some items exists for this year, verify user wants to overwrite
            thisyearitems = ClubAffiliation.query.filter_by(club_id=club_id, year=thisyear).all()
            if thisyearitems and not force=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite club affiliations for this year?', confirm=True)

            # user has agreed to overwrite any items -- assume all are obsolete until overwritten
            obsoleteitems = {}
            for item in thisyearitems:
                obsoleteitems[item.shortname] = item
            
            # copy each entry from requested club/year
            for item in ClubAffiliation.query.filter_by(club_id=fromclubid, year=fromyear).all():
                newitem = ClubAffiliation(club_id=club_id, year=thisyear, shortname=item.shortname, title=item.title, alternates=item.alternates)
                insert_or_update(db.session, ClubAffiliation, newitem, year=thisyear, club_id=club_id, shortname=item.shortname, skipcolumns=['id'])
                
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
bp.add_url_rule('/_copyclubaffiliations',view_func=AjaxCopyClubAffiliations.as_view('_copyclubaffiliations'),methods=['GET', 'POST'])

