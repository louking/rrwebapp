###########################################################################################
# member - member views for member results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       03/01/14        Lou King        Create
#
#   Copyright 2014 Lou King
#
###########################################################################################

# standard
import json
import csv
import os.path
import time
import tempfile
import os
import traceback

# pypi
import flask
from flask import make_response, request
from flask_login import login_required, current_user
from flask.views import MethodView
from werkzeug.utils import secure_filename

# home grown
from . import app
from . import racedb
from .accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from .database_flask import db   # this is ok because this module only runs under flask
from .apicommon import failure_response, success_response

# module specific needs
from collections import OrderedDict
import csv
from copy import copy
from .racedb import Runner, Club, RaceResult, ApiCredentials
from .forms import MemberForm 
#from runningclub import memberfile   # required for xlsx support
from loutilities.csvu import DictReaderStr2Num
from loutilities import timeu
from running.runsignup import RunSignUp, members2csv as rsu_members2csv
from . import clubmember
from .clubmember import rsu_api2filemapping
from .request import addscripts
from .crudapi import CrudApi
from .datatables_utils import getDataTableParams

# module globals
tYmd = timeu.asctime('%Y-%m-%d')
MINHDR = ['FamilyName','GivenName','Gender','DOB','RenewalDate','ExpirationDate','City','State']

class InvalidUser(Exception): pass

#----------------------------------------------------------------------
def normalizeRAmemberlist(inputstream,filterexpdate=None):
#----------------------------------------------------------------------
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

mm_dbattrs = 'id,name,fname,lname,dateofbirth,gender,hometown,renewdate,expdate,member'.split(',')
mm_formfields = 'rowid,name,fname,lname,dob,gender,hometown,renewal,expiration,member'.split(',')
mm_dbmapping = OrderedDict(list(zip(mm_dbattrs, mm_formfields)))
mm_formmapping = OrderedDict(list(zip(mm_formfields, mm_dbattrs)))

# convert member back / forth
mm_dbmapping['member'] = lambda form: 1 if form['member'] == 'is-member' or form['member'] == 'true' else 0
mm_formmapping['member'] = lambda dbrow: 'is-member' if dbrow.member else 'non-member'

mm = CrudApi(pagename = 'Manage Members',
             template='managemembers.html',
             endpoint = 'managemembers',
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
#                 return flask.redirect(flask.url_for('managemembers'))
    
#             # handle Delete
#             elif request.form['whichbutton'] == 'Delete':
#                 member = Runner.query.filter_by(club_id=club_id,active=True,id=memberid).first()
#                 # db.session.delete(member)   # should we allow member deletion?  maybe not
#                 member.active = False

#                 # commit database updates and close transaction
#                 db.session.commit()
#                 return flask.redirect(flask.url_for('managemembers'))

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
#                 return flask.redirect(flask.url_for('managemembers'))
            
#         except:
#             # roll back database updates and close transaction
#             db.session.rollback()
#             raise
# #----------------------------------------------------------------------
# app.add_url_rule('/membersettings/<int:memberid>',view_func=MemberSettings.as_view('membersettings'),methods=['GET','POST'])
# #----------------------------------------------------------------------

#######################################################################
class AjaxImportMembers(MethodView):
#######################################################################
    decorators = [login_required]
    
    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
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
                    app.logger.error(cause)
                    return failure_response(cause=cause)
                thisapi = ApiCredentials.query.filter_by(name=apitype).first()
                if not thisapi:
                    db.session.rollback()
                    cause = "Unexpected Error: API credentials for '{}' not configured".format(apitype)
                    app.logger.error(cause)
                    return failure_response(cause=cause)
                apikey = thisapi.key
                apisecret = thisapi.secret
                if not apikey or not apisecret:
                    db.session.rollback()
                    cause = "Unexpected Error: API credentials for '{}' not configured with key or secret".format(apitype)
                    app.logger.error(cause)
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
                    app.logger.error(cause)
                    return failure_response(cause=cause)
                if not allowed_file(memberfile.filename):
                    db.session.rollback()
                    cause = 'Invalid file type {} for file {}'.format(ext,memberfile.filename)
                    app.logger.error(cause)
                    return failure_response(cause=cause)

            # get all the member runners currently in the database
            # hash them into dict by (name,dateofbirth)
            allrunners = Runner.query.filter_by(club_id=club_id,member=True,active=True).all()
            inactiverunners = {}
            for thisrunner in allrunners:
                inactiverunners[thisrunner.name,thisrunner.dateofbirth] = thisrunner

            # if some members exist, verify user wants to overwrite
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


            # bring in data from the file
            if ext in ['.xls','.xlsx']:
                members = clubmember.XlClubMember(memberpathname)
            elif ext in ['.csv']:
                members = clubmember.CsvClubMember(memberpathname)
            
            # how did this happen?  check allowed_file() for bugs
            else:
                db.session.rollback()
                cause =  'Program Error: Invalid file type {} for file {} path {} (unexpected)'.format(ext,memberfilename,memberpathname)
                app.logger.error(cause)
                return failure_response(cause=cause)
            
            # remove file and temporary directory
            os.remove(memberpathname)
            try:
                os.rmdir(tempdir)
            # no idea why this can happen; hopefully doesn't happen on linux
            except WindowsError as e:
                app.logger.debug('WindowsError exception ignored: {}'.format(e))

            # get old clubmembers from database
            dbmembers = clubmember.DbClubMember(club_id=club_id)   # use default database

            # prepare for age check
            thisyear = timeu.epoch2dt(time.time()).year
            asofasc = '{}-1-1'.format(thisyear) # jan 1 of current year
            asof = tYmd.asc2dt(asofasc) 
    
            # process each name in new membership list
            allmembers = members.getmembers()
            for name in allmembers:
                thesemembers = allmembers[name]
                # NOTE: may be multiple members with same name
                for thismember in thesemembers:
                    thisname = thismember['name']
                    thisfname = thismember['fname']
                    thislname = thismember['lname']
                    thisdob = thismember['dob']
                    thisgender = thismember['gender'][0].upper()    # male -> M, female -> F
                    thishometown = thismember['hometown']
                    thisrenewdate = thismember['renewdate']
                    thisexpdate = thismember['expdate']
        
                    # prep for if .. elif below by running some queries
                    # handle close matches, if DOB does match
                    age = timeu.age(asof,tYmd.asc2dt(thisdob))
                    matchingmember = dbmembers.findmember(thisname,age,asofasc)
                    dbmember = None
                    if matchingmember:
                        membername,memberdob = matchingmember
                        if memberdob == thisdob:
                            dbmember = racedb.getunique(db.session,Runner,club_id=club_id,member=True,name=membername,dateofbirth=thisdob)
                    
                    # TODO: need to handle case where dob transitions from '' to actual date of birth
                    
                    # no member found, maybe there is nonmember of same name already in database
                    if dbmember is None:
                        dbnonmember = racedb.getunique(db.session,Runner,club_id=club_id,member=False,name=thisname)
                        # TODO: there's a slim possibility that there are two nonmembers with the same name, but I'm sure we've already
                        # bolloxed that up in importresult as there's no way to discriminate between the two
                        
                        ## make report for new members
                        #NEWMEMCSV.writerow({'name':thisname,'dob':thisdob})
                        
                    # see if this runner is a member in the database already, or was a member once and make the update
                    # add or update runner in database
                    # get instance, if it exists, and make any updates
                    found = False
                    if dbmember is not None:
                        thisrunner = Runner(club_id,membername,thisdob,thisgender,thishometown,
                                            fname=thisfname,lname=thislname,
                                            renewdate=thisrenewdate,expdate=thisexpdate)
                        
                        # this is also done down below, but must be done here in case member's name has changed
                        if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                            inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))
        
                        # overwrite member's name if necessary
                        thisrunner.name = thisname  
                        
                        added = racedb.update(db.session,Runner,dbmember,thisrunner,skipcolumns=['id'])
                        found = True
                        
                    # if runner's name is in database, but not a member, see if this runner is a nonmemember which can be converted
                    # Check first result for age against age within the input file
                    # if ages match, convert nonmember to member
                    elif dbnonmember is not None:
                        # get dt for date of birth, if specified
                        try:
                            dob = tYmd.asc2dt(thisdob)
                        except ValueError:
                            dob = None
                            
                        # nonmember came into the database due to a nonmember race result, so we can use any race result to check nonmember's age
                        if dob:
                            result = RaceResult.query.filter_by(runnerid=dbnonmember.id).first()
                            resultage = result.agage
                            racedate = tYmd.asc2dt(result.race.date)
                            expectedage = timeu.age(racedate,dob)
                            #expectedage = racedate.year - dob.year - int((racedate.month, racedate.day) < (dob.month, dob.day))
                        
                        # we found the right person, always if dob isn't specified, but preferably check race result for correct age
                        if dob is None or resultage == expectedage:
                            thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                                fname=thisfname,lname=thislname,
                                                renewdate=thisrenewdate,expdate=thisexpdate)
                            added = racedb.update(db.session,Runner,dbnonmember,thisrunner,skipcolumns=['id'])
                            found = True
                        else:
                            app.logger.warning('{} found in database, wrong age, expected {} found {} in {}'.format(thisname,expectedage,resultage,result))
                            # TODO: need to make file for these, also need way to force update, because maybe bad date in database for result
                            # currently this will cause a new runner entry
                    
                    # if runner was not found in database, just insert new runner
                    if not found:
                        thisrunner = Runner(club_id,thisname,thisdob,thisgender,thishometown,
                                            fname=thisfname,lname=thislname,
                                            renewdate=thisrenewdate,expdate=thisexpdate)
                        added = racedb.insert_or_update(db.session,Runner,thisrunner,skipcolumns=['id'],club_id=club_id,name=thisname,dateofbirth=thisdob)
                        
                    # remove this runner from collection of runners which should be deactivated in database
                    if (thisrunner.name,thisrunner.dateofbirth) in inactiverunners:
                        inactiverunners.pop((thisrunner.name,thisrunner.dateofbirth))
                
            # any runners remaining in 'inactiverunners' should be deactivated
            for (name,dateofbirth) in inactiverunners:
                thisrunner = Runner.query.filter_by(club_id=club_id,name=name,dateofbirth=dateofbirth).first() # should be only one returned by filter
                thisrunner.active = False
        
            # commit database updates and close transaction
            db.session.commit()
            return success_response()
        
        except Exception as e:
            # roll back database updates and close transaction
            db.session.rollback()
            cause = traceback.format_exc()
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_importmembers',view_func=AjaxImportMembers.as_view('_importmembers'),methods=['POST'])
#----------------------------------------------------------------------

#######################################################################
class AjaxLoadMembers(MethodView):
#######################################################################
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
   
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
            app.logger.error(traceback.format_exc())
            return failure_response(cause=cause)
#----------------------------------------------------------------------
app.add_url_rule('/_loadmembers',view_func=AjaxLoadMembers.as_view('_loadmembers'),methods=['GET'])
#----------------------------------------------------------------------

