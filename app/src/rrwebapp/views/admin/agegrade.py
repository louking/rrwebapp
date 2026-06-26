"""views for age grade table management
"""

# standard
from datetime import datetime
from numbers import Number

# pypi
from flask import url_for, request, jsonify
from flask.views import MethodView
from loutilities.tables import get_request_data, get_request_action, apimethod, dt_editor_response
from loutilities.timeu import asctime
import pandas as pd

# home grown
from . import bp
from ...crudapi import CrudApi
from ...accesscontrol import owner_permission
from ...model import db, AgeGradeTable, AgeGradeFactor, AgeGradeCategory

class parameterError(Exception): pass

# age grade table view
agtable_dbattrs = 'id,name,last_update'.split(',')
agtable_formfields = 'rowid,name,last_update'.split(',')
agtable_dbmapping = dict(list(zip(agtable_dbattrs, agtable_formfields)))
agtable_formmapping = dict(list(zip(agtable_formfields, agtable_dbattrs)))

displaytime = asctime('%Y-%m-%d %H:%M:%S')
agtable_formmapping['last_update'] = lambda r: displaytime.dt2asc(r.last_update) if r.last_update else ''

agtable_view = CrudApi(
    app = bp,
    pagename = 'Age Grade Tables',
    endpoint = 'admin.ag_tables',
    rule = '/ag_tables',
    dbmapping = agtable_dbmapping,
    formmapping = agtable_formmapping,
    writepermission = owner_permission.can,
    dbtable = AgeGradeTable,
    clientcolumns = [
       {'data': 'name', 'name': 'name', 'label': 'Table Name'},
       {'data': 'last_update', 'name': 'last_update', 'label': 'Last Update', 'type': 'readonly'},
    ],
    serverside = False,
    byclub = False,
    idSrc = 'rowid',
    buttons = lambda: [
        'create',
        'editRefresh',
        'remove',
        {
            'text': 'Import Factors',
            'name': 'import-factors',
            'editor': {'eval': 'agegrade_import_saeditor.saeditor'},
            'url': url_for('admin.importagfactors'),
            'action': f'agegrade_import_button("{url_for("admin.importagfactors")}")',
        },
        {
            'text': 'Display Table',
            'name': 'display-table',
            'action': f'agegrade_display_button("{url_for("admin.displayagfactors")}")',
        },
        {
            'text': 'Copy Table',
            'name': 'copy-table',
            'action': f'agegrade_copy_button("{url_for("admin.copyagfactors")}")',
        },
    ]
    )
agtable_view.register()


# import age grade api
class ImportAgeGradeFactorsApi(MethodView):

    def permission(self):
        '''
        determine if current user is permitted to use the view
        '''
        # adapted from loutilities.tables.DbCrudApiRolePermissions
        allowed = False

        # must have factortable_id query arg
        if request.args.get('factortable_id', False):
            if owner_permission.can():
                allowed = True

        return allowed

    def rollback(self):
        db.session.rollback()
        
    @apimethod
    def get(self):
        # verify ag_table exists, else exception is raised
        factortable_id = request.args['factortable_id']
        factortable = AgeGradeTable.query.filter_by(id=factortable_id).one()

        return jsonify(table=factortable.name)

    @apimethod
    def post(self):
        # there should be one 'id' in this form data, 'keyless'
        requestdata = get_request_data(request.form)
        action = get_request_action(request.form)
        
        factortable_id = request.args['factortable_id']
        factortable = AgeGradeTable.query.filter_by(id=factortable_id).one()
        
        gender = requestdata['keyless']['gender']
        surface = requestdata['keyless']['type']
        filename = requestdata['keyless']['file']
        
        self._fielderrors = []
        
        if action == 'import':
            # check parameters
            for field in ['gender', 'type', 'file']:
                if not requestdata['keyless'][field]:
                    self._fielderrors.append({'name': field, 'status': 'please supply'})
            if self._fielderrors:
                raise parameterError('field errors occurred')

            fileext = filename.split('.')[-1]
            
            if fileext in ['xlsx', 'xls']:
                # import [flask_uploads] agfactors here so we don't have circular import
                from ... import agfactors
                filepath = agfactors.path(filename)
                xl = pd.ExcelFile(filepath)
                sheets = xl.sheet_names
                factors = pd.read_excel(xl, sheets[0])
            else:
                raise parameterError(f'invalid file type: {fileext}')
            
            # set df column labels based on distance in km, row (index) labels based on value in 1st column
            # distrow = factors[factors.iloc[:, 0]=='Distance'].index.values[0]
            indexes = [e.lower() if isinstance(e, str) else e for e in factors.iloc[:, 0]]
            factors.index = indexes
            # factors.columns = factors.iloc[distrow]
            factors.columns = factors.loc['distance']
            ages = [i for i in factors.index if type(i)==int]
            distances = [c for c in factors.columns if isinstance(c, Number)]
            
            for dist in distances:
                # update open standard table
                dist_mm = int(dist*1000000) # mm = km * 1,000,000
                category = AgeGradeCategory.query.filter_by(factortable=factortable, gender=gender, surface=surface, dist_mm=dist_mm).one_or_none()
                if not category:
                    category = AgeGradeCategory(factortable=factortable, gender=gender, surface=surface, dist_mm=dist_mm)
                    db.session.add(category)
                    db.session.flush()
                category.oc_secs = factors.at['oc sec', dist]
                
                # update factors table
                for age in ages:
                    factor = AgeGradeFactor.query.filter_by(category=category, age=age).one_or_none()
                    if not factor:
                        factor = AgeGradeFactor(category=category, age=age)
                        db.session.add(factor)
                    factor.factor = factors.at[age, dist]
            
        elif action == 'clear':
            filterby = {}
            filterby['factortable'] = factortable
            if gender:
                filterby['gender'] = gender
            if surface:
                filterby['surface'] = surface
            categories = AgeGradeCategory.query.filter_by(**filterby).all()
            for category in categories:
                AgeGradeFactor.query.filter_by(category=category).delete()
                db.session.delete(category)
        
        else:
            raise parameterError(f'invalid action received: {action}')

        # use age grade table's view's dte to get the response data
        factortable.last_update = datetime.now()
        thisrow = agtable_view.dte.get_response_data(factortable)
        self._responsedata = [thisrow]
        
        # update database
        db.session.commit()
        
        return dt_editor_response(data=self._responsedata)

bp.add_url_rule('/_importagfactors/rest', view_func=ImportAgeGradeFactorsApi.as_view('importagfactors'), methods=['GET', 'POST'])


# display age grade factors api
class AgFactorsDisplayApi(MethodView):

    def permission(self):
        return owner_permission.can()

    def rollback(self):
        pass

    @apimethod
    def get(self):
        factortable_id = request.args.get('factortable_id')
        gender = request.args.get('gender', 'M')
        surface = request.args.get('surface', 'road')

        factortable = AgeGradeTable.query.filter_by(id=factortable_id).one()
        categories = (AgeGradeCategory.query
                      .filter_by(factortable_id=factortable_id, gender=gender, surface=surface)
                      .order_by(AgeGradeCategory.dist_mm)
                      .all())

        distances = [cat.dist_mm for cat in categories]
        oc_secs = {str(cat.dist_mm): cat.oc_secs for cat in categories}
        factors = {}
        for cat in categories:
            for fac in cat.factors:
                if fac.age not in factors:
                    factors[fac.age] = {}
                factors[fac.age][cat.dist_mm] = fac.factor

        ages = sorted(factors.keys())

        return jsonify(
            name=factortable.name,
            gender=gender,
            surface=surface,
            distances=distances,
            oc_secs=oc_secs,
            ages=ages,
            factors={str(age): {str(d): v for d, v in factors[age].items()} for age in ages},
        )

bp.add_url_rule('/_agfactors/display', view_func=AgFactorsDisplayApi.as_view('displayagfactors'), methods=['GET'])


# copy age grade table api
class CopyAgeGradeTableApi(MethodView):

    def permission(self):
        return owner_permission.can()

    def rollback(self):
        db.session.rollback()

    @apimethod
    def post(self):
        factortable_id = request.args.get('factortable_id')
        new_name = (request.get_json() or {}).get('new_name', '').strip()

        if not new_name:
            return jsonify(error='new table name is required')

        source = AgeGradeTable.query.filter_by(id=factortable_id).one()

        new_table = AgeGradeTable(name=new_name, last_update=datetime.now())
        db.session.add(new_table)
        db.session.flush()

        for cat in source.categories:
            new_cat = AgeGradeCategory(
                factortable=new_table,
                gender=cat.gender,
                surface=cat.surface,
                dist_mm=cat.dist_mm,
                oc_secs=cat.oc_secs,
            )
            db.session.add(new_cat)
            db.session.flush()
            for fac in cat.factors:
                db.session.add(AgeGradeFactor(category=new_cat, age=fac.age, factor=fac.factor))

        db.session.commit()

        thisrow = agtable_view.dte.get_response_data(new_table)
        return dt_editor_response(data=[thisrow])

bp.add_url_rule('/_agfactors/copy', view_func=CopyAgeGradeTableApi.as_view('copyagfactors'), methods=['POST'])

