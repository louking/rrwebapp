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

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask_login import login_required
from flask.views import MethodView
from celery import states

# homegrown
from . import app
from . import celery
from racedb import ApiCredentials, Club, Runner, RaceResultService, Course
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response
from loutilities.csvwt import wlist
from request import addscripts
from crudapi import CrudApi

# set up services to collect data from
collectservices = {}
import athlinksresults
collectservices['athlinks'] = athlinksresults.collect

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
        args = dict(pagename = 'Results Analysis Status',
                    endpoint = 'resultsanalysisstatus', 
                    )
        args.update(kwargs)        
        for key in args:
            setattr(self, key, args[key])

    #----------------------------------------------------------------------
    def register(self):
    #----------------------------------------------------------------------
        # create supported endpoints
        my_view = self.as_view(self.endpoint, **self.kwargs)
        app.add_url_rule('/{}'.format(self.endpoint),view_func=my_view,methods=['GET',])
        app.add_url_rule('/{}/rest'.format(self.endpoint),view_func=my_view,methods=['GET', 'POST'])

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
                'order': [0,'asc']
            }

            # buttons just names the buttons to be included, in what order
            buttons = [ 
                        { 'extend':'start', 
                          'url': '{}/rest?action=start'.format(url_for('resultsanalysisstatus')),
                          'statusurl': '{}/rest'.format(url_for('resultsanalysisstatus')) 
                        },
                        { 'extend':'cancel', 
                          'url': '{}/rest?action=cancel'.format(url_for('resultsanalysisstatus')), 
                          'enabled': False 
                        },
                      ]


            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html', 
                                         pagename=self.pagename,
                                         pagejsfiles=addscripts(['resultanalysis.js', 'datatables.js']),
                                         tabledata=tabledata, 
                                         tablebuttons = buttons,
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
            taskfile = '{}/{}-task.id'.format(app.config['MEMBERSHIP_DIR'], clubslug)
            
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
        # app.logger.debug('task.state={} task.info={}'.format(task.state, task.info))

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
            taskfile = '{}/{}-task.id'.format(app.config['MEMBERSHIP_DIR'], clubslug)

            # check action
            action = request.args.get('action')

            # start task
            if action == 'start':
                # if taskfile exists, make believe it was just started and return
                try:
                    with open(taskfile) as tf:
                        task_id = tf.read()
                    db.session.commit()
                    return jsonify({'success': True, 'task_id': task_id}), 202, {}

                # taskfile doesn't exist. this is the normal path -- ignore the exception
                except IOError:
                    pass

                # TODO: do proper oauth to get user access token
                rakey = ApiCredentials.query.filter_by(name='raprivuser').first().key

                # note extra set of {{service}} brackets, which will be replace by service name
                detailfile = '{}/{}-{{service}}-detail.csv'.format(app.config['MEMBERSHIP_DIR'], clubslug)

                # set debugrace to False if not debugging
                debugrace = True
                if debugrace:
                    racefile = '{}/{}-{{service}}-race.csv'.format(app.config['MEMBERSHIP_DIR'], clubslug)
                else:
                    racefile = None

                # convert members to file-like list
                # filefields and dbattrs are used to convert db to file format
                filefields = 'GivenName,FamilyName,DOB,Gender'.split(',')
                dbattrs = 'fname,lname,dateofbirth,gender'.split(',')
                memberfile = wlist()
                OUT = csv.DictWriter(memberfile, filefields)
                OUT.writeheader()
                members = Runner.query.filter_by(club_id=club_id, member=True, active=True)
                mapping = dict(zip(dbattrs, filefields))
                for member in members:
                    filerow = {}
                    for dbattr in mapping:
                        filerow[mapping[dbattr]] = getattr(member, dbattr)
                    OUT.writerow(filerow)

                # kick off analysis task
                task = analyzeresultstask.apply_async((club_id, memberfile, detailfile, taskfile, racefile), queue='longtask')

                # save taskfile
                with open(taskfile,'w') as tf:
                    tf.write(task.id)

                # we've started
                db.session.commit()
                return jsonify({'success': True, 'task_id': task.id}), 202, {}

            # cancel indicated task
            elif action == 'cancel':
                task_id = request.args.get('task_id')
                os.remove(taskfile)
                celery.control.revoke(task_id, terminate=True)
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

course_dbattrs = 'id,name,source,sourceid,date,distmiles,distkm,surface,location,raceid'.split(',')
course_formfields = 'rowid,name,source,sourceid,date,distmiles,distkm,surface,location,raceid'.split(',')
course_dbmapping = OrderedDict(zip(course_dbattrs, course_formfields))
course_formmapping = OrderedDict(zip(course_formfields, course_dbattrs))
course = CrudApi(pagename = 'Courses', 
             endpoint = 'courses', 
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
             byclub = False, 
             idSrc = 'rowid', 
             buttons = ['create', 'edit', 'remove'])
course.register()

#----------------------------------------------------------------------
def getservicename(service):
#----------------------------------------------------------------------
    apicredential = ApiCredentials.query.filter_by(id=service.apicredentials_id).first()
    servicename = apicredential.name
    return servicename

#----------------------------------------------------------------------
def getservicekey(service):
#----------------------------------------------------------------------
    apicredential = ApiCredentials.query.filter_by(id=service.apicredentials_id).first()
    servicekey = apicredential.key
    return servicekey

#----------------------------------------------------------------------
@celery.task(bind=True)
def analyzeresultstask(self, club_id, memberfile, detailfile, taskfile, racefile):
#----------------------------------------------------------------------
    
    try:
        # how many members? Note memberfile always comes as list, with a header line
        nummembers = len(memberfile) - 1

        # collect all the data
        # each service creates a detailed file
        clubservices = RaceResultService.query.filter_by(club_id = club_id).all()
        status = {}
        for service in clubservices:
            # TODO: read memberfile to see how many members there are
            status[getservicename(service)] = {'status': 'not started', 'lastname': '', 'processed': 0, 'total': nummembers}

        for service in clubservices:
            servicename = getservicename(service)
            key = getservicekey(service)
            thisdetailfile = detailfile.format(service=servicename)

            # debug file with race information
            if racefile:
                thisracefile = racefile.format(service=servicename)
            else:
                thisracefile = None
            
            status[servicename]['status'] = 'collecting'
            collectservices[servicename](self, club_id, memberfile, thisdetailfile, thisracefile, status, key=key)

        # add data to database from all the services which were collected

        # compile the data into summary from database, deduplicating for the summary information
        # NOTE: because this is a summary, this cannot be filtered, e.g., by date range
        #       so this is fixed a three year window


        for service in clubservices:
            status[getservicename(service)]['status'] = 'completed'

        # not in a task any more
        os.remove(taskfile)
        
        # save all our work
        db.session.commit()
        return {'progress':status}

    except:
        # not in a task any more
        os.remove(taskfile)

        # roll back database updates and close transaction
        db.session.rollback()

        # tell the admins that this happened
        celery.mail_admins('[scoretility] importtaskresults: exception occurred', traceback.format_exc())

        # report this as success, but since traceback is present, server will tell user
        app.logger.error(traceback.format_exc())
        return {'progress':status, 'traceback': traceback.format_exc()}


