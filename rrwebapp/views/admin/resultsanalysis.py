###########################################################################################
# resultsanalysis - result analysis views 
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/14/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
#
###########################################################################################

# standard
import csv
from collections import OrderedDict
import traceback
import os
import os.path
import json

# pypi
import flask
from flask import request, jsonify, url_for, current_app
from flask_login import login_required
from flask.views import MethodView

# homegrown
from . import bp
from ...celery import celeryapp
from ...tasks import analyzeresultstask
from ...model import ApiCredentials, Club, Runner, RaceResultService, Course
from ...accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from ...model import db   # this is ok because this module only runs under flask
from ...apicommon import failure_response, success_response
from loutilities.csvwt import wlist
from ...request_helpers import addscripts
from ...crudapi import CrudApi
from ...datatables_utils import AdminDatatablesCsv
from loutilities.timeu import asctime
ftime = asctime('%Y-%m-%d')

# define exceptions
class invalidParameter(Exception): pass

# set up summary file name template
summaryfiletemplate = lambda: '{}/{{clubslug}}-summary.csv'.format(current_app.config['MEMBERSHIP_DIR'])


#######################################################################
class ResultsAnalysisStatus(MethodView):
#######################################################################
    decorators = [login_required]
    # NOTE: pattern loosely follows crudapi.CrudApi

    #----------------------------------------------------------------------
    def __init__(self, **kwargs):
    #----------------------------------------------------------------------
        # the args dict has all the defined parameters to 
        # caller supplied keyword args are used to update the defaults
        # all arguments are made into attributes for self
        self.kwargs = kwargs
        args = dict(pagename = 'Results Analysis Status / Control',
                    endpoint = 'resultsanalysisstatus', 
                    rule = '/resultsanalysisstatus'
                    )
        args.update(kwargs)        
        for key in args:
            setattr(self, key, args[key])

    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        # create supported endpoints
        my_view = self.as_view(self.endpoint, **self.kwargs)
        bp.add_url_rule('{}'.format(self.rule),view_func=my_view,methods=['GET',])
        bp.add_url_rule('{}/rest'.format(self.rule),view_func=my_view,methods=['GET', 'POST'])

    #----------------------------------------------------------------------
    def _renderpage(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            # build table data, will be retrieved later
            tabledata = []

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [
                    { 'data': 'source', 'name': 'source', 'label': 'Source' },
                    { 'data': 'status', 'name': 'status', 'label': 'Status' }, 
                    { 'data': 'lastnameprocessed', 'name': 'stlastnameprocessedatus', 'label': 'Last Name Processed' }, 
                    { 'data': 'records', 'name': 'records', 'label': 'Processed / Total' }, 
                ],
                'select': False,
                'ordering': True,
                'order': [[0,'asc']]
            }

            # buttons just names the buttons to be included, in what order
            buttons = [ 
                        { 'extend':'collect', 
                          'url': '{}/rest?action=collect'.format(url_for('admin.resultsanalysisstatus')),
                          'statusurl': '{}/rest'.format(url_for('admin.resultsanalysisstatus')) 
                        },
                        { 'extend':'summarize', 
                          'url': '{}/rest?action=summarize'.format(url_for('admin.resultsanalysisstatus')),
                          'statusurl': '{}/rest'.format(url_for('admin.resultsanalysisstatus')) 
                        },
                        { 'extend':'cancel', 
                          'url': '{}/rest?action=cancel'.format(url_for('admin.resultsanalysisstatus')), 
                          'enabled': False 
                        },
                      ]


            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html', 
                                         pagename=self.pagename,
                                         pagejsfiles=addscripts(['resultanalysis.js']),
                                         tabledata=tabledata, 
                                         tablebuttons = buttons,
                                         tablefiles = None,
                                         options = {'dtopts': dt_options},
                                         inhibityear=True,
                                         writeallowed=owner_permission.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def _retrieverows(self):
    #----------------------------------------------------------------------

        task_id = request.args.get('task_id', None)

        # maybe we are being asked if task is already running
        if not task_id:
            club_id = flask.session['club_id']
            clubslug = Club.query.filter_by(id=club_id).first().shname
            
            # taskfile is used to indicate a task is currently running
            # this file gets created at start (here), 
            # and deleted at finish (by analyzeresultstask) or cancel (here)
            taskfile = '{}/{}-task.id'.format(current_app.config['MEMBERSHIP_DIR'], clubslug)
            
            # if task is running, get task id from taskfile
            try:
                with open(taskfile) as tf:
                    task_id = tf.read()
            
            # if taskfile doesn't exist, task isn't running, tell caller without further processing
            except IOError:
                response = {
                    'state': 'IDLE',
                    'progress': {}
                }
                return jsonify(response)

        task = analyzeresultstask.AsyncResult(task_id)
        # current_app.logger.debug('task.state={} task.info={}'.format(task.state, task.info))

        if task.state == 'PENDING':
            # job did not start yet
            response = {
                'state': task.state,
                'progress': {'starting': { 'status': 'starting', 'lastname':'', 'processed': '', 'total': ''} },
                'task_id': task_id,
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'progress': task.info.get('progress', {}),
                'task_id': task_id,
            }

            # task is finished, check for traceback, which indicates an error occurred
            if task.state == 'SUCCESS':
                # check for traceback, which indicates an error occurred
                response['cause'] = task.info.get('traceback','')
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
                'progress': task.info.get('progress', {}),
                'task_id': task_id,
                'cause': str(task.info),  # this is the exception raised
            }
        return jsonify(response)

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        # verify user can write the data, otherwise abort
        if not owner_permission.can():
            db.session.rollback()
            flask.abort(403)
            
        if request.path[-4:] != 'rest':
            return self._renderpage()
        else:
            return self._retrieverows()

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            clubslug = Club.query.filter_by(id=club_id).first().shname
            
            # verify user can write the data, otherwise abort
            if not owner_permission.can():
                db.session.rollback()
                flask.abort(403)
            
            # taskfile is used to indicate a task is currently running
            # this file gets created at start (here), 
            # and deleted at finish (by analyzeresultstask) or cancel (here)
            taskfile = '{}/{}-task.id'.format(current_app.config['MEMBERSHIP_DIR'], clubslug)

            # summaryfile is used to save the summary information for individual members
            summaryfile = summaryfiletemplate().format(clubslug=clubslug)

            # check action
            action = request.args.get('action')

            # start task
            if action in ['collect', 'summarize']:
                # if taskfile exists, make believe it was just started and return
                try:
                    with open(taskfile) as tf:
                        task_id = tf.read()
                    db.session.commit()
                    return jsonify({'success': True, 'task_id': task_id}), 202, {}

                # taskfile doesn't exist. this is the normal path -- ignore the exception
                except IOError:
                    pass

                # note extra set of {{service}} brackets, which will be replace by service name
                detailfile = '{}/{}-{{service}}-detail.csv'.format(current_app.config['MEMBERSHIP_DIR'], clubslug)
                fulldetailfile = '{}/{}-detail.csv'.format(current_app.config['MEMBERSHIP_DIR'], clubslug)

                # convert members to file-like list
                # filefields and dbattrs are used to convert db to file format
                filefields = 'GivenName,FamilyName,DOB,Gender'.split(',')
                dbattrs = 'fname,lname,dateofbirth,gender'.split(',')
                memberfile = wlist()
                OUT = csv.DictWriter(memberfile, filefields)
                OUT.writeheader()
                members = Runner.query.filter_by(club_id=club_id, member=True, active=True)
                mapping = dict(list(zip(dbattrs, filefields)))
                for member in members:
                    filerow = {}
                    for dbattr in mapping:
                        filerow[mapping[dbattr]] = getattr(member, dbattr)
                    OUT.writerow(filerow)

                # kick off analysis task
                task = analyzeresultstask.apply_async((club_id, action, url_for('.resultschart'), memberfile, detailfile, summaryfile, fulldetailfile, taskfile), queue='longtask')

                # save taskfile
                with open(taskfile,'w') as tf:
                    tf.write(task.id)

                # we've started
                db.session.commit()
                return jsonify({'success': True, 'task_id': task.id}), 202, {}

            # cancel indicated task
            elif action == 'cancel':
                task_id = request.args.get('task_id')
                try:
                    os.remove(taskfile)
                except:
                    # ignore exceptions removing file
                    pass
                celeryapp.control.revoke(task_id, terminate=True)
                db.session.commit()
                return jsonify({'success': True, 'task_id': task_id})

        except:
            # roll back database updates and close transaction
            if os.path.isfile(taskfile):
                os.remove(taskfile)
            db.session.rollback()
            raise

#----------------------------------------------------------------------
ras = ResultsAnalysisStatus()
ras.register()
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# courses endpoint
#----------------------------------------------------------------------

course_dbattrs = 'id,club_id,name,source,sourceid,date,distmiles,distkm,surface,location,raceid'.split(',')
course_formfields = 'rowid,club_id,name,source,sourceid,date,distmiles,distkm,surface,location,raceid'.split(',')
course_dbmapping = OrderedDict(list(zip(course_dbattrs, course_formfields)))
course_formmapping = OrderedDict(list(zip(course_formfields, course_dbattrs)))
course = CrudApi(
    app = bp,
    pagename = 'Courses', 
    endpoint = 'admin.courses',
    rule = '/courses', 
    dbmapping = course_dbmapping, 
    formmapping = course_formmapping, 
    writepermission = owner_permission.can, 
    dbtable = Course, 
    clientcolumns = [
       { 'data': 'name', 'name': 'name', 'label': 'Race Name' },
       { 'data': 'source', 'name': 'source', 'label': 'Source' },
       { 'data': 'sourceid', 'name': 'sourceid', 'label': 'Source ID' },
       { 'data': 'date', 'name': 'date', 'label': 'Date' },
       { 'data': 'distmiles', 'name': 'distmiles', 'label': 'Dist (Miles)' },
       { 'data': 'distkm', 'name': 'distkm', 'label': 'Dist (km)' },
       { 'data': 'surface', 'name': 'surface', 'label': 'Surface' },
       { 'data': 'location', 'name': 'location', 'label': 'Location' },
       { 'data': 'raceid', 'name': 'raceid', 'label': 'Race ID' },
    ], 
    servercolumns = None,  # no ajax
    byclub = True, 
    idSrc = 'rowid', 
    buttons = ['create', 'edit', 'remove'])
course.register()


#----------------------------------------------------------------------
# resultsanalysissummary endpoint
#----------------------------------------------------------------------

def ras_readpermission():
    club_id = flask.session['club_id']
    readcheck = ViewClubDataPermission(club_id)
    return readcheck.can()

def ras_csvfile():
    club_id = flask.session['club_id']
    clubslug = Club.query.filter_by(id=club_id).first().shname
    return summaryfiletemplate().format(clubslug=clubslug)

# items are name:label. use label for for button text. use OrderedDict so buttons are in same order as headers
ras_statnames = OrderedDict([('1yr-agegrade', '1yr agegrade'), ('avg-agegrade', 'avg agegrade'), ('trend', 'trend'), ('numraces', 'numraces')])
def ras_columns():
    club_id = flask.session['club_id']
    clubslug = Club.query.filter_by(id=club_id).first().shname
    colfile = summaryfiletemplate().format(clubslug=clubslug) + '.cols'
    with open(colfile, 'r') as cols:
        cols = json.loads(cols.read())
    
    invisiblecols = ['lname', 'fname', 'r-squared', 'stderr', 'pvalue']
    for col in cols:
        if col['name'] in ['name']:
            col['className'] = ' _rrwebapp-table-nowrap'

        if col['name'] in ['age', 'gender']:
            col['className'] = 'dt-body-center'

        for invisiblename in invisiblecols:
            if invisiblename in col['name']:
                col['visible'] = False

        for statname in ras_statnames:
            if statname in col['name']:
                if 'overall' in col['name']:
                    col['className'] = 'dt-body-center _rrwebapp-ras-summary'
                else:
                    col['className'] = 'dt-body-center _rrwebapp-ras-{}-detail'.format(statname)

            if 'agegrade' in col['name']:
                # note need () around function for this to be eval'd correctly
                col['render'] = '(function (data) { return (data != "") ? parseFloat(data).toFixed(1) : "" })'

            if 'trend' in col['name']:
                col['render'] = '(function (data) { return (data != "") ? parseFloat(data).toFixed(1)+"%/yr" : "" })'
                col['type'] = 'agtrend'


    return cols

def ras_buttons():
    buttons = ['csv']
    for statname in ras_statnames:
        buttons.append({
                'extend' : 'colvisToggleGroup',
                'visibletext' : '{} -'.format(ras_statnames[statname]),
                'hiddentext' : '{} +'.format(ras_statnames[statname]),
                'columns' : '._rrwebapp-ras-{}-detail'.format(statname),
                'visible' : False,
            })
    return buttons

ras = AdminDatatablesCsv(
    app = bp,
    pagename = 'Results Analysis Summary', 
    endpoint = 'admin.resultsanalysissummary', 
    rule = '/resultsanalysissummary',
    dtoptions =  {
        'stateSave' : True,
        'fixedColumns' : { 'leftColumns': 1 },
        'scrollX' : True,
        'scrollXInner' : '100%', 
        'autoWidth' : False,
        },
        readpermission = ras_readpermission, 
        csvfile = ras_csvfile,
        # columns labels must match labels in resultssummarize.summarize
        columns = ras_columns, 
        buttons = ras_buttons,
        )
ras.register()



