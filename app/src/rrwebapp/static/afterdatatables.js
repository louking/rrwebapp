// note there are definitions for afterdatatabases() also in other .js files

if (location.pathname.includes('/ag_tables')) {
    function afterdatatables() {
        agegrade_import_saeditor.init();

        // Row-dependent buttons are only enabled when a row is selected
        _dt_table.button('import-factors:name').disable();
        _dt_table.button('display-table:name').disable();
        _dt_table.button('copy-table:name').disable();
        _dt_table.on('select deselect', function(e, dt, type, indexes) {
            var ids = _dt_table.rows({selected:true}).ids();
            if (ids.length == 0) {
                _dt_table.button('import-factors:name').disable();
                _dt_table.button('display-table:name').disable();
                _dt_table.button('copy-table:name').disable();
            } else {
                _dt_table.button('import-factors:name').enable();
                _dt_table.button('display-table:name').enable();
                _dt_table.button('copy-table:name').enable();
            }
        });
    }

} else if (location.pathname.includes('/resultschart')) {
    function afterdatatables() {
        // give table special classes
        $( "#datatable_wrapper" ).addClass("dt-chart-table dt-chart-tabledisplay dt-hide");

        // TODO: hack to hide copyright which I'm having trouble positioning correctly
        $( ".Footer" ).hide();
    }
}
