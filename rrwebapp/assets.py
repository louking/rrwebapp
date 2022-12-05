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
jq_ver = '3.6.0'
jq_ui_ver = '1.13.2'


# dataTables
dt_datatables_ver = '1.13.1'
dt_editor_ver = '2.0.10'
dt_buttons_ver = '2.3.3'
dt_fixedcolumns_ver = '4.2.1'
dt_responsive_ver = '2.4.0'
dt_select_ver = '1.5.0'
dt_editor_plugin_fieldtype_ver = '?'
dt_datetime_ver = '1.2.0'

# select2
# NOTE: patch to jquery ui required, see https://github.com/select2/select2/issues/1246#issuecomment-17428249
# currently in datatables.js
s2_ver = '4.0.13'

# selectize
sz_ver = '0.13.3'

# smartmenus
sm_ver = '1.1.1'

# yadcf
yadcf_ver = '0.9.4.beta.27'

# lodash
lodash_ver = '4.17.21'      # lodash.js (see https://lodash.com)

# d3
d3_cdn = 'https://d3js.org'
d3_ver = '6.7.0'
d3_sc_ver = '2.0.0'    # d3-scale-chromatic

# fontawsome
fa_ver = '5.13.0'           # https://fontawesome.com/

asset_bundles = {
    'admin_js' : Bundle(
        f'js/jquery-{jq_ver}/jquery.js',

        f'js/jQueryUI-{jq_ui_ver}/jquery-ui.js',

        f'js/smartmenus-{sm_ver}/jquery.smartmenus.js',
        f'js/lodash-{lodash_ver}/lodash.js',

        f'js/DataTables-{dt_datatables_ver}/js/jquery.dataTables.js',
        f'js/DataTables-{dt_datatables_ver}/js/dataTables.jqueryui.js',

        f'js/Buttons-{dt_buttons_ver}/js/dataTables.buttons.js',
        f'js/Buttons-{dt_buttons_ver}/js/buttons.jqueryui.js',
        f'js/Buttons-{dt_buttons_ver}/js/buttons.html5.js',
        f'js/Buttons-{dt_buttons_ver}/js/buttons.colVis.js',
        f'js/DateTime-{dt_datetime_ver}/js/dataTables.dateTime.js',
        f'js/Responsive-{dt_responsive_ver}/js/dataTables.responsive.js',
        f'js/Responsive-{dt_responsive_ver}/js/responsive.jqueryui.js',

        f'js/FixedColumns-{dt_fixedcolumns_ver}/js/dataTables.fixedColumns.js',
        f'js/Editor-{dt_editor_ver}/js/dataTables.editor.js',
        f'js/Editor-{dt_editor_ver}/js/editor.jqueryui.js',

        f'js/Select-{dt_select_ver}/js/dataTables.select.js',

        # select2 is required for use by Editor forms
        f'js/select2-{s2_ver}/js/select2.full.js',
        # the order here is important
        'js/FieldType-Select2/editor.select2.js',

        # selectize is required for use by Editor forms
        f'js/selectize-{sz_ver}/js/standalone/selectize.js',
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.js
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.css
        'js/FieldType-Selectize/editor.selectize.js',

        f'js/yadcf-{yadcf_ver}/jquery.dataTables.yadcf.js',

        f'js/d3-{d3_ver}/d3.js',
        f'js/d3-scale-chromatic-{d3_sc_ver}/d3-scale-chromatic.js',

        # these need to be before datatables.js is loaded
        'js/jquery.ui.dialog-clickoutside.js', # from https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside
        'editor-saeditor.js',                       # from loutilities
        'utils.js',                                 # from loutilities
        'layout.js',
        'beforedatatables.js',

        'datatables.js',                            # from loutilities

        # these need to be after datatables.js is loaded
        'datatables.dataRender.ellipsis.js',        # from loutilities
        'background-post-data-manager.js',          # from loutilities
        'managemembers.js',
        'downloadresults.js',
        'RaceResults.js',

        output='gen/admin.js',
        filters='jsmin',
    ),

    'admin_css': Bundle (
        f'js/jQueryUI-{jq_ui_ver}/themes/base/jquery-ui.css',
        # f'js/jquery-ui-{jq_ui_ver}/themes/base/jquery-ui.structure.css',
        f'js/jQueryUI-{jq_ui_ver}/themes/base/theme.css',
        f'js/smartmenus-{sm_ver}/css/sm-core-css.css',
        f'js/smartmenus-{sm_ver}/css/sm-blue/sm-blue.css',
        f'js/DataTables-{dt_datatables_ver}/css/dataTables.jqueryui.css',
        f'js/Buttons-{dt_buttons_ver}/css/buttons.jqueryui.css',
        f'js/DateTime-{dt_datetime_ver}/css/dataTables.dateTime.css',
        f'js/FixedColumns-{dt_fixedcolumns_ver}/css/fixedColumns.jqueryui.css',
        f'js/Editor-{dt_editor_ver}/css/editor.jqueryui.css',
        f'js/Responsive-{dt_responsive_ver}/css/responsive.jqueryui.css',
        f'js/Select-{dt_select_ver}/css/select.jqueryui.css',
        f'js/select2-{s2_ver}/css/select2.css',
        f'js/selectize-{sz_ver}/css/selectize.css',
        'js/FieldType-Selectize/editor.selectize.css',
        f'js/yadcf-{yadcf_ver}/jquery.dataTables.yadcf.css',
        f'js/fontawesome-{fa_ver}/css/fontawesome.css', 
        f'js/fontawesome-{fa_ver}/css/solid.css', 
        'jqueryui.theme.adjust.css',    # loutilities
        'datatables.css',               # loutilities
        'editor.css',                   # loutilities
        'filters.css',                  # loutilities
        'branding.css',                 # loutilities
        'style.css',
        output='gen/admin.css',
        # cssrewrite helps find image files when ASSETS_DEBUG = False
        filters=['cssrewrite', 'cssmin'],
    )
}

asset_env = Environment()
