// note there are definitions for afterdatatabases() also in other .js files

if (location.pathname.includes('/ag_tables')) {
    function afterdatatables() {
        agegrade_import_saeditor.init();

        // Import Factors button is only enabled when a row is selected
        _dt_table.button('import-factors:name').disable();
        _dt_table.on('select deselect', function(e, dt, type, indexes) {
            var ids = _dt_table.rows({selected:true}).ids();
            if (ids.length == 0) {
                _dt_table.button('import-factors:name').disable();
            } else {
                _dt_table.button('import-factors:name').enable();
            }
        });
    }
}
