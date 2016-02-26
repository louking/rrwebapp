// generic datatables / Editor handling
// data, dt_options, ed_options are objects
// buttons is a JSON parsable string, as it references editor which hasn't been instantiated yet
function datatables(data, buttons, dt_options, ed_options) {
    var has_editor = false
    if (ed_options !== undefined) {
        has_editor = true
    }

    if (has_editor) {
        $.extend(ed_options,{table:'#datatable'})
        var editor = new $.fn.dataTable.Editor ( ed_options );
    }

    var button_options = [];
    for (i=0; i<buttons.length; i++) {
        button = buttons[i];
        if ($.inArray(button, ['create', 'edit', 'remove'])) {
            button_options.push({extend:button, editor:editor});
        } else {
            button_options.push(button);
        }
    };

    jQuery.extend(dt_options, {data:data, buttons:button_options});
    var table = $('#datatable').DataTable ( dt_options );

}