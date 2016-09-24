###########################################################################################
# services - external service access
#
#       Date            Author          Reason
#       ----            ------          ------
#       09/23/16        Lou King        Create
#
#   Copyright 2016 Lou King.  All rights reserved
#
###########################################################################################

# standard
from urllib import urlencode
import traceback

# pypi
import flask
from flask import make_response, request, jsonify, url_for
from flask.ext.login import login_required
from flask.views import MethodView
from datatables import DataTables, ColumnDT
from collections import OrderedDict

# home grown
from . import app
import racedb
from accesscontrol import owner_permission, ClubDataNeed, UpdateClubDataNeed, ViewClubDataNeed, \
                                    UpdateClubDataPermission, ViewClubDataPermission
from database_flask import db   # this is ok because this module only runs under flask
from apicommon import failure_response, success_response
from request import addscripts

# module specific needs
from racedb import ApiCredentials
from datatables_editor import DataTablesEditor, dt_editor_response, get_request_action, get_request_data


#######################################################################
class ServiceCredentials(MethodView):
#######################################################################
    decorators = [login_required]

    # set up mapping between database and editor form
    dbattrs = 'id,name,key,secret'.split(',')
    formfields = 'rowid,name,key,secret'.split(',')
    dbmapping = OrderedDict(zip(dbattrs,formfields))
    formmapping = OrderedDict(zip(formfields,dbattrs))
    dte = DataTablesEditor(dbmapping, formmapping)

    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)

            # verify user can write the data, otherwise abort
            if not owner_permission.can():
                db.session.rollback()
                flask.abort(403)
            
            # retrieve apicredentials table
            dbrecords = ApiCredentials.query.all()

            # build table data
            tabledata = []
            for dbrecord in dbrecords:
                thisentry = self.dte.get_response_data(dbrecord)
                tabledata.append(thisentry)

            # DataTables options string, data: and buttons: are passed separately
            dt_options = {
                'dom': '<"H"lBpfr>t<"F"i>',
                'columns': [
                    {
                        'data': None,
                        'defaultContent': '',
                        'className': 'select-checkbox',
                        'orderable': False
                    },
                    { 'data': 'name', 'name': 'name', 'label': 'Service Name' },
                    { 'data': 'key', 'name': 'key', 'label': 'Key', 'render':'$.fn.dataTable.render.text()' }, 
                    { 'data': 'secret', 'name': 'secret', 'label': 'Secret', 'render':'$.fn.dataTable.render.text()' }
                ],
                'select': True,
                'ordering': True,
                'order': [1,'asc']
            }

            ed_options = {
                'idSrc': 'rowid',
                'ajax': url_for('servicecredentials'),
                'fields': [
                    { 'label': 'Service Name:',  'name': 'name' },
                    { 'label': 'Key:',  'name': 'key' },
                    { 'label': 'Secret:',  'name': 'secret' },
                ],
            }

            # buttons just names the buttons to be included, in what order
            buttons = [ 'create', 'edit', 'remove', 'csv' ]


            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('datatables.html', 
                                         pagename='Service Credentials',
                                         pagejsfiles=addscripts(['datatables.js']),
                                         tabledata=tabledata, 
                                         tablebuttons = buttons,
                                         options = {'dtopts': dt_options, 'editoropts': ed_options},
                                         inhibityear=True,
                                         writeallowed=writecheck.can())
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise

    #----------------------------------------------------------------------
    def post(self):
    #----------------------------------------------------------------------
        # prepare for possible errors
        error = ''
        fielderrors = []


        try:
            club_id = flask.session['club_id']
            
            readcheck = ViewClubDataPermission(club_id)
            writecheck = UpdateClubDataPermission(club_id)

            # verify user can write the data, otherwise abort
            if not owner_permission.can():
                db.session.rollback()
                cause = 'operation not permitted for user'
                return dt_editor_response(error=cause)
            
            # handle create, edit, remove
            action = get_request_action(request.form)

            # get data from form
            data = get_request_data(request.form)
            app.logger.debug('action={}, data={}, form={}'.format(action, data, request.form))

            if action not in ['create', 'edit', 'remove']:
                db.session.rollback()
                cause = 'unknown action "{}"'.format(action)
                app.logger.warning(cause)
                return dt_editor_response(error=cause)

            # loop through data
            responsedata = []
            for thisid in data:
                thisdata = data[thisid]
                
                # create item
                if action == 'create':
                    dbitem = ApiCredentials()
                    self.dte.set_dbrow(thisdata, dbitem)
                    app.logger.debug('creating id={}, name={}'.format(thisid,dbitem.name))
                    db.session.add(dbitem)
                    db.session.flush()

                # edit item
                elif action == 'edit':
                    dbitem = ApiCredentials.query.filter_by(id=thisid).first()
                    app.logger.debug('editing id={}, name={}'.format(thisid,dbitem.name))
                    self.dte.set_dbrow(thisdata, dbitem)
                    app.logger.debug('after edit id={}, name={}'.format(thisid,dbitem.name))

                # remove item
                elif action == 'remove':
                    resultid = thisdata['rowid']
                    dbitem = ApiCredentials.query.filter_by(id=thisid).first()
                    app.logger.debug('deleting id={}, name={}'.format(thisid,dbitem.name))
                    db.session.delete(dbitem)

                # prepare response
                if action != 'remove':
                    thisrow = self.dte.get_response_data(dbitem)
                    responsedata.append(thisrow)
                    app.logger.debug('thisrow={}'.format(thisrow))

            # commit database updates and close transaction
            db.session.commit()
            return dt_editor_response(data=responsedata)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            if fielderrors:
                cause = 'please check indicated fields'
            elif error:
                cause = error
            else:
                cause = traceback.format_exc()
                app.logger.error(traceback.format_exc())
            return dt_editor_response(data=[], error=cause, fieldErrors=fielderrors)

#----------------------------------------------------------------------
app.add_url_rule('/servicecredentials',view_func=ServiceCredentials.as_view('servicecredentials'),methods=['GET', 'POST'])
#----------------------------------------------------------------------

