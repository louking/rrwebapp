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
    $( "#navigation" ).menu();
    
    // common dataTables
    var sDomValue = '<"H"Clpfr>t<"F"i>';
    
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
    };

    // getvalue tested for checkbox and select - sel is standard DOM selector (not jQuery)    
    function getvalue(sel) {
        var fieldtype = $( sel ).attr('type');
        if (fieldtype && (fieldtype.toLowerCase() == 'checkbox' || fieldtype.toLowerCase() == 'radio')) {
            var value = $( sel ).prop('checked')
        } else {
            var value = $( sel ).val();
        }
        return value
    };
        
    // getchoicevalues tested for select
    // from http://stackoverflow.com/questions/4964456/make-javascript-do-list-comprehension
    function getchoicevalues(sel) {
        var choiceslist = jQuery.map($(sel).children('option'), function (element) {
            return jQuery(element).val();
        });
        return choiceslist;
    };
    
    // setvalue tested for checkbox and select - sel is standard DOM selector (not jQuery)    
    function setvalue(sel,value) {
        var fieldtype = $( sel ).attr('type');
        if (fieldtype && (fieldtype.toLowerCase() == 'checkbox' || fieldtype.toLowerCase() == 'radio')) {
            $( sel ).prop('checked',value)
        } else {
            $( sel ).val(value);
        }
    };
    
    // gettableheight - assumes some elements exist on the page
    function gettableheight() {
        // TODO: not sure why 112 works -- what's missing?
        var height=$(window).height()
            - $('.heading').height()
            - $('#_rrwebapp-heading-elements').height()
            - $('.dataTables_filter').height()
            - $('thead').height()
            - 112;
        // error return
        if (height<100){
            return 430;
        }
        //normal return
        return height;
    };

    // decorate buttons
    $("._rrwebapp-actionbutton").button();
    $("._rrwebapp-simplebutton").button();
    
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
    
    function ajax_update_db_form_resp(url,form,data) {
        console.log(data);
        if (data.success) {
            if (data.redirect){
                window.location.replace(data.redirect);
            } else {
                location.reload(true);
            };
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
                                ajax_update_db_form(url,form,true);
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
    
    function ajax_update_db_form(urlpath,form,force) {
        //var form_data = new FormData($(this).parent()[0]);
        //var form_data = new FormData($(this).closest('form')[0]);
        //var form_data = new FormData($('#copy-series')[0]); // not used
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
                ajax_update_db_form_resp(urlpath,form,data);
            },
        });
        
        toolbutton.close();
    };
        
    function ajax_update_db_noform_resp(url,addparms,data,sel,callback) {
        console.log(data);
        if (data.success) {
            if (typeof $( sel ).data('revert') != 'undefined') {
                $( sel ).data('revert', getvalue(sel));
            };
            if (callback) {
                callback(sel,data)
            }
            if (data.redirect){
                window.location.replace(data.redirect);
            };

        } else {
            if (typeof $( sel ).data('revert') != 'undefined') {
                setvalue(sel,$( sel ).data('revert'));
            }
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
                                ajax_update_db_noform(url,addparms,sel,true);
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
    
    function ajax_update_db_noform(urlpath,addparms,sel,force,callback) {
        // force = true means to overwrite existing data, not necessarily used by target page
        addparms.force = force
        
        var url = urlpath +'?'+$.param(addparms)
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
                ajax_update_db_noform_resp(urlpath,addparms,data,sel,callback);
            },
        });
    };
        
    function ajax_import_file_resp(urlpath,formsel,data) {
        console.log(data);
        if (data.success) {
            if (data.redirect){
                window.location.replace(data.redirect);
            } else {
                location.reload(true);
            };
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
                                ajax_import_file(urlpath,formsel,true);
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
    
    function ajax_import_file(urlpath,formsel,force) {
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
            success: function(data) {ajax_import_file_resp(urlpath,formsel,data)},
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
                ajax_import_file('/_importmembers','#import-members',false);
            });
        }

        $('#_rrwebapp-table-manage-members').dataTable({
            sDom: sDomValue,
            bJQueryUI: true,
            bPaginate: false,
            sScrollY: gettableheight()-10,      // -10 because sorting icons shown below headings
            bScrollCollapse: true,
        });
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
                //ajax_update_db_form('_importraces',form,false);
                ajax_import_file('/_importraces','#import-races',false);
            });
        };
            
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
            var seriesresultsaction = $(this).attr('_rrwebapp-seriesresultsaction');
            
            var popupcontent = ""
            
            if (writeallowed) {
                popupcontent = popupcontent + "\
                    <form action='"+action+"', id='"+formid+"' method='post' enctype='multipart/form-data'> \
                        <input type='file' name=file /> <button id='"+buttonid+"'>Import</button> \
                    </form>\
                ";
                if (editaction) {
                    popupcontent = popupcontent + "\
                    <form method='link' action='"+editaction+"'>\
                        <input type='submit' value='Edit Participants' />\
                    </form>\
                    "
                };
            };

            if (seriesresultsaction) {
                popupcontent = popupcontent + "\
                <form method='link' action='"+seriesresultsaction+"'>\
                    <input type='submit' value='View Series Results' />\
                </form>\
                "
            };

            var popupaction = function() {
                $('#'+buttonid)
                    .click( function( event ) {
                        event.preventDefault();
                        ajax_import_file(formaction,'#'+formid,false);
                    });
            }
            popupbutton.click(this, popupcontent, popupaction)
            
        });

        _rrwebapp_table = $('#_rrwebapp-table-manage-races').dataTable({
            sDom: sDomValue,
            bJQueryUI: true,
            bPaginate: false,
            sScrollY: gettableheight(), 
            bSort: false,
            bScrollCollapse: true,
        });
        //_rrwa_racestable = $('#_rrwebapp-table-manage-races').DataTable({
        //    paging: false,
        //    scrollY: 450, // when scrolling, scroll jumps after updating column value
        //    ordering: false,
        //});

    };  // manageraces
    
    // manageseries
    function manageseries() {
        
        var $copyseries = $('#manageseries-copy-button');
        $copyseries.click( function( event ) {
            event.preventDefault();
            var form = $(this).closest('form')
            ajax_update_db_form('_copyseries',form,false);
        });
    
        _rrwebapp_table = $('#_rrwebapp-table-manage-series').dataTable({
                sDom: sDomValue,
                bJQueryUI: true,
                bPaginate: false,
                sScrollY: gettableheight(),
                bSort: false,
                bScrollCollapse: true,
            })
    };  // manageseries

    // managedivisions
    function managedivisions() {
        
        var $copydivisions = $('#managedivisions-copy-button');
        $copydivisions.click( function( event ) {
            event.preventDefault();
            var form = $(this).parent()
            ajax_update_db_form('_copydivisions',form,false);
        });
    
        _rrwebapp_table = $('#_rrwebapp-table-manage-divisions').dataTable({
                sDom: sDomValue,
                bJQueryUI: true,
                bPaginate: false,
                sScrollY: gettableheight(),
                bSort: false,
                bScrollCollapse: true,
            })
        
            setTimeout( function () {
                console.log('adjusting column sizing');
                _rrwebapp_table.fnAdjustColumnSizing();
            }, 30 );
    };  // managedivisions
        
    // editresults
    function editresults(writeallowed) {
        
        function setchecked(sel) {
            if (sel.checked) {
                $(sel).button({icons:{ primary: 'ui-icon-check' }});
            } else {
                $(sel).button({icons:{ primary: null }});         
            }
        };

        // make button for checkbox
        $('._rrwebapp-editresults-checkbox-confirmed').button({text:false});
        $('._rrwebapp-editresults-checkbox-confirmed').each(function(){setchecked(this);});
        if (writeallowed) {
            // set up import button
            $('#_rrwebapp-button-import').button()
                .click( function( event ) {
                    event.preventDefault();
                    url = $('#_rrwebapp-import-results').attr('_rrwebapp-import-url')
                    ajax_import_file(url,'#_rrwebapp-import-results',false);
                });
            
            // set up tabulate button
            $('#_rrwebapp-button-tabulate').button()
                .click( function( event ) {
                    event.preventDefault();
                    url = $('#_rrwebapp-button-tabulate').attr('_rrwebapp-tabulate-url')
                    ajax_update_db_noform(url,{},'#_rrwebapp-button-tabulate',false)
                });

            // handle checkbox update
            $('._rrwebapp-editresults-checkbox-confirmed')
                .on('click',
                    function(){
                        setchecked(this);
                    });
        }
        
        // initial revert values -- see ajax_update_db_noform_resp for use of 'revert' data field
        $('._rrwebapp-editresults-select-runner, ._rrwebapp-editresults-checkbox-confirmed').each(function() {
            $( this ).data('revert', getvalue(this));
        });
        
        $('._rrwebapp-editresults-select-runner, ._rrwebapp-editresults-checkbox-confirmed')
            .on('change',
                function ( event ) {
                    var apiurl = $( this ).attr('_rrwebapp-apiurl');
                    var field = $( this ).attr('_rrwebapp-field');
                    value = getvalue(this)

                    // ajax parameter setup
                    ajaxparams = {field:field,value:value}
                    
                    // control exclusion table
                    selectelement = $(this).parent().parent().find('select._rrwebapp-editresults-select-runner')
                    selectvalue = $( selectelement ).val()
                    choicevalues = getchoicevalues(selectelement);
                    // remove value from choicevalues (if it exists -- it should exist, though)
                    if ($.inArray(selectvalue, choicevalues) != -1) {
                        choicevalues.splice( $.inArray(selectvalue, choicevalues), 1 );
                    }
                    // why doesn't ajax call stringify choicevalues?
                    addlfields = {include:selectvalue,exclude:JSON.stringify(choicevalues)} 
                    $.extend(ajaxparams,addlfields)

                    ajax_update_db_noform(apiurl,ajaxparams,this,true,
                        // this function is called in ajax_update_db_noform_resp if successful
                        function(sel){
                            // change row class if confirmed changes
                            var field = $( sel ).attr('_rrwebapp-field');
                            value = getvalue(sel)
                            if (field=='confirmed'){
                                if (value) {
                                    $(sel).closest('tr').removeClass('_rrwebapp-row-confirmed-False');
                                    $(sel).closest('tr').addClass('_rrwebapp-row-confirmed-True');
                                } else {
                                    $(sel).closest('tr').removeClass('_rrwebapp-row-confirmed-True');
                                    $(sel).closest('tr').addClass('_rrwebapp-row-confirmed-False');
                                }
                            }
                        });
        });

        $('#_rrwebapp-table-editresults').dataTable({
            //bPaginate: false,
            //sScrollY: 450,  // when scrolling, scroll jumps after updating column value
            sDom: sDomValue,
            bJQueryUI: true,
            bSort: false,
            bScrollCollapse: true,
        });
        //_rrwa_resultstable = $('#_rrwebapp-table-editresults').DataTable({
        //    //paging: false,
        //    //scrollY: 450, // when scrolling, scroll jumps after updating column value
        //    ordering: false,
        //    //drawCallback: setuppage,
        //    //columnDefs: [{target:'._rrwebapp-col-time',type:'date',orderable:true},
        //    //             {target:'._rrwebapp-col-_unordered',orderable:false},
        //    //             ]
        //});
        
    };  // editresults

    function seriesresults(writeallowed) {
        
        console.log('$(window).height()='+$(window).height())
        console.log("$('.heading').height()="+$('.heading').height())
        console.log("$('#_rrwebapp-heading-elements').height()="+$('#_rrwebapp-heading-elements').height())
        console.log("$('thead').height()="+$('thead').height())
        console.log('sScrollY='+($(window).height()-$('.heading').height()-$('#_rrwebapp-heading-elements').height()))-$('thead').height()-130
        _rrwebapp_table = $('#_rrwebapp-table-seriesresults').dataTable({
                sDom: sDomValue,
                bJQueryUI: true,
                bPaginate: false,
                sScrollY: gettableheight()-15,  // -15 due to sort arrows, I think 
                bScrollCollapse: true,
                aoColumnDefs: [
                    {aTargets:[0],bVisible:false},
                            ],
            })
            .yadcf([{
                    column_number:0,
                    filter_container_id:"_rrwebapp_filterseries",
                    filter_reset_button_text: false,    // no filter reset button
                },{
                    column_number:3,
                    filter_container_id:"_rrwebapp_filtergender",
                },{
                    column_number:5,
                    filter_container_id:"_rrwebapp_filterdivision",
                },]);
        //_rrwa_resultstable = $('#_rrwebapp-table-seriesresults').DataTable({
        //    paging: false,
        //    scrollY: 450, // when scrolling, scroll jumps after updating column value
        //    //ordering: false,
        //});
        
        selectfilter = '#_rrwebapp_filterseries select';
        $(selectfilter+" option[value='-1']").remove();
        var serieschoices = getchoicevalues(selectfilter);
        yadcf.exFilterColumn(_rrwebapp_table, 0, serieschoices[0])
        
        
    };  // seriesresults

    function viewstandings() {
        // not sure why fudge is needed, needed after adding accordion above table
        var initialheightfudge = 35;
        var redrawheightfudge = 50;
        
        // Race list is kept in accordion above table, for reference
        // height gets changed as accordion changes -- see http://datatables.net/forums/discussion/10906/adjust-sscrolly-after-init/p1
        $( "#_rrwebapp-accordion-standings-races" ).accordion({
          collapsible: true,
          active: 'none',   // see http://stackoverflow.com/questions/2675263/collapse-all-sections-in-accordian-on-page-load-in-jquery-accordian
          activate: function(event,ui) {
            var oSettings = _rrwebapp_table.fnSettings();
            var newheight = gettableheight() + redrawheightfudge;   // hmm, why +
            oSettings.oScroll.sY = newheight;
            $('div.dataTables_scrollBody').height(newheight);
            console.log('newheight='+newheight)
          }
        });

        // table needs to be after accordion declaration so size is set right
        _rrwebapp_table = $('#_rrwebapp-table-standings').dataTable({
                sDom: sDomValue,
                bJQueryUI: true,
                bPaginate: false,
                sScrollY: gettableheight() - initialheightfudge,
                bScrollCollapse: true,
                aoColumnDefs: [
                    {aTargets:[0],bVisible:false},
                    {aTargets:['_rrwebapp-class-col-place',
                               '_rrwebapp-class-col-race',
                               '_rrwebapp-class-col-total'
                               ],sType:'num-html'},
                    ],
            })
            .yadcf([{
                    column_number:0,
                    filter_container_id:"_rrwebapp_filterdivision",
                    column_data_type: "html",
                    html_data_type: "text",
                    filter_reset_button_text: false,    // no filter reset button
                },{
                    column_number:3,
                    column_data_type: "html",
                    html_data_type: "text",
                    filter_container_id:"_rrwebapp_filtergender",
                },]);
        
        // force always to have some Division filter, hopefully Overall
        selectfilter = '#_rrwebapp_filterdivision select';
        $(selectfilter+" option[value='-1']").remove();
        var serieschoices = getchoicevalues(selectfilter);
        if ($.inArray('Overall', serieschoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, 0, 'Overall');
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, 0, serieschoices[0])            
        }

        // mouseover races shows race name
        $( document ).tooltip();
    };  // viewstandings

    function updateselect(sel,apiurl,ajaxparams) {
        ajax_update_db_noform(apiurl,ajaxparams,sel,true,
            // this function is called in ajax_update_db_noform_resp if successful
            function(sel,data){
                // remove current options
                $(sel+' option').each(function(){
                   $(this).remove() 
                });
                // add options from response
                $.each(data.choices,function(ndx,choice){
                   $(sel).append($('<option>').val(choice[0]).text(choice[1]));
                });
            });
        
    };
    
    function choosestandings() {
        $('#_rrwebapp-choosestandings-select-club')
            .on('change',
                function ( event ) {
                    var apiurl = $( this ).attr('_rrwebapp_apiurl');
                    club = getvalue('#_rrwebapp-choosestandings-select-club')

                    // club needs to be set
                    if (!club ) {
                        return
                    }
                    
                    // ajax parameter setup
                    ajaxparams = {club:club}
                    
                    updateselect('#_rrwebapp-choosestandings-select-year',apiurl,ajaxparams);
        });

        $('#_rrwebapp-choosestandings-select-club, #_rrwebapp-choosestandings-select-year')
            .on('change',
                function ( event ) {
                    var apiurl = $( this ).attr('_rrwebapp_apiurl');
                    club = getvalue('#_rrwebapp-choosestandings-select-club')
                    year = getvalue('#_rrwebapp-choosestandings-select-year')

                    // both need to be set
                    if (!club || !year) {
                        return
                    }
                    
                    // ajax parameter setup
                    ajaxparams = {club:club,year:year}
                    
                    updateselect('#_rrwebapp-choosestandings-select-series',apiurl,ajaxparams);
        });

    };  // choosestandings
