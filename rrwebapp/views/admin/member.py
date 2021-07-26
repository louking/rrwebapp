"""
member - member views for member results web application
==========================================================
"""

# standard
import json
import csv
import os.path
import tempfile
import os
import traceback
from collections import OrderedDict
import csv
from copy import copy

# pypi
import flask
from flask import request, current_app, url_for, jsonify
from flask_login import login_required, current_user
from flask.views import MethodView
from werkzeug.utils import secure_filename
from loutilities.csvwt import wlist
from loutilities.timeu import asctime
from running.runsignup import members2csv as rsu_members2csv

# home grown
from . import bp
from ...model import db
from ...accesscontrol import UpdateClubDataPermission, ViewClubDataPermission
from ...apicommon import failure_response, success_response
from ...model import Runner, Club, ApiCredentials
from ...forms import MemberForm 
from ...tasks import importmemberstask
from ...clubmember import rsu_api2filemapping
from ...crudapi import CrudApi
from ...datatables_utils import getDataTableParams
from ...version import __docversion__

# module globals
tYmd = asctime('%Y-%m-%d')
MINHDR = ['FamilyName','GivenName','Gender','DOB','RenewalDate','ExpirationDate','City','State']

class InvalidUser(Exception): pass

def normalizeRAmemberlist(inputstream,filterexpdate=None):
    '''
    Take RunningAHEAD membership list (Export individual membership records), and produce member list.
    For a given expiration date, the earliest renewal date is used
    This allows "first renewal for year" computations
    
    :param inputstream: open file with csv exported from RunningAHEAD (e.g., from request.files['file'].stream)
    :param filterexpdate: yyyy-mm-dd for expiration date to filter on, else None
    :rtype: csv file data, string format (e.g., data for make_response(data))
    '''

    memberships = csv.DictReader(inputstream)
    members = OrderedDict({})
    
    # for each membership, unique member can be found from combination of names, dob, gender (should be unique)
    # make list of memberships for this member
    for mship in memberships:
        first = mship['GivenName']
        middle = mship['MiddleName']
        last = mship['FamilyName']
        gender = mship['Gender']
        dob = mship['DOB']
        
        # make list of memberships for this member
        members.setdefault((last,first,middle,dob,gender),[]).append(mship)
    
    # get ready for output
    outdatalist = wlist()
    OUT = csv.DictWriter(outdatalist,MINHDR,extrasaction='ignore')
    OUT.writeheader()
    
    # for each member, find earliest renew date for each expiration date
    for key in members:
        renewbyexp = {}
        thesememberships = members[key]
        for mship in thesememberships:
            thisexpdate = mship['ExpirationDate']
            thisrenewdate = mship['RenewalDate']
            
            # special case for 11/11/2013, FSRC bulk import
            if thisrenewdate =='2013-11-11':
                thisrenewdate = mship['JoinDate']
            
            # optional filter
            if not filterexpdate or thisexpdate == filterexpdate:
                if thisexpdate not in renewbyexp or thisrenewdate < renewbyexp[thisexpdate]:
                    renewbyexp[thisexpdate] = thisrenewdate
        
        # for each expiration date (already filtered appropriately),
        # grab a record, update renewal and expiration dates, then save
        for thisexpdate in renewbyexp:
            outrec = copy(members[key][-1])   # doesn't matter which one, pick the last
            outrec['RenewalDate'] = renewbyexp[thisexpdate]
            outrec['ExpirationDate'] = thisexpdate
            OUT.writerow(outrec)    # note this adds \r\n
    
    # one big string for return data
    outputdata = ''.join(outdatalist)
    return outputdata

#----------------------------------------------------------------------
# managemembers endpoint
#----------------------------------------------------------------------

mm_dbattrs = 'id,name,fname,lname,dateofbirth,estdateofbirth,gender,hometown,renewdate,expdate,member'.split(',')
mm_formfields = 'rowid,name,fname,lname,dob,estdateofbirth,gender,hometown,renewal,expiration,member'.split(',')
mm_dbmapping = OrderedDict(list(zip(mm_dbattrs, mm_formfields)))
mm_formmapping = OrderedDict(list(zip(mm_formfields, mm_dbattrs)))

# convert member back / forth
mm_dbmapping['member'] = lambda form: 1 if form['member'] == 'is-member' or form['member'] == 'true' else 0
mm_formmapping['member'] = lambda dbrow: 'is-member' if dbrow.member else 'non-member'

mm = CrudApi(
    app=bp,
    pagename = 'Manage Members',
    template='managemembers.html',
    endpoint = '.managemembers',
    templateargs={'docversion': __docversion__},
    rule='/managemembers',
    dbmapping = mm_dbmapping, 
    formmapping = mm_formmapping, 
    permission=lambda: UpdateClubDataPermission(flask.session['club_id']).can,
    dbtable = Runner,
    queryparams = { 'active' : True },
    clientcolumns = [
       { 'data': 'name', 'name': 'name', 'label': 'Name' },
       { 'data': 'fname', 'name': 'fname', 'label': 'First Name' },
       { 'data': 'lname', 'name': 'lname', 'label': 'Last Name' },
       { 'data': 'dob', 'name': 'dob', 'label': 'Date of Birth' }, 
       { 'data': 'estdateofbirth', 'name': 'estdateofbirth', 'label': 'Estimated DOB',
           'class': 'TextCenter',
           '_treatment': {'boolean': {'formfield': 'estdateofbirth', 'dbfield': 'estdateofbirth'}},
           'ed': {'def': 'no'},
           },
       { 'data': 'gender', 'name': 'gender', 'label': 'Gender' }, 
       { 'data': 'hometown', 'name': 'hometown', 'label': 'Hometown' }, 
       { 'data': 'renewal', 'name': 'renewal', 'label': 'Renewal Date' }, 
       { 'data': 'expiration', 'name': 'expiration', 'label': 'Expiration Date' }, 
       { 'data': 'member', 'name': 'member', 'label': 'Member' }
    ], 
    servercolumns = None,  # no ajax
    byclub = True, 
    idSrc = 'rowid', 
    buttons = [
        'edit',
        'csv',
        {'name': 'tools', 'text': 'Import'},
    ],
    dtoptions = {
                   'scrollCollapse': True,
                   'scrollX': True,
                   'scrollXInner': "100%",
                   'scrollY': True,
               },
    )
mm.register()

# # NOTE: THIS HAS NOT BEEN TESTED AND IS NOT CURRENTLY USED
# # perhaps some kind of member merge will be required in the future, but editing a member would get overwritten by member import
# #######################################################################
# class MemberSettings(MethodView):
# #######################################################################
#     decorators = [login_required]
#     #----------------------------------------------------------------------
#     def get(self,memberid):
#     #----------------------------------------------------------------------
#         try:
#             club_id = flask.session['club_id']
#             thisyear = flask.session['year']
            
#             readcheck = ViewClubDataPermission(club_id)
#             writecheck = UpdateClubDataPermission(club_id)
            
#             # verify user can at least read the data, otherwise abort
#             if not readcheck.can():
#                 db.session.rollback()
#                 flask.abort(403)
                
#             # memberid == 0 means add
#             if memberid == 0:
#                 if not writecheck.can():
#                     db.session.rollback()
#                     flask.abort(403)
#                 member = Runner(club_id)
#                 form = MemberForm()
#                 action = 'Add'
#                 pagename = 'Add Member'
            
#             # memberid != 0 means update
#             else:
#                 member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
    
#                 # copy source attributes to form
#                 params = {}
#                 for field in vars(member):
#                     params[field] = getattr(member,field)
                
#                 form = MemberForm(**params)
#                 action = 'Update'
#                 pagename = 'Edit Member'
    
#             # commit database updates and close transaction
#             db.session.commit()
#             # delete button only for edit (memberid != 0)
#             return flask.render_template('membersettings.html',thispagename=pagename,
#                                          action=action,deletebutton=(memberid!=0),
#                                          form=form,member=member,writeallowed=writecheck.can())
        
#         except:
#             # roll back database updates and close transaction
#             db.session.rollback()
#             raise
        
#     #----------------------------------------------------------------------
#     def post(self,memberid):
#     #----------------------------------------------------------------------
#         form = MemberForm()

#         try:
#             club_id = flask.session['club_id']
#             thisyear = flask.session['year']

#             # handle Cancel
#             if request.form['whichbutton'] == 'Cancel':
#                 db.session.rollback() # throw out any changes which have been made
#                 return flask.redirect(flask.url_for('.managemembers'))
    
#             # handle Delete
#             elif request.form['whichbutton'] == 'Delete':
#                 member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
#                 # db.session.delete(member)   # should we allow member deletion?  maybe not
#                 member.active = False

#                 # commit database updates and close transaction
#                 db.session.commit()
#                 return flask.redirect(flask.url_for('.managemembers'))

#             # handle Update and Add
#             elif request.form['whichbutton'] in ['Update','Add']:
#                 if not form.validate_on_submit():
#                     return 'error occurred on form submit -- update error message and display form again'
                    
#                 readcheck = ViewClubDataPermission(club_id)
#                 writecheck = UpdateClubDataPermission(club_id)
                
#                 # verify user can at write the data, otherwise abort
#                 if not writecheck.can():
#                     db.session.rollback()
#                     flask.abort(403)
                
#                 # add
#                 if request.form['whichbutton'] == 'Add':
#                     member = Runner(club_id)
#                 # update
#                 else:
#                     member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
                
#                 # copy fields from form to db object
#                 for field in vars(member):
#                     # only copy attributes which are in the form class already
#                     if field in form.data:
#                         setattr(member,field,form.data[field])
                
#                 # add
#                 if request.form['whichbutton'] == 'Add':
#                     db.session.add(member)
#                     db.session.flush()  # needed to update member.id
#                     memberid = member.id    # not needed yet, but here for consistency

#                 # commit database updates and close transaction
#                 db.session.commit()
#                 return flask.redirect(flask.url_for('.managemembers'))
            
#         except:
#             # roll back database updates and close transaction
#             db.session.rollback()
#             raise
# #----------------------------------------------------------------------
# app.add_url_rule('/membersettings/<int:memberid>',view_func=MemberSettings.as_view('membersettings'),methods=['GET','POST'])
# #----------------------------------------------------------------------


class AjaxImportMembers(MethodView):
    decorators = [login_required]
    
    def post(self):
        def allowed_file(filename):
            return '.' in filename and filename.split('.')[-1] in ['csv','xlsx','xls']
    
        try:
            club_id = flask.session['club_id']
            thisyear = flask.session['year']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)
            
            # verify user can write the data, otherwise abort
            if not writecheck.can():
                db.session.rollback()
                flask.abort(403)
            
            # if using api, collect data from api and save in temp directory
            useapi = request.args.get('useapi')=='true'

            # if we're using the api, do some quick checks that the request makes sense
            # save apitype, apiid, apikey, apisecret for later
            if useapi:
                thisclub = Club.query.filter_by(id=club_id).first()
                apitype = thisclub.memberserviceapi
                apiid = thisclub.memberserviceid
                if not apitype or not apiid:
                    db.session.rollback()
                    cause = 'Unexpected Error: API requested but not configured'
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)
                thisapi = ApiCredentials.query.filter_by(name=apitype).first()
                if not thisapi:
                    db.session.rollback()
                    cause = "Unexpected Error: API credentials for '{}' not configured".format(apitype)
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)
                apikey = thisapi.key
                apisecret = thisapi.secret
                if not apikey or not apisecret:
                    db.session.rollback()
                    cause = "Unexpected Error: API credentials for '{}' not configured with key or secret".format(apitype)
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)

            # if we're not using api, file came in with request
            else:
                memberfile = request.files['file']

                # get file extention
                root,ext = os.path.splitext(memberfile.filename)
                
                # make sure valid file
                if not memberfile:
                    db.session.rollback()
                    cause = 'Unexpected Error: Missing file'
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)
                if not allowed_file(memberfile.filename):
                    db.session.rollback()
                    cause = 'Invalid file type {} for file {}'.format(ext,memberfile.filename)
                    current_app.logger.error(cause)
                    return failure_response(cause=cause)

            # if some members exist, verify user wants to overwrite
            allrunners = Runner.query.filter_by(club_id=club_id,member=True,active=True).all()
            if allrunners and not request.args.get('force')=='true':
                db.session.rollback()
                return failure_response(cause='Overwrite members?',confirm=True)
            
            # if we're using the api, collect the member information using the appropriate credentials
            # NOTE: only runsignup supported at this time
            if useapi:
                tempdir = tempfile.mkdtemp()
                memberfilename = 'members.csv'
                ext = '.csv'
                memberpathname = os.path.join(tempdir,memberfilename)
                rsu_members2csv(apiid, apikey, apisecret, rsu_api2filemapping, filepath=memberpathname)

            else:
                # save file for import
                tempdir = tempfile.mkdtemp()
                memberfilename = secure_filename(memberfile.filename)
                memberpathname = os.path.join(tempdir,memberfilename)
                memberfile.save(memberpathname)            

            # start task
            task = importmemberstask.apply_async((club_id, tempdir, memberpathname, memberfilename))

            # commit database updates and close transaction
            db.session.commit()
            return jsonify({'success': True, 'current': 0, 'total':100, 'location': url_for('.importmembersstatus', task_id=task.id)}), 202, {}
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)

bp.add_url_rule('/_importmembers',view_func=AjaxImportMembers.as_view('_importmembers'),methods=['POST'])

class ImportMembersStatus(MethodView):

    def get(self, task_id):
        task = importmemberstask.AsyncResult(task_id)
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
                    response['redirect'] = url_for('.managemembers')
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

bp.add_url_rule('/importmembersstatus/<task_id>',view_func=ImportMembersStatus.as_view('importmembersstatus'), methods=['GET',])


class AjaxLoadMembers(MethodView):
    
    def get(self):
   
        try:
            if not current_user.is_active:
                db.session.rollback()
                cause = "need to be logged in to use this api"
                return failure_response(cause=cause)

            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            
            # verify user can read the data, otherwise abort
            if not readcheck.can():
                db.session.rollback()
                cause = "need to have read permissions to use this api"
                return failure_response(cause=cause)
               
            # get all the runners in the database
            runners = Runner.query.filter_by(club_id=club_id).all()

            # pull out the pertinent data in the runner table
            table = []
            columns = [
                'id',
                'name',
                'fname',
                'lname',
                'dateofbirth',
                'gender',
                'hometown',
                'renewdate',
                'expdate',
                'member',
                'active',
            ]

            for runner in runners:
                row = {}
                for column in columns:
                    row[column] = getattr(runner,column,None)
                table.append(row)

            # commit database updates and close transaction
            db.session.commit()
            return success_response(data=table)
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            current_app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)

bp.add_url_rule('/_loadmembers',view_func=AjaxLoadMembers.as_view('_loadmembers'),methods=['GET'])

