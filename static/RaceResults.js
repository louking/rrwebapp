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
    
    // from http://stackoverflow.com/questions/1480133/how-can-i-get-an-objects-absolute-position-on-the-page-in-javascript
    var cumulativeOffset = function(element) {
        var top = 0, left = 0;
        do {
            top += element.offsetTop  || 0;
            left += element.offsetLeft || 0;
            element = element.offsetParent;
        } while(element);
    
        return {
            top: top,
            left: left
        };
    };
    
    // common dataTables
    // gettableheight - assumes some elements exist on the page
    function gettableheight() {
        var height;
        // dataTable has been drawn
        if (typeof _rrwebapp_table != 'undefined') {
            // there should be only one of these
            $('.dataTables_scrollBody').each( function () {
                height = $(window).height() - cumulativeOffset(this).top;
            });
            // subtract off height of info field -- assumes this is the only
            // field at bottom of table.  See sDomValue definition
            var footerheight = 0;
            $('.dataTables_info').each(function(){
                footerheight = this.offsetHeight;
            });
            height = height - (footerheight + 10); // 10 for padding

        // dataTable hasn't been drawn yet
        } else {
            height=$(window).height()
                - $('.heading').height()
                - $('#_rrwebapp-heading-elements').height()
                - $('.dataTables_filter').height()
                - $('thead').height()
                - 112;
        }

        // override if too small
        if (height<50){
            height = 430;
        }
        //normal return
        return height;
    }

    var sDomValue = '<"H"lBpfr>t<"F"i>';
    var sPrinterFriendlyDomValue = 'lpfrt';
    // var sDomValue = '<"H"Clpfr>t<"F"i>';
    // var sPrinterFriendlyDomValue = '<"H"Clpr>t<"F">';
    function getDataTableParams(updates,printerfriendly) {
        if (arguments.length == 1) {
            printerfriendly = false;
        }
        if (!printerfriendly){
            var params = {
                    dom: sDomValue,
                    jQueryUI: true,
                    paging: false,
                    scrollY: gettableheight(),
                    scrollCollapse: true,
                    buttons: [],
                    // responsive: true,    // causes + button on left, which is not user friendly
                    scrollX: true,
                    scrollXInner: "100%",
                    infoCallback: function( oSettings, iStart, iEnd, iMax, iTotal, sPre ) {
                        var info = "Showing ";
                        if (oSettings.oFeatures.bPaginate) {
                            info = info + iStart +" to ";                        
                            info = info + iEnd +" of "+ iMax +" entries";
                        } else {
                            info = info + iEnd +" entries";
                        }
    
                        return info;
                      }
                };
        }
        else {
            var params = {
                    dom: sPrinterFriendlyDomValue,
                    jQueryUI: true,
                    paging: false,
                    ordering: false,
                    scrollCollapse: true,
                }
        }
        $.extend(params,updates)
        return params;
    }
    //var sSpecDomValue = '<"H"Clpr>t';
    var sSpecDomValue = 'lfrtip';
    function getSpecTableParams(updates) {
        var params = {
                dom: sSpecDomValue,
                jQueryUI: true,
                paging: false,
                ordering: false,
                scrollCollapse: true,
                //scrollXInner: "100%",
            }
        $.extend(params,updates)
        return params
    };

    // note this expects all dataTable tables be called _rrwebapp_table, and this be global variable
    // see https://datatables.net/forums/discussion/10437/fixedheader-column-headers-not-changing-on-window-resize/p1
    function resetDataTableHW() {
        _rrwebapp_table.fnAdjustColumnSizing();
        $('div.dataTables_scrollBody').height(gettableheight());
    };
    $(window).on('resize', function () {
        if (typeof _rrwebapp_table != 'undefined') {
            resetDataTableHW();
        }
      } );

    // dataTables num-html support [modified plugin from http://datatables.net/plug-ins/sorting#functions_type "Numbers with HTML"]
    jQuery.extend( jQuery.fn.dataTableExt.oSort, {
      "num-html-pre": function ( a ) {
          var x = String(a).replace( /<[\s\S]*?>/g, "" );
          return parseFloat( x );
      },
   
      "num-html-asc": function ( a, b ) {
          if (!a || a == '') {a = 0};
          if (!b || b == '') {b = 0};
          return ((a < b) ? -1 : ((a > b) ? 1 : 0));
      },
   
      "num-html-desc": function ( a, b ) {
          if (!a || a == '') {a = 0};
          if (!b || b == '') {b = 0};
          return ((a < b) ? 1 : ((a > b) ? -1 : 0));
      }
    } );
    
    // sort extension for 'racetime' ([[h:]mm:]ss)
    jQuery.extend( jQuery.fn.dataTableExt.oSort, {
      "racetime-pre": function ( a ) {
            if (!a || a == '') {return 0};
            var parts = a.split(':');
            var len = parts.length;
            var numsecs = 0;
            for (var i = 0; i < len; i++) {
              numsecs = numsecs*60 + parseFloat( parts[i] );
            }
            traceonce = 0;
            return numsecs;
      },
   
      "racetime-asc": function ( a, b ) {
          return ((a < b) ? -1 : ((a > b) ? 1 : 0));
      },
   
      "racetime-desc": function ( a, b ) {
          return ((a < b) ? 1 : ((a > b) ? -1 : 0));
      }
    } );
    
    // retrieve filter used for table at indicated column (per https://groups.google.com/forum/#!topic/daniels_code/j6xFhWin38U)
    function getFilterValue(table_arg, column_number){
        return table_arg.fnSettings().aoPreSearchCols[column_number].sSearch;
    }

    // retrieve column index when header has certain text
    function getColIndex(searchtext) {
        return $('thead tr:first th').filter(
            function(){
                return $(this).text() == searchtext;
            }).index();
    }
    // common functions
    
    // for slow loading links
    $("a").click(function(){
        var img = $(this).attr('_rrwebapp-loadingimg');
        if (img) {
            //$(this).after("&nbsp;&nbsp;&nbsploading...");
            $(this).after('<div id="progressbar"><div class="progress-label">&nbsp;&nbsp;&nbsploading...</div></div>');
            $('#progressbar').progressbar({
                value: false,
            });
            //for some reason the image was broken
            //window.console && console.log("<img src='"+img+"' alt='&nbsp;&nbsp;&nbsploading...' />");
            //$(this).after("<img src='"+img+"' alt='&nbsp;&nbsp;&nbsploading...' />").fadeIn();
        }
    });
    
    // this opens url in new window or tab, depending on browser settings
    function newtab(url) {
        // from http://stackoverflow.com/questions/19851782/how-to-open-a-url-in-a-new-tab-using-javascript-or-jquery
        var win = window.open(url, '_blank');
        if(win){
            //Browser has allowed it to be opened
            win.focus();
        }else{
            //Browser has blocked it
            alert('Please allow popups for this site');
        }
    }

    function geturl () {
        return document.URL.split('?')[0];
    }
    
    function geturlargs() {
        var vars = {}, hash;
        var q = document.URL.split('?')[1];
        if(q !== undefined){
            q = q.split('&');
            for(var i = 0; i < q.length; i++){
                hash = q[i].split('=');
                // decode the URI, but have to replace '+' with ' ' - from http://stackoverflow.com/questions/3431512/javascript-equivalent-to-phps-urldecode 
                vars[decodeURIComponent(hash[0])] = decodeURIComponent(hash[1].replace(/\+/g, ' '));
            }
        }
        return vars;
    }
    
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
        
    // getselecttext - sel is standard DOM selector (not jQuery), val is value looking for, returns "" if not found
    function getselecttext(sel,val) {
        return $( sel ).find("option[value="+val+"]").text()
    }
    
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
    
    function updateselectbyapi(sel,apiurl,ajaxparams) {
        ajax_update_db_noform(apiurl,ajaxparams,sel,true,
            // this function is called in ajax_update_db_noform_resp if successful
            function(sel,data){
                // remove current options
                $(sel+' option').each(function(){
                   $(this).remove();
                });
                // add options from response
                $.each(data.choices,function(ndx,choice){
                   $(sel).append($('<option>').val(choice[0]).text(choice[1]));
                });
            });
        
    };
    
    function updateselectbyarray(sel,selchoices) {
        $(sel+' option').each(function(){
           $(this).remove();
        });
        // add options from selchoices array
        $.each(selchoices,function(ndx,choice){
           $(sel).append($('<option>').val(choice[0]).text(choice[1]));
        });
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

        init: function ( buttonsel, text, label, icons, clickoutside ) {
            if (arguments.length < 5) {
                popupbutton.clickoutside = false;
            }
            $( buttonsel )
                .button({
                            icons: icons,
                            label: label,
                            text: text,
                        });
            popupbutton.clickoutside = clickoutside;
        },
        
        click: function ( buttonsel, popupcontent, popupaction ) {
            if (popupbutton.popupstatus) {
                popupbutton.$popupdialog.dialog("destroy");
                popupbutton.popupstatus = 0;
            } else {
                popupbutton.$popupdialog = $('<div>').append(popupcontent);
                popupbutton.dialogwidget = popupbutton.$popupdialog
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
                        clickOutside: popupbutton.clickoutside, // see https://github.com/coheractio/jQuery-UI-Dialog-ClickOutside
                        clickOutsideTrigger: buttonsel,
                        close: function () {
                            popupbutton.popupstatus = 0;
                        },
                        open: function () {
                            popupbutton.popupstatus = 1;
                            
                            if (popupaction) {
                                popupaction();
                            };
                        },
                        });
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
        window.console && console.log(data);
        if (data.success) {
            if (data.redirect){
                window.location.replace(data.redirect);
            } else {
                location.reload(true);
            };
        } else {
            window.console && console.log('FAILURE: ' + data.cause);
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
        //window.console && console.log(form_data)
        
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
        window.console && console.log(data);
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
            window.console && console.log('FAILURE: ' + data.cause);
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
        window.console && console.log(data);
        if (data.success) {
            if (data.redirect){
                window.location.replace(data.redirect);
            } else {
                location.reload(true);
            };
        } else {
            window.console && console.log('FAILURE: ' + data.cause);
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
                var url = $(this).attr('_rrwebapp-formaction')
                ajax_import_file(url,'#import-members',false);
            });
        }

        _rrwebapp_table = $('#_rrwebapp-table-manage-members')
            .dataTable(getDataTableParams({scrollY: gettableheight()-10}));
                // -10 because sorting icons shown below headings
        resetDataTableHW();
        
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
                url = $(this).attr('_rrwebapp-formaction')
                ajax_import_file(url,'#import-races',false);
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
            var importdoc = $(this).attr('_rrwebapp-importdoc');
            var editaction = $(this).attr('_rrwebapp-editaction');
            var seriesresultsaction = $(this).attr('_rrwebapp-seriesresultsaction');
            
            var popupcontent = ""
            
            if (writeallowed) {
                popupcontent = popupcontent + "\
                    <p>Import the selected races's results as a CSV file. Please read the <a href='"+importdoc+"' target='_blank'>Import Guide</a> for information on the column headers and data format.</p>\
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

        _rrwebapp_table = $('#_rrwebapp-table-manage-races')
            .dataTable(getDataTableParams({ordering: false}));
        resetDataTableHW();

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
    
        _rrwebapp_table = $('#_rrwebapp-table-manage-series')
            .dataTable(getDataTableParams({ordering: false}));
        resetDataTableHW();

    };  // manageseries

    // managedivisions
    function managedivisions() {
        
        var $copydivisions = $('#managedivisions-copy-button');
        $copydivisions.click( function( event ) {
            event.preventDefault();
            var form = $(this).parent()
            ajax_update_db_form('_copydivisions',form,false);
        });
    
        _rrwebapp_table = $('#_rrwebapp-table-manage-divisions')
            .dataTable(getDataTableParams({ordering:false}))
        setTimeout(function () {resetDataTableHW()},30);
        
    };  // managedivisions
    
    // editparticipants
    function editparticipants(raceid, readallowed, writeallowed, membersonly) {
        
        function setchecked(sel) {
            if (sel.checked) {
                $(sel).button({icons:{ primary: 'ui-icon-check' }});
            } else {
                $(sel).button({icons:{ primary: null }});         
            }
        };

        if (writeallowed) {
            // handle checkbox update
            $('._rrwebapp-editparticipants-checkbox-confirmed')
                .on('click',
                    function(){
                        setchecked(this);
                    });
        }
        
        // set up for editing
        var editor = new $.fn.dataTable.Editor( {
            ajax:  window.location.origin + '/_editparticipants/' + raceid,
            table: '#_rrwebapp-table-editparticipants',
            idSrc:  'id',
                fields: [
                { label: 'Result Name:', name: 'resultname',
                  type: 'selectize', options: membernames,
                  opts: { searchField: 'label' },
                },
                { label: 'Gender:',  name: 'gender',
                  type: 'select', options: {'': 'None', 'M':'M', 'F':'F'},
                },
                { label: 'Age:',  name: 'age'  },
                { label: 'Time:',  name: 'time'  },
                { label: 'Hometown:',  name: 'hometown'  },
                { label: 'Club:',  name: 'club'  }
            ]
        } );

        // initialize table before everything else
        var matchCol = getColIndex('Match');
        var typeCol = getColIndex('Type');      // if not there, -1
        var yadcffilters = [{
                        column_number:matchCol,
                        filter_container_id:"_rrwebapp_filtermatch",
                        column_data_type: "text",
                        filter_match_mode: "exact",
                        filter_type:"multi_select",
                        select_type: 'select2',
                        select_type_options: {
                            width: '20em',
                        },
                        filter_reset_button_text: 'all',    // no filter reset button
                    }];
        if (typeCol != -1) {
            yadcffilters.push({
                        column_number:typeCol,
                        filter_container_id:"_rrwebapp_filtertype",
                        column_data_type: "text",
                        filter_match_mode: "exact",
                        filter_type:"multi_select",
                        select_type: 'select2',
                        select_type_options: {
                            width: '20em',
                        },
                        filter_reset_button_text: 'all',    // no filter reset button
                    });
        }

        _rrwebapp_table = $('#_rrwebapp-table-editparticipants')
            .on( 'draw.dt', function () {
                // make button for checkbox
                $('._rrwebapp-editparticipants-checkbox-confirmed').button({text:false});
                $('._rrwebapp-editparticipants-checkbox-confirmed').each(function(){setchecked(this);});
                
                // initial revert values -- see ajax_update_db_noform_resp for use of 'revert' data field
                $('._rrwebapp-editparticipants-select-runner, ._rrwebapp-editparticipants-checkbox-confirmed').each(function() {
                    $( this ).data('revert', getvalue(this));
                });
                
                if (writeallowed) {
                    // handle checkbox update
                    $('._rrwebapp-editparticipants-checkbox-confirmed')
                        .on('click',
                            function(){
                                setchecked(this);
                            });
                }

                $('._rrwebapp-editparticipants-select-runner, ._rrwebapp-editparticipants-checkbox-confirmed')
                    .on('change',
                        function ( event ) {
                            var apiurl = $( this ).attr('_rrwebapp-apiurl');
                            var field = $( this ).attr('_rrwebapp-field');
                            value = getvalue(this)

                            // ajax parameter setup
                            ajaxparams = {field:field,value:value}
                            
                            // control exclusion table
                            selectelement = $(this).parent().parent().find('select._rrwebapp-editparticipants-select-runner')
                            selectvalue = $( selectelement ).val()
                            excludevalues = getchoicevalues(selectelement);
                            // remove value from excludevalues (if it exists -- it should exist, though)
                            if ($.inArray(selectvalue, excludevalues) != -1) {
                                excludevalues.splice( $.inArray(selectvalue, excludevalues), 1 );
                            }
                            // also remove 'new' from excludevalues
                            if ($.inArray('new', excludevalues) != -1) {
                                    excludevalues.splice( $.inArray(selectvalue, excludevalues), 1 );
                            }
                            
                            // special processing for runnerid field, if going to new name, or coming from new name
                            if (!membersonly && field === 'runnerid') {
                                var newname = $( this ).attr('_rrwebapp-newrunner-name')
                                var newgen = $( this ).attr('_rrwebapp-newrunner-gender')
                                var lastid = $( this ).data('revert')
                                if (typeof newname != undefined) {
                                    // if going to new name
                                    if (getselecttext(this,getvalue(this)) === newname + ' (new)') {
                                        addlfields = {newname:newname,newgen:newgen}
                                        $.extend(ajaxparams,addlfields)
                                    // if coming from new name
                                    } else if (getselecttext(this,lastid) === newname + ' (new)') {
                                        addlfields = {removeid:lastid}
                                        $.extend(ajaxparams,addlfields)
                                        // remove lastid from excludevalues (if it exists -- it should exist, though)
                                        if ($.inArray(lastid, excludevalues) != -1) {
                                            excludevalues.splice( $.inArray(lastid, excludevalues), 1 );
                                        }
                                    }
                                }
                            }

                            // why doesn't ajax call stringify excludevalues?
                            addlfields = {include:selectvalue,exclude:JSON.stringify(excludevalues)} 
                            $.extend(ajaxparams,addlfields)
                            
                            ajax_update_db_noform(apiurl,ajaxparams,this,true,
                                // this function is called in ajax_update_db_noform_resp if successful
                                function(sel,data){
                                    // change row class if confirmed changes
                                    var field = $( sel ).attr('_rrwebapp-field');
                                    value = getvalue(sel)
                                    if (field=='confirmed'){
                                        if (value) {
                                            $(sel).closest('tr').removeClass('_rrwebapp-row-confirmed-false');
                                            $(sel).closest('tr').addClass('_rrwebapp-row-confirmed-true');
                                        } else {
                                            $(sel).closest('tr').removeClass('_rrwebapp-row-confirmed-true');
                                            $(sel).closest('tr').addClass('_rrwebapp-row-confirmed-false');
                                        }
                                    }
                                    
                                    // if newname added or removed, update select field appropriately
                                    // see http://stackoverflow.com/questions/5915789/replace-item-in-array-with-javascript for array manipulation
                                    if (typeof data.action != 'undefined') {
                                        // successful add of newname
                                        var choicevals = getchoicevalues(sel);
                                        var choices = [];
                                        for (i=0;i<choicevals.length;i++) {
                                            choices.push([choicevals[i],getselecttext(sel,choicevals[i])])
                                        }
                                        if (data.action == 'newname') {
                                            var index = choicevals.indexOf('new');
                                            if (index != -1) {
                                                choices[index] = [data.id,data.name+' (new)'];
                                                updateselectbyarray('#'+$(sel).attr('id'),choices);
                                                setvalue(sel,data.id);
                                                $( sel ).data('revert', data.id);
                                            }
                                        }
                                        // successfull remove of id, just moved off of this one, replace with new
                                        // preserve choice user just made
                                        else if (data.action == 'removeid') {
                                            var index = choicevals.indexOf(data.id.toString())
                                            if (index != -1) {
                                                var currchoice = getvalue(sel);
                                                choices[index] = ['new',data.name+' (new)'];
                                                updateselectbyarray('#'+$(sel).attr('id'),choices);
                                                setvalue(sel,currchoice);
                                                $( sel ).data('revert', currchoice);
                                            }
                                        }
                                    }
                                });
                });
            })
        .dataTable(getDataTableParams({
                data: tabledata,
                columns: [
                    {
                        data: null,
                        defaultContent: '',
                        className: 'select-checkbox',
                        orderable: false
                    },
                    // when Editor idSrc option is used with select, this column gets removed from the table
                    // { data: 'id',           name: 'id',          visible: false },   
                    { data: 'place',        name: 'place',       className: 'dt-body-center' },
                    { data: 'resultname',   name: 'resultname' },
                    { data: 'gender',       name: 'gender',      className: 'dt-body-center' },
                    { data: 'age',          name: 'age',         className: 'dt-body-center' },
                    { data: 'disposition',  name: 'disposition', className: 'dt-body-center' },
                    { data: 'confirm',      name: 'confirm',     className: 'dt-body-center',
                      render: function ( data, type, row, meta ) {
                        var val = '' 
                            + '<input class="_rrwebapp-editparticipants-checkbox-confirmed" type="checkbox" ' 
                            + ((data) ? 'checked ' : ' ') 
                            + 'id="_rrwebapp-editparticipants-checkbox-confirmed-' + row.id + '" ' 
                            + '_rrwebapp-field=\'confirmed\' ' 
                            + '_rrwebapp-apiurl=' + window.location.origin + '/_updatemanagedresult/' + row.id + '>\n' 
                            + '<label for="_rrwebapp-editparticipants-checkbox-confirmed-' + row.id + '"></label>';
                        return val;
                      }
                    },
                    { data: 'runnerid',     name: 'runnerid',    
                      render: function ( data, type, row, meta ) { 
                        if ( data && row.disposition==='definite') {
                            return memberages[data];
                        } else if (writeallowed && (row.disposition === 'missed' || row.disposition === 'similar') || (!membersonly && row.disposition != 'definite')) {
                            var val = ''
                                + '<select class="_rrwebapp-editparticipants-select-runner"'
                                + ' id="_rrwebapp-editparticipants-select-id-' + row.id + '"'
                                + ' _rrwebapp-field=\'runnerid\''
                                + ((!membersonly) ? ' _rrwebapp-newrunner-name=' + row.name + ' _rrwebapp-newrunner-gender=' + row.gender : '')
                                + '_rrwebapp-apiurl=' + window.location.origin + '/_updatemanagedresult/' + row.id + '>\n'
                            var len = tableselects[row.id].length;
                            for ( var i = 0; i < len; i++ ) {
                                var value  = tableselects[row.id][i][0];
                                var choice = tableselects[row.id][i][1];
                                val += '<option value=' + ((value===null) ? 'None' : value)
                                    + ((value==data) ? ' selected' : '')
                                    + '>' + choice + '</option>\n';
                            }
                            val += '</select>';

                            return val
                        } else {
                            return '';
                        }
                      }
                    },
                    { data: 'hometown',     name: 'hometown' },
                    { data: 'club',         name: 'club' },
                    { data: 'time',         name: 'time',        className: 'dt-body-center', type: 'racetime' }
                ],
                rowCallback: function ( row, data, index ) {
                                $( row ).addClass('_rrwebapp-row-disposition-' + data.disposition);
                                $( row ).addClass('_rrwebapp-row-confirmed-' + data.confirm);

                                var table = this.api();
                                var id_ndx = table.column('id:name').index();
                            },
                paging: true,
                select: true,
                buttons: [
                    { extend: 'create', editor: editor },
                    { extend: 'edit',   editor: editor },
                    { extend: 'remove', editor: editor },
                    'csv'
                ],
                ordering: true,
                order: [10,'asc'],  // 10 is time column
            }))
            .yadcf(yadcffilters);

        // set initial table height
        resetDataTableHW();

        // set up widgets at top of page
        if (writeallowed) {
            toolbutton.$widgets.css({height:"0px"});   // no more widgets in container            
            if (typeCol == -1) {
                toolbutton.position({my: "left center", at: "right+3 center", of: '#_rrwebapp_filtermatch'});                
            } else {
                toolbutton.position({my: "left center", at: "right+3 center", of: '#_rrwebapp_filtertype'});                                
            }
        }

    };  // editparticipants

    function seriesresults(writeallowed,series,division,gender,printerfriendly) {
        
        var seriesCol = 0;
        var genderCol = 3;
        var divisionCol = 5;
        var timeCol = 7;
        var paceCol = 8;
        var agtimeCol = 9;
        var columndefs = [
                        {targets:[seriesCol],bVisible:false},
                        {targets:[timeCol,paceCol,agtimeCol],type:'racetime'},
                                ];
        
        if (!printerfriendly){
            var tableparamupdates = {
                    scrollY: gettableheight()+13, 
                    buttons: ['csv'],
                    // scrollXInner: "100%",
                    columnDefs: columndefs,
                    language: {
                        emptyTable: "Race results have not been tabulated yet, please check again later"
                    },
                };
        }
        else {
            var tableparamupdates = {
                    columnDefs: columndefs,
                    language: {
                        emptyTable: "Race results have not been tabulated yet, please check again later"
                    },
            }
        }

        _rrwebapp_table = $('#_rrwebapp-table-seriesresults')
            .dataTable(getDataTableParams(tableparamupdates,printerfriendly))
            .yadcf([{
                    column_number:seriesCol,
                    filter_container_id:"_rrwebapp_filterseries",
                    filter_reset_button_text: false,    // no filter reset button
                },{
                    column_number:genderCol,
                    filter_container_id:"_rrwebapp_filtergender",
                    filter_reset_button_text: 'all',
                },{
                    column_number:divisionCol,
                    filter_container_id:"_rrwebapp_filterdivision",
                    filter_reset_button_text: 'all',
                },]);
        if (!printerfriendly) {
            resetDataTableHW();
        }

        // force always to have some Series filter
        var selectfilter = '#_rrwebapp_filterseries select';
        $(selectfilter+" option[value='-1']").remove();

        // set series based on caller's preference
        var serieschoices = getchoicevalues(selectfilter);
        if ($.inArray(series, serieschoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, seriesCol, series);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, seriesCol, serieschoices[0])            
        }

        // set division based on caller's preference
        var selectfilter = '#_rrwebapp_filterdivision select';
        var divchoices = getchoicevalues(selectfilter);
        if ($.inArray(division, divchoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, divisionCol, division);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, divisionCol, divchoices[0])            
        }
        
        // set gender based on caller's preference
        selectfilter = '#_rrwebapp_filtergender select';
        var genchoices = getchoicevalues(selectfilter);
        if ($.inArray(gender, genchoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, genderCol, gender);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, genderCol, genchoices[0])            
        }
        
        // printerfriendly
        $('#_rrwebapp-button-printerfriendly').button({
            text: false,
            icons: {primary: "ui-icon-print"},
        }).on('click',
              function() {
                var fullurl = $( this ).attr('_rrwebapp_action');
                var selected = new Object({});
                selected['series'] = getFilterValue(_rrwebapp_table,seriesCol);
                selected['gen'] = getFilterValue(_rrwebapp_table,genderCol);
                selected['div'] = getFilterValue(_rrwebapp_table,divisionCol);
                var url = geturl(fullurl);
                var args = geturlargs(fullurl);
                $.extend(args,selected,{'printerfriendly':true});
                newurl = url + '?' + $.param(args);
                newtab(newurl);
        });
            
        
    };  // seriesresults

    function runnerresults(name,series) {
        
        // for future use
        var printerfriendly = false;
        var division = null;
        var gender = null;
        
        // column definitions
        var nameCol = 0;
        var seriesCol = 1;
        var genderCol = 5;
        var divisionCol = 8;
        var timeCol = 10;
        var paceCol = 11;
        var agtimeCol = 12;
        var columndefs = [
                        {targets:[timeCol,paceCol,agtimeCol],type:'racetime'},
                                ];
        
        if (!printerfriendly) {
            if (document.referrer.search('viewstandings') != -1) {
                $('#_rrwebapp-button-back').button()
                    .on('click',
                        function(){
                            window.location.href = document.referrer;
                        });
            } else {
                $('#_rrwebapp-button-back').hide();
            }
        }
        
        if (!printerfriendly){
            var tableparamupdates = {
                    //scrollY: gettableheight()+3, 
                    //scrollXInner: "100%",
                    paging: true,
                    pageLength: 25,
                    buttons: ['csv'],
                    lengthMenu: [[25, 50, 100, -1], [25, 50, 100, "All"]],
                    //orderClasses: false,
                    deferRender: true,
                    columnDefs: columndefs,
                };
            if (name !== 'None') {
                tableparamupdates['order'] = [];
            }
        }
        else {
            var tableparamupdates = {
                    columnDefs: columndefs,
                    orderClasses: false,
            }
        }

        _rrwebapp_table = $('#_rrwebapp-table-runnerresults')
            .dataTable(getDataTableParams(tableparamupdates,printerfriendly))
            .yadcf([
                {
                    column_number:nameCol,
                    filter_container_id:"_rrwebapp_filtername",
                    filter_type:"multi_select",
                    select_type: 'select2',
                    select_type_options: {
                        width: '30em',
                    },
                    filter_reset_button_text: 'all',
                },{
                    column_number:seriesCol,
                    filter_container_id:"_rrwebapp_filterseries",
                    filter_reset_button_text: 'all',
                },{
                    column_number:genderCol,
                    filter_container_id:"_rrwebapp_filtergender",
                    filter_reset_button_text: 'all',
                },{
                    column_number:divisionCol,
                    filter_container_id:"_rrwebapp_filterdivision",
                    filter_reset_button_text: 'all',
                },]);
            
        if (!printerfriendly) {
            resetDataTableHW();
        }
        

        // set name based on caller's preference
        var selectfilter = '#_rrwebapp_filtername select';
        var namechoices = getchoicevalues(selectfilter);
        if ($.inArray(name, namechoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, nameCol, name);
        //} else {
        //    yadcf.exFilterColumn(_rrwebapp_table, nameCol, namechoices[0])            
        }

        // set series based on caller's preference
        var selectfilter = '#_rrwebapp_filterseries select';
        var serieschoices = getchoicevalues(selectfilter);
        if ($.inArray(series, serieschoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, seriesCol, series);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, seriesCol, serieschoices[0])            
        }

        // set division based on caller's preference
        var selectfilter = '#_rrwebapp_filterdivision select';
        var divchoices = getchoicevalues(selectfilter);
        if ($.inArray(division, divchoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, divisionCol, division);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, divisionCol, divchoices[0])            
        }
        
        // set gender based on caller's preference
        selectfilter = '#_rrwebapp_filtergender select';
        var genchoices = getchoicevalues(selectfilter);
        if ($.inArray(gender, genchoices) != -1) {
            yadcf.exFilterColumn(_rrwebapp_table, genderCol, gender);
        } else {
            yadcf.exFilterColumn(_rrwebapp_table, genderCol, genchoices[0])            
        }
        
        // printerfriendly
        $('#_rrwebapp-button-printerfriendly').button({
            text: false,
            icons: {primary: "ui-icon-print"},
        }).on('click',
              function() {
                var fullurl = $( this ).attr('_rrwebapp_action');
                var selected = new Object({});
                selected['series'] = getFilterValue(_rrwebapp_table,seriesCol);
                selected['gen'] = getFilterValue(_rrwebapp_table,genderCol);
                selected['div'] = getFilterValue(_rrwebapp_table,divisionCol);
                var url = geturl(fullurl);
                var args = geturlargs(fullurl);
                $.extend(args,selected,{'printerfriendly':true});
                newurl = url + '?' + $.param(args);
                newtab(newurl);
        });
            
        
    };  // runnerresults

    // define as variable to support replacement during stackoverflow debugging
    var viewstandings = function (division,gender,printerfriendly) {
        // not sure why fudge is needed
        var initialheightfudge = -12;
        
        // Legend
        if (!printerfriendly){
            legend = '<table>\
                        <tr><td><div class="_rrwebapp-class-standings-data-race-dropped">red</div></td><td>points are dropped</td></tr>\
                        <tr><td><div class="_rrwebapp-class-standings-data-overall-award">blue</div></td><td>runner won overall award, not eligible for age group award</td></tr>\
                        <tr><td><div class="_rrwebapp-class-standings-data-division-award">green</div></td><td>runner won age group award</td></tr>\
                     </table>';
            popupbutton.init('#_rrwebapp-button-standings-legend', true, 'Legend', {}, true);
            $('#_rrwebapp-button-standings-legend').on(
                'click', function() { popupbutton.click('#_rrwebapp-button-standings-legend',legend) }
            );
            
            // Race list is kept in accordion above table, for reference
            // height gets changed as accordion changes -- see http://datatables.net/forums/discussion/10906/adjust-sscrolly-after-init/p1
            $( "#_rrwebapp-accordion-standings-races" ).accordion({
              collapsible: true,
              active: 'none',   // see http://stackoverflow.com/questions/2675263/collapse-all-sections-in-accordian-on-page-load-in-jquery-accordian
              activate: function(event,ui) {
                var oSettings = _rrwebapp_table.fnSettings();
                var newheight = gettableheight();
                oSettings.oScroll.sY = newheight;
                $('div.dataTables_scrollBody').height(newheight);
              }
            });
        }

        // table needs to be after accordion declaration so size is set right
        var divisionCol = 0;
        var genderCol = 3;
        var columndefs = [
                    {targets:[divisionCol],bVisible:false},
                    {targets:['_rrwebapp-class-col-place',
                               '_rrwebapp-class-col-race',
                               '_rrwebapp-class-col-total',
                               '_rrwebapp-class-col-nraces'
                               ],type:'num-html'},
                    ];
        if (!printerfriendly){
            var tableparamupdates = {
                scrollY: gettableheight() - initialheightfudge,
                buttons: ['csv'],
                // scrollX: "100%",
                //scrollXInner: "150%",
                columnDefs: columndefs,
                };
        }
        else {
            var tableparamupdates = {
                columnDefs: columndefs,
            }
        }
        _rrwebapp_table = $('#_rrwebapp-table-standings')
            .dataTable(getDataTableParams(tableparamupdates,printerfriendly))
            .yadcf([{
                    column_number:divisionCol,
                    filter_container_id:"_rrwebapp_filterdivision",
                    column_data_type: "html",
                    html_data_type: "text",
                    filter_reset_button_text: false,    // no filter reset button
                },{
                    column_number:genderCol,
                    column_data_type: "html",
                    html_data_type: "text",
                    filter_container_id:"_rrwebapp_filtergender",
                    filter_reset_button_text: 'all',
                },]);
        if (!printerfriendly) {
            resetDataTableHW();
        }
        
        // printerfriendly
        $('#_rrwebapp-button-printerfriendly').button({
            text: false,
            icons: {primary: "ui-icon-print"},
        }).on('click',
              function() {
                var fullurl = $( this ).attr('_rrwebapp_action');
                var selected = new Object({});
                selected['gen'] = getFilterValue(_rrwebapp_table,genderCol);     //getvalue('#_rrwebapp_filtergender');
                selected['div'] = getFilterValue(_rrwebapp_table,divisionCol);   //getvalue('#_rrwebapp_filterdivision');
                var url = geturl(fullurl);
                var args = geturlargs(fullurl);
                $.extend(args,selected,{'printerfriendly':true});
                newurl = url + '?' + $.param(args);
                newtab(newurl);
        });
            
        // find the external filters
        var divfilter = '#_rrwebapp_filterdivision select';
        var genfilter = '#_rrwebapp_filtergender select';

        // force always to have some Division filter, hopefully Overall
        $(divfilter+" option[value='-1']").remove();
        
        // set division based on caller's preference
        // set gender based on caller's preference
        var divchoices = getchoicevalues(divfilter);
        var genchoices = getchoicevalues(genfilter);
        if ($.inArray(division, divchoices) != -1) {
            var usedivision = division;
        } else {
            var usedivision = divchoices[0];
        }
        if ($.inArray(gender, genchoices) != -1) {
            var usegender = gender;
        } else {
            var usegender = genchoices[0]
        }

        yadcf.exFilterColumn(_rrwebapp_table, [[divisionCol, usedivision], [genderCol, usegender]])

        // reset gender column if didn't mean to filter
        if (usegender == "-1") {
            yadcf.exResetFilters( _rrwebapp_table, [genderCol] )
        }
        
        // mouseover races shows race name
        $( document ).tooltip();
    };  // viewstandings

    function choosestandings() {
        function setyearselect( sel ) {
            var apiurl = $( sel ).attr('_rrwebapp_apiurl');
            club = getvalue('#_rrwebapp-choosestandings-select-club')

            // club needs to be set
            if (!club ) {
                return
            }
            
            // save last value
            var selectvalue = getvalue('#_rrwebapp-choosestandings-select-year')
            
            // ajax parameter setup
            ajaxparams = {club:club}
            
            updateselectbyapi('#_rrwebapp-choosestandings-select-year',apiurl,ajaxparams);
            
            // reset last value if possible
            choicevalues = getchoicevalues('#_rrwebapp-choosestandings-select-year')
            if ($.inArray(selectvalue, choicevalues) != -1) {
                setvalue('#_rrwebapp-choosestandings-select-year',selectvalue)
            }
        };
        
        function setseriesselect( sel ) {
            var apiurl = $( sel ).attr('_rrwebapp_apiurl');
            club = getvalue('#_rrwebapp-choosestandings-select-club')
            year = getvalue('#_rrwebapp-choosestandings-select-year')

            // both need to be set
            if (!club || !year) {
                return
            }
            
            // save last value
            var selectvalue = getvalue('#_rrwebapp-choosestandings-select-series')
            
            // ajax parameter setup
            ajaxparams = {club:club,year:year}
            
            updateselectbyapi('#_rrwebapp-choosestandings-select-series',apiurl,ajaxparams);

            // reset last value if possible
            choicevalues = getchoicevalues('#_rrwebapp-choosestandings-select-series')
            if ($.inArray(selectvalue, choicevalues) != -1) {
                setvalue('#_rrwebapp-choosestandings-select-series',selectvalue)
            }
        };
        
        $('#_rrwebapp-choosestandings-select-club')
            .on('change',
                function ( event ) {
                    setyearselect( this );
        });

        $('#_rrwebapp-choosestandings-select-club, #_rrwebapp-choosestandings-select-year')
            .on('change',
                function ( event ) {
                    setseriesselect( '#_rrwebapp-choosestandings-select-year' );
        });

        setyearselect('#_rrwebapp-choosestandings-select-club');
        setseriesselect('#_rrwebapp-choosestandings-select-year');
    };  // choosestandings

    function importspec() {
        
        _rrwebapp_spec_table = $('#_rrwebapp-table-importspec')
            .dataTable(getSpecTableParams());

    };  // importspec

