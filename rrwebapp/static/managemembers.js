    // managemembers
    function managemembers( writeallowed ) {        
        if (writeallowed) {
            // put toolbutton in the right place
            //toolbutton.$widgets.css({height:"0px"});   // no more widgets in container
            
            var $importmembers = $('#managemembersImport');
            $importmembers.click( function( event ) {
                event.preventDefault();
                var url = $(this).attr('_rrwebapp-formaction')
                ajax_import_file(url,'#import-members',false);
            });
        }

        _rrwebapp_table = $('#_rrwebapp-table-manage-members')
            .dataTable(getDataTableParams({scrollY: gettableheight()-10}));
                // -10 because sorting icons shown below headings
        resetDataTableHW();
        
    };  // managemembers

// hold dialog for tools
var toolsdialog;

// set up tools button
function membertools( e, dt, node, config ) {
    toolsdialog = $( '#dialog-tools' ).dialog({
        title: 'Import Members',
        autoOpen: true,
        modal: true,
        minWidth: 475,
        position: { my: 'left top', at: 'center bottom', of: '.import-buttons' }
    });
    // retrieve service information for club id selected
    var clubid = $('#club_select').val();
    $.ajax({
        type: 'POST',
        url: '/_clubservice/query?id='+clubid,
        contentType: false,
        cache: false,
        async: true,
        success: function(data) {
            console.log('Tools button _clubservices response = ' + JSON.stringify(data))
            // only one club requested, so first is ok
            thisclub = data[0];
            // if service configured, let user see service controls
            if (thisclub.service) {
                $( '.importapi' ).show();
            }
        },
        error: function(jqxhr, textstatus, errorthrown) {
            alert('error occurred retrieving club data: ' + textstatus + ' ' + errorthrown);
        },
    });    
}
function setmembertools() {
    $( '#widgets' ).append("\
            <div id='dialog-tools' style='display:none;'>\
                <div class='importapi' style='display:none;'>\
                    <p>Import the member list directly from the configured service</p>\
                    <button id='managemembersImportApi' _rrwebapp-formaction='/_importmembers'>Download from Service</button>\
                </div>\
                <div class='importfile'>\
                  <p>Import the member list from a CSV file. See <a href='/doc/importmembers' target='_blank'>Import Guide</a> for information on the column headers and data format.</p>\
                  <form id='import-members' method='post' enctype='multipart/form-data'>\
                    <input id='choosefileImport' type=file name='file'>\
                    <button id='managemembersImport' _rrwebapp-formaction='/_importmembers'>Import</button>\
                  </form>\
                </div>\
            </div>\
            ")

    // handle Import button within Import dialog
    var $importmembers = $('#managemembersImport');
    $importmembers.click( function( event ) {
        event.preventDefault();
        var url = $(this).attr('_rrwebapp-formaction')
        ajax_import_file(url, '#import-members', false);
        toolsdialog.dialog('close');
    });

    // handle Download from Service button within Import dialog
    var $importmembersapi = $('#managemembersImportApi');
    $importmembersapi.click( function( event ) {
        event.preventDefault();
        var url = $(this).attr('_rrwebapp-formaction')
        // reload page after api import. Note if importing file (above) reload 
        // handling is in ajax_import_file_resp
        ajax_update_db_noform(url, {'useapi':true}, this, false, function() { 
            location.reload(true); 
        }, true);
        toolsdialog.dialog('close');
    });

    return membertools;
}


