###########################################################################################
# docs - documentation views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/28/14        Lou King        Create
#
#   Copyright 2014 Lou King.  All rights reserved
#
###########################################################################################

# standard
import csv
import os.path

# pypi
import flask
from flask.views import MethodView
from docutils.core import publish_parts

# home grown
from . import app
from .database_flask import db   # this is ok because this module only runs under flask

# module specific needs

#----------------------------------------------------------------------
def publish_fragment(source):
#----------------------------------------------------------------------
    return publish_parts(source,writer_name='html')['fragment']

#######################################################################
class IcdView(MethodView):
#######################################################################
    '''
    icdfile is csv with columns, in the following order
    
    * tablegroup - ``table``,``thead``, ``tbody``, ``tfoot``, ``/table``
    * tablerowclass - comma separated list of classes for row
    * tablecelltype - ``th``, ``td``
    * rest of table's columns in reStructuredText markup format - see http://sphinx-doc.org/rest.html
    
    Rows of text prior to column1 having ``table`` will be rendered before the table.
    
    Rows of of text after the row with ``/table`` in tablegroup column will be rendered after the table.
    
    ``/table`` is optional if no text is to be rendered after the table.
    '''
    
    # inherited class must override these
    icdfile = os.path.join(app.static_folder,'doc','icdtest.csv')
    pagename = 'Test Spec'
    
    #----------------------------------------------------------------------
    def get(self):
    #----------------------------------------------------------------------
        try:
            # use csv reader to understand file contents
            ff = open(self.icdfile, 'r', newline='')
            cc = csv.reader(ff)
            
            # pull in the file text, then close it, remembering table start and end
            tablestart = -1
            tableend = -1
            rows = []
            ndx = 0
            for row in cc:
                rows.append(row)
                if row[0].lower() == 'table':
                    tablestart = ndx+1
                elif row[0].lower() == '/table':
                    tableend = ndx
                ndx += 1
            ff.close()
            
            # table and /table are optional
            if tablestart == -1:
                tablestart = 0
            if tableend == -1:
                tableend = len(rows)
            
            # intro and summary only have text in the first column
            rstintro = '\n'.join([col[0] for col in rows[:tablestart-1]])
            intro = publish_fragment(rstintro)
            rstsummary = '\n'.join([col[0] for col in rows[tableend+1:]])
            summary = publish_fragment(rstsummary)

            # build table dict, assumes all thead before all tbody before all tfoot
            GROUP = 0
            CLASS = 1
            TYPE = 2
            STARTCOL = 3
            groups = ['thead','tbody','tfoot']
            hasgroups = []
            table = {}
            for group in groups:
                table[group] = {'rows':[]}
            for rowndx in range(tablestart,tableend):
                row = rows[rowndx]
                # find row's group
                group = row[GROUP]
                # check if something is out of order
                while groups and group != groups[0]:
                    groups.pop(0)
                if not groups:
                    error = 'invalid tablegroup found in icdfile at row {}'.format(rowndx)
                    break
                
                # all ok, record row
                if group not in hasgroups:
                    hasgroups.append(group)
                table[group]['rows'].append({'class':row[CLASS], 'type':row[TYPE], 'cells':[publish_fragment(cell) for cell in row[STARTCOL:]]})
        
            # commit database updates and close transaction
            db.session.commit()
            return flask.render_template('importspec.html',pagename=self.pagename,groups=hasgroups,intro=intro,table=table,summary=summary,
                                         inhibityear=True,inhibitclub=True)
        
        except:
            # roll back database updates and close transaction
            db.session.rollback()
            raise
#----------------------------------------------------------------------
app.add_url_rule('/doc/_icdtest',view_func=IcdView.as_view('icdtest'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ImportResultsSpec(IcdView):
#######################################################################
    icdfile = os.path.join(app.static_folder,'doc','importresults.csv')
    pagename = 'Import Results File Format'
#----------------------------------------------------------------------
app.add_url_rule('/doc/importresults',view_func=ImportResultsSpec.as_view('doc_importresults'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ImportMembersSpec(IcdView):
#######################################################################
    icdfile = os.path.join(app.static_folder,'doc','importmembers.csv')
    pagename = 'Import Members File Format'
#----------------------------------------------------------------------
app.add_url_rule('/doc/importmembers',view_func=ImportMembersSpec.as_view('doc_importmembers'),methods=['GET'])
#----------------------------------------------------------------------

#######################################################################
class ImportRacesSpec(IcdView):
#######################################################################
    icdfile = os.path.join(app.static_folder,'doc','importraces.csv')
    pagename = 'Import Races File Format'
#----------------------------------------------------------------------
app.add_url_rule('/doc/importraces',view_func=ImportRacesSpec.as_view('doc_importraces'),methods=['GET'])
#----------------------------------------------------------------------
