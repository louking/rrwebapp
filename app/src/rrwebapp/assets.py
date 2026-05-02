"""
assets - create js and css asset bundles
--------------------------------------------
"""

# pypi
from flask_assets import Bundle, Environment

# jquery
jq_ver = '3.7.1'
jq_ui_ver = '1.14.2'

# dataTables
dt_datatables_ver = '2.3.8-pkgs-jqui'

# select2
# NOTE: patch to jquery ui required, see https://github.com/select2/select2/issues/1246#issuecomment-17428249
# currently in datatables.js
s2_ver = '4.0.13'

# selectize
sz_ver = '0.13.3'

# smartmenus
sm_ver = '1.1.1'

# yadcf
yadcf_ver = '2.0.1.beta.9.louking.3'
yadcf_suffix = '-2.0'

# lodash
lodash_ver = '4.17.21'      # lodash.js (see https://lodash.com)

# d3
d3_cdn = 'https://d3js.org'
d3_ver = '7.4.2'
d3_sc_ver = '2.0.0'    # d3-scale-chromatic

# fontawsome
fa_ver = '5.13.0'           # https://fontawesome.com/

asset_bundles = {
    'admin_js' : Bundle(
        f'js/jQuery-{jq_ver}/jquery-{jq_ver}.js',
        f'js/jquery-ui-{jq_ui_ver}.custom/jquery-ui.js',

        f'js/smartmenus-{sm_ver}/jquery.smartmenus.js',
        f'js/lodash-{lodash_ver}/lodash.js',

        f'js/DataTables-{dt_datatables_ver}/datatables.js',

        # select2 is required for use by Editor forms
        f'js/select2-{s2_ver}/js/select2.full.js',
        # the order here is important
        'js/FieldType-Select2/editor.select2-v4.js',

        # selectize is required for use by Editor forms
        f'js/selectize-{sz_ver}/js/standalone/selectize.js',
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.js
        #   https://editor.datatables.net/plug-ins/download?cdn=cdn-download&amp;q=field-type/editor.selectize.min.css
        'js/FieldType-Selectize/editor.selectize.js',

        f'js/yadcf-{yadcf_ver}/jquery.dataTables.yadcf{yadcf_suffix}.js',

        f'js/d3-{d3_ver}/d3.js',
        f'js/d3-scale-chromatic-{d3_sc_ver}/d3-scale-chromatic.js',

        # these need to be before datatables.js is loaded
        'js/jquery.ui.dialog-clickoutside.js', # from https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside
        'mutex-promise.js',                          # from loutilities
        'editor-saeditor.js',                       # from loutilities
        'utils.js',                                 # from loutilities
        'layout.js',
        'beforedatatables.js',

        'datatables.js',                            # from loutilities

        # these need to be after datatables.js is loaded
        'afterdatatables.js',
        'datatables.dataRender.ellipsis.js',        # from loutilities
        'editor.buttons.editrefresh.js',            # from loutilities
        'background-post-data-manager.js',          # from loutilities
        'managemembers.js',
        'downloadresults.js',
        'RaceResults.js',

        output='gen/admin.js',
        filters='jsmin',
    ),

    'admin_css': Bundle (
        f'js/jquery-ui-{jq_ui_ver}.custom/jquery-ui.css',
        f'js/jquery-ui-{jq_ui_ver}.custom/jquery-ui.structure.css',
        f'js/jquery-ui-{jq_ui_ver}.custom/jquery-ui.theme.css',
        
        f'js/DataTables-{dt_datatables_ver}/datatables.css',

        f'js/smartmenus-{sm_ver}/css/sm-core-css.css',
        f'js/smartmenus-{sm_ver}/css/sm-blue/sm-blue.css',
        
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
