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
    // toolbutton feature
    var toolbutton = {
        // toolcontent needs to be formatted as expected by JQuery accordian widget
        init: function ( toolcontent ) {
            toolbutton.toolstatus = 0;
            toolbutton.$toolbutton = $('<button>Tools</button>');
            toolbutton.$widgets = $('#widgets')
            toolbutton.$widgets.append(toolbutton.$toolbutton)
            toolbutton.$toolpopup = $('<div>').append(toolcontent);
            toolbutton.$toolcontent = toolbutton.$toolpopup.accordion({
                heightStyle: "content",
                animate: 30,
            });
            toolbutton.$tooldialog = $('<div>').append(toolbutton.$toolpopup);

            toolbutton.$toolbutton
                .button({ icons: { secondary: "ui-icon-gear" } })
                .on('click',
                    function() {
                        if (toolbutton.toolstatus == 0) {
                            toolbutton.open()
                        } else {
                            toolbutton.close()
                        };
                    });
                
            toolbutton.$tooldialog.dialog({
                                dialogClass: "no-titlebar",
                                draggable: false,
                                //resizeable: false,
                                open:toolbutton.$toolcontent,
                                autoOpen: false,
                                height: "auto",
                                width: 450,
                                position:{
                                        my: "left top",
                                        at: "left bottom",
                                        of: toolbutton.$toolbutton
                                        },
                                });

        },
        
        open: function() {
            toolbutton.$tooldialog.dialog("open");
            toolbutton.$toolcontent.show();
            toolbutton.toolstatus = 1;
        },
        
        close: function() {
            toolbutton.$tooldialog.dialog("close");
            toolbutton.$toolcontent.hide();
            toolbutton.toolstatus = 0;
        },
        
    }
    
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
        toolbutton.$widgets.css({height:"0px"});   // no more widgets in container
        toolbutton.$toolbutton.position({
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
            
            //closetoolbutton();
            toolbutton.close();
        };
            
        var $importraces = $('#manageracesImport');
        $importraces.click( function( event ) {
            event.preventDefault();
            ajaximportraces(false);
        });
    
    };  // manageraces
