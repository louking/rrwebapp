    // layout.html
    $('.sessionoption')
        .on('change',
            function ( event ) {
                var apiurl = $( this ).attr('sessionoptionapi');
                var selected = $( this ).val();
                
                $.ajax({
                    url: $SCRIPT_ROOT + apiurl + '/' + selected,
                    type: 'POST',
                    dataType: 'json',
                    complete: function(data){
                        var success = data.success;
                        location.reload(true);
                        }
                });
            });

    // common
    var toolstatus = 0;
    var $toolbutton = $('.toolbutton');
    var $toolcontent = $('.toolpopup').accordion({
        heightStyle: "content",
        animate: 30,
    })
    var $tooldialog = $('.tooldialog');
    
    function opentoolbutton() {
        $tooldialog.dialog("open");
        $toolcontent.show();
        toolstatus = 1;
    };
    
    function closetoolbutton() {
        $tooldialog.dialog("close");
        $toolcontent.hide();
        toolstatus = 0;
    };
    
    $toolbutton
        .button({ icons: { secondary: "ui-icon-gear" } })
        .on('click',
            function() {
                if (toolstatus == 0) {
                    opentoolbutton()
                } else {
                    closetoolbutton()
                };
            });
    $tooldialog.dialog({
                        dialogClass: "no-titlebar",
                        draggable: false,
                        //resizeable: false,
                        open:$toolcontent,
                        autoOpen: false,
                        height: "auto",
                        width: 450,
                        position:{
                                my: "left top",
                                at: "left bottom",
                                of: $toolbutton
                                },
                        });
    
    // manageraces
    function manageraces() {
        var $filterseries = $('#filterseries');
        $filterseries
            //.selectmenu({ icons: { secondary: "ui-icon-triangle-1-s" } })
            .on('change',
                function() {
                    this.form.submit();
                });
        
        // put toolbutton in the right place
        $toolbutton.position({
            my: "left center",
            at: "right+3 center",
            of: $filterseries,
        });
        
        function ajaximportracesresp(data) {
            console.log(data);
            if (data.success) {
                location.reload(true);
            } else {
                console.log('FAILURE: ' + data.cause);
                // if overwrite requested, force the overwrite
                if (data.confirm) {
                    $("<div>Overwrite year information?</div>").dialog({
                        dialogClass: 'no-titlebar',
                        height: "auto",
                        buttons: [
                            {   text:  'Overwrite',
                                click: function(){
                                    ajaximportraces(true);
                                    $( this ).dialog('destroy');
                                }
                            },{ text:  'Cancel',
                                click: function() {
                                    $( this ).dialog('destroy');
                                }
                            }
                        ],
                    });
                } else {
                    $("<div>Error Occurred: "+data.cause+"</div>").dialog({
                        dialogClass: 'no-titlebar',
                        height: "auto",
                        buttons: [
                            {   text:  'OK',
                                click: function(){
                                    $( this ).dialog('destroy');
                                }
                            }
                        ],
                    });
                };
            };
        };
        
        function ajaximportraces(force) {
            var form_data = new FormData($('#upload-file')[0]);
            
            // force = true means to overwrite existing data for this year
            var url = '/_importraces?force='+force
            
            $.ajax({
                type: 'POST',
                url: url,
                data: form_data,
                contentType: false,
                cache: false,
                processData: false,
                async: false,
                success: ajaximportracesresp,
            });
            
            closetoolbutton();
        };
            
        var $importraces = $('#manageracesImport');
        $importraces.click( function( event ) {
            event.preventDefault();
            ajaximportraces(false);
        });
    
    };  // manageraces
