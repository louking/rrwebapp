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
    function getconfirmation(event,button,text) {
        event.preventDefault();
        $('<div>').append(text).dialog({
            dialogClass: "no-titlebar",
            autoOpen: true,
            height: "auto",
            modal: true,
            buttons: [
                {   text:  'Cancel',
                    click: function() {
                        $( this ).dialog('close');
                    }
                },{ text:  'Confirm',
                    click: function(){
                        $form = $(event.target).closest("form")
                        $form.append('<input type="hidden" name="whichbutton" value="'+button+'">')
                        $(event.target).closest("form").submit()
                        $( this ).dialog('close');
                    }
                }
            ],
                
            close: function(event,ui) {$(this).remove()},

            });
    }
    
    // decorate buttons
    $("._rrwebapp-actionbutton").button();
    $("._rrwebapp-simplebutton").button()
    
    // get confirmation for any deletes
    $("._rrwebapp-deletebutton").on('click', function(event){getconfirmation(event,'Delete','Please confirm item deletion')});

    
    // toolbutton feature
    var toolbutton = {
        // toolcontent needs to be formatted as expected by JQuery accordian widget
        init: function ( buttonid, toolcontent ) {
            toolbutton.toolstatus = 0;
            toolbutton.$toolbutton = $('<button id="'+buttonid+'">Tools</button>');
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
            
            toolbutton.selector = toolbutton.$toolbutton;
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
        
        position: function(position) {
            toolbutton.$toolbutton.position(position)
        }
    }
    
    // popupbutton feature
    var popupbutton = {

        init: function ( buttonsel, text, label, icons ) {
            $( buttonsel )
                .button({
                            icons: icons,
                            label: label,
                            text: text,
                        })
        },
        
        click: function ( buttonsel, popupcontent, popupaction ) {
            if (popupbutton.popupstatus) {
                popupbutton.$popupdialog.dialog("destroy");
                popupbutton.popupstatus = 0;
            } else {
                popupbutton.$popupdialog = $('<div>').append(popupcontent);
                popupbutton.$popupdialog
                    .dialog({
                        dialogClass: "no-titlebar",
                        draggable: false,
                        autoOpen: true,
                        height: "auto",
                        width: 450,
                        position:{
                                my: "left top",
                                at: "right bottom",
                                of: $( buttonsel ),
                                },
                        });
    
                popupbutton.popupstatus = 1;
                
                if (popupaction) {
                    popupaction();
                };
            };
        },
    };
    
    // addbutton feature
    var addbutton = {
        init: function ( buttonid, url ) {
            addbutton.$addbutton = $('<button id="'+buttonid+'">Add</button>');
            addbutton.$widgets = $('#widgets');
            addbutton.$widgets.append(addbutton.$addbutton);

            addbutton.$addbutton
                .button({ icons: { secondary: "ui-icon-plus" } })
                .on('click',
                    function() {
                        document.location.href = url;
                    });
                
            addbutton.selector = addbutton.$addbutton;
        },
        
        position: function(position) {
            addbutton.$addbutton.position(position)
        }
    };
    
    function ajaxupdatedbresp(url,form,data) {
        console.log(data);
        if (data.success) {
            location.reload(true);
        } else {
            console.log('FAILURE: ' + data.cause);
            // if overwrite requested, force the overwrite
            if (data.confirm) {
                $("<div>" + data.cause + "</div>").dialog({
                    dialogClass: 'no-titlebar',
                    height: "auto",
                    modal: true,
                    buttons: [
                        {   text:  'Cancel',
                            click: function() {
                                $( this ).dialog('destroy');
                            }
                        },{ text:  'Overwrite',
                            click: function(){
                                ajaxupdatedb(url,form,true);
                                $( this ).dialog('destroy');
                            }
                        }
                    ],
                });
            } else {
                $("<div>Error Occurred: " + data.cause + "</div>").dialog({
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
    
    function ajaxupdatedb(urlpath,form,force) {
        //var form_data = new FormData($(this).parent()[0]);
        //var form_data = new FormData($(this).closest('form')[0]);
        var form_data = new FormData($('#copy-series')[0]); // not used
        //console.log(form_data)
        
        // force = true means to overwrite existing data for this year
        params = [{name:"force",value:force}]
        
        // get form values into parameters
        $.each(form.serializeArray(), function(index,value){
            params.push(value)
        })
        
        var url = urlpath +'?'+$.param(params)
        //form_data.append('force',force)
        //url = urlpath

        $.ajax({
            type: 'POST',
            url: url,
            //data: form_data,
            contentType: false,
            cache: false,
            async: false,
            success: function(data) {
                ajaxupdatedbresp(urlpath,form,data);
            },
        });
        
        toolbutton.close();
    };
        
    function ajaximportfileresp(urlpath,formsel,data) {
        console.log(data);
        if (data.success) {
            location.reload(true);
        } else {
            console.log('FAILURE: ' + data.cause);
            // if overwrite requested, force the overwrite
            if (data.confirm) {
                $("<div>"+data.cause+"</div>").dialog({
                    dialogClass: 'no-titlebar',
                    height: "auto",
                    modal: true,
                    buttons: [
                        {   text:  'Cancel',
                            click: function() {
                                $( this ).dialog('destroy');
                            }
                        },{ text:  'Overwrite',
                            click: function(){
                                ajaximportfile(urlpath,formsel,true);
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
    
    function ajaximportfile(urlpath,formsel,force) {
        var form_data = new FormData($(formsel)[0]);
        
        // force = true means to overwrite existing data for this year
        var url = urlpath+'?force='+force
        
        $.ajax({
            type: 'POST',
            url: url,
            data: form_data,
            contentType: false,
            cache: false,
            processData: false,
            async: false,
            success: function(data) {ajaximportfileresp(urlpath,formsel,data)},
        });
        
        //closetoolbutton();
        toolbutton.close();
    };
        
    // managemembers
    function managemembers( writeallowed ) {
        //var $filterseries = $('#filterseries');
        //$filterseries
        //    //.selectmenu({ icons: { secondary: "ui-icon-triangle-1-s" } })
        //    .on('change',
        //        function() {
        //            this.form.submit();
        //        });
        
        if (writeallowed) {
            // put toolbutton in the right place
            //toolbutton.$widgets.css({height:"0px"});   // no more widgets in container
            
            var $importmembers = $('#managemembersImport');
            $importmembers.click( function( event ) {
                event.preventDefault();
                ajaximportfile('/_importmembers','#import-members',false);
            });
        }
    };  // managemembers
    
    // manageraces
    function manageraces( writeallowed ) {
        var $filterseries = $('#filterseries');
        $filterseries
            //.selectmenu({ icons: { secondary: "ui-icon-triangle-1-s" } })
            .on('change',
                function() {
                    this.form.submit();
                });
        
        if (writeallowed) {
            // put toolbutton in the right place
            toolbutton.$widgets.css({height:"0px"});   // no more widgets in container
            
            var $importraces = $('#manageracesImport');
            $importraces.click( function( event ) {
                event.preventDefault();
                //var form = $(this).parent()
                //ajaxupdatedb('_importraces',form,false);
                ajaximportfile('/_importraces','#import-races',false);
            });
            
            $("._rrwebapp-importResultsButton").each(function(){
                raceid = $(this).attr('_rrwebapp-raceid');
                imported = $(this).attr('_rrwebapp-imported');
                action = $(this).attr('_rrwebapp-formaction');
                formid = $(this).attr('_rrwebapp-formid');
                buttonid = formid+'-import';

                if (imported) {
                    icons = {secondary:'ui-icon-check'};
                    text = false;
                    label = null;
                } else {
                    icons = {};
                    label = 'import';
                    text = true;
                };
                
                popupbutton.init(this, text, label, icons);
            });
            
            $("._rrwebapp-importResultsButton").click(function(){
                var raceid = $(this).attr('_rrwebapp-raceid');
                var imported = $(this).attr('_rrwebapp-imported');
                var formid = $(this).attr('_rrwebapp-formid');
                var buttonid = formid+'-import'
                var formaction = $(this).attr('_rrwebapp-formaction');
                var editaction = $(this).attr('_rrwebapp-editaction');
                
                var popupcontent = "\
                    <form method='link' action='"+editaction+"'>\
                        <input type='submit' value='Edit' />\
                    </form>\
                    <form action='"+action+"', id='"+formid+"' method='post' enctype='multipart/form-data'> \
                        <input type='file' name=file /> <button id='"+buttonid+"'>Import</button> \
                    </form>\
                "
                
                var popupaction = function() {
                    $('#'+buttonid)
                        .click( function( event ) {
                            event.preventDefault();
                            ajaximportfile(formaction,'#'+formid,false);
                        });
                }
                popupbutton.click(this, popupcontent, popupaction)
                
            });
        }
    };  // manageraces
    
    // manageseries
    function manageseries() {
        
        var $copyseries = $('#manageseries-copy-button');
        $copyseries.click( function( event ) {
            event.preventDefault();
            var form = $(this).closest('form')
            ajaxupdatedb('_copyseries',form,false);
        });
    
    };  // manageseries

    // managedivisions
    function managedivisions() {
        
        var $copydivisions = $('#managedivisions-copy-button');
        $copydivisions.click( function( event ) {
            event.preventDefault();
            var form = $(this).parent()
            ajaxupdatedb('_copydivisions',form,false);
        });
    
    };  // managedivisions

    // editresults
    function editresults(writeallowed) {
        
        $('#_rrwebapp-table-editresults').scrollTableBody({rowsToDisplay:15});
        
    };  // editresults
