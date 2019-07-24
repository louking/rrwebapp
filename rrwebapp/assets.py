###########################################################################################
# assets - create js and css asset bundles
#
#       Date            Author          Reason
#       ----            ------          ------
#       06/07/19        Lou King        Create
#
#   Copyright 2010 Lou King.  All rights reserved
###########################################################################################

# pypi
from flask import current_app
from flask_assets import Bundle, Environment

# jquery
jq_ver = '3.4.1'
jq_ui_ver = '1.12.1'


# dataTables
dt_datatables_ver = '1.10.18'
dt_editor_ver = '1.9.0'
dt_buttons_ver = '1.5.6'
dt_colvis_ver = '1.5.6'
dt_fixedcolumns_ver = '3.2.5'
dt_select_ver = '1.3.0'
dt_editor_plugin_fieldtype_ver = '?'

# select2
# NOTE: patch to jquery ui required, see https://github.com/select2/select2/issues/1246#issuecomment-17428249
# currently in datatables.js
s2_ver = '4.0.7'

# selectize
sz_ver = '0.12.6'

# yadcf
yadcf_ver = '0.9.4.beta.27'

# lodash
lodash_ver = '4.17.11'      # lodash.js (see https://lodash.com)

# d3
d3_cdn = 'https://d3js.org'
d3_ver = '5.9.2'
d3_sc_ver = '1.3.3'    # d3-scale-chromatic

asset_bundles = {
    'admin_js' : Bundle(
        'js/jQuery-{ver}/jquery.js'.format(ver=jq_ver),

        'js/jquery-ui-{ver}.custom/jquery-ui.js'.format(ver=jq_ui_ver),

        'js/lodash-{ver}/lodash.js'.format(ver=lodash_ver),

        'js/DataTables-{ver}/js/jquery.dataTables.js'.format(ver=dt_datatables_ver),
        'js/DataTables-{ver}/js/dataTables.jqueryui.js'.format(ver=dt_datatables_ver),

        'js/Buttons-{ver}/js/dataTables.buttons.js'.format(ver=dt_buttons_ver),
        'js/Buttons-{ver}/js/buttons.jqueryui.js'.format(ver=dt_buttons_ver),
        'js/Buttons-{ver}/js/buttons.html5.js'.format(ver=dt_buttons_ver),
        'js/Buttons-{ver}/js/buttons.colVis.js'.format(ver=dt_colvis_ver),

        'js/FixedColumns-{ver}/js/dataTables.fixedColumns.js'.format(ver=dt_fixedcolumns_ver),
        'js/Editor-{ver}/js/dataTables.editor.js'.format(ver=dt_editor_ver),
        'js/Editor-{ver}/js/editor.jqueryui.js'.format(ver=dt_editor_ver),

        'js/Select-{ver}/js/dataTables.select.js'.format(ver=dt_select_ver),

        # select2 is required for use by Editor forms
        'js/select2-{ver}/js/select2.full.js'.format(ver=s2_ver),
        # the order here is important
        'js/FieldType-Select2/editor.select2.js',

        # selectize is required for use by Editor forms
        'js/selectize-{ver}/js/standalone/selectize.js'.format(ver=sz_ver),
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.js
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.css
        'js/FieldType-Selectize/editor.selectize.js',

        'js/yadcf-{ver}/jquery.dataTables.yadcf.js'.format(ver=yadcf_ver),

        'js/d3-{ver}/d3.js'.format(ver=d3_ver),
        'js/d3-scale-chromatic-{ver}/d3-scale-chromatic.js'.format(ver=d3_sc_ver),

        'js/jquery.ui.dialog-clickoutside.js', # from https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside

        'datatables.js',
        'datatables.dataRender.ellipsis.js',
        'managemembers.js',
        'RaceResults.js',

        output='gen/admin.js',
        filters='jsmin',
    ),

    'admin_css': Bundle (
        'js/jquery-ui-{ver}.custom/jquery-ui.css'.format(ver=jq_ui_ver),
        'js/jquery-ui-{ver}.custom/jquery-ui.structure.css'.format(ver=jq_ui_ver),
        'js/jquery-ui-{ver}.custom/jquery-ui.theme.css'.format(ver=jq_ui_ver),
        'js/DataTables-{ver}/css/dataTables.jqueryui.css'.format(ver=dt_datatables_ver),
        'js/Buttons-{ver}/css/buttons.jqueryui.css'.format(ver=dt_buttons_ver),
        'js/FixedColumns-{ver}/css/fixedColumns.jqueryui.css'.format(ver=dt_fixedcolumns_ver),
        'js/Editor-{ver}/css/editor.jqueryui.css'.format(ver=dt_editor_ver),
        'js/Select-{ver}/css/select.jqueryui.css'.format(ver=dt_select_ver),
        'js/select2-{ver}/css/select2.css'.format(ver=s2_ver),
        'js/selectize-{ver}/css/selectize.css'.format(ver=sz_ver),
        'js/FieldType-Selectize/editor.selectize.css',
        'js/yadcf-{ver}/jquery.dataTables.yadcf.css'.format(ver=yadcf_ver),
        'datatables.css',
        'editor.css',
        'filters.css',
        'branding.css',
        'style.css',
        output='gen/admin.css',
        # cssrewrite helps find image files when ASSETS_DEBUG = False
        filters=['cssrewrite', 'cssmin'],
    )
}

asset_env = Environment()
