    // managemembers
    function managemembers( writeallowed, toolscontent ) {
        var tools = new EditorButtonDialog({
            content: toolscontent,
            accordian: false,
        });

        var btn = _dt_table.button( 'tools:name' );
        tools.position({
           my: "left top",
           at: "middle bottom",
           of: btn.node()
        });
        btn.action( function( object, dtapi, button, cnf ){
            tools.click();
        } );

        // retrieve service information for club id selected
        var clubid = $('#club_select').val();
        $.ajax({
            type: 'POST',
            url: '/admin/_clubservice/query?id='+clubid,
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

        // create background post data handler for member update by file
        var import_file_background = new BackgroundPostDataManager({
            urlpath: $('#managemembersImport').attr('_rrwebapp-formaction'),
            get_postdata: function() {
                return new FormData($('#import-members')[0]);
            },
        });

        var $importmembers = $('#managemembersImport');
        $importmembers.click( function( event ) {
            event.preventDefault();
            import_file_background.post(false);
            tools.close();
        });

        // create background post data handler for member update by service
        var import_service_background = new BackgroundPostDataManager({
            urlpath: $('#managemembersImportApi').attr('_rrwebapp-formaction'),
            urlparams: {'useapi': true},
        });

        // handle Download from Service button within Import dialog
        var $importmembersapi = $('#managemembersImportApi');
        $importmembersapi.click( function( event ) {
            event.preventDefault();
            // reload page after api import. Note if importing file (above) reload
            // handling is in ajax_import_file_resp
            import_service_background.post(false);
            tools.close();
        });
    };  // managemembers
