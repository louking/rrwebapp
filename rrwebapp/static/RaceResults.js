    // round a value to a particular precision
    function round(value, precision) {
        var multiplier = Math.pow(10, precision || 0);
        return Math.round(value * multiplier) / multiplier;
    }

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

    // return date for yyyy-mm-dd string
    function toDate(dateStr) {
        var parts = dateStr.split("-");
        return new Date(parts[0], parts[1] - 1, parts[2]);
    }

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

    function ajax_update_db_noform_resp(url,addparms,data,sel,callback,showprogress) {
        if (showprogress) {
            $('#progressbar').progressbar('destroy');
            $('#progressbar').remove();
        }
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
                                ajax_update_db_noform(url,addparms,sel,true,callback,showprogress);
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

    function ajax_update_db_noform(urlpath,addparms,sel,force,callback,showprogress) {
        // force = true means to overwrite existing data, not necessarily used by target page
        addparms.force = force

        var url = urlpath +'?'+$.param(addparms)

        $.ajax({
            type: 'POST',
            url: url,
            contentType: false,
            cache: false,
            async: true,
            success: function(data) {
                ajax_update_db_noform_resp(urlpath,addparms,data,sel,callback,showprogress);
            },
        });

        if (showprogress) {
            // show we're doing something
            $('#progressbar-container').after('<div id="progressbar"><div class="progress-label">Loading...</div></div>');
            progressbar = $('#progressbar').progressbar({value:false});
        }
    };

    function ajax_import_file_resp(urlpath,formsel,data) {
        window.console && console.log(data);
        $('#progressbar').progressbar('destroy');
        $('#progressbar').remove();

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
            async: true,
            success: function(data) {ajax_import_file_resp(urlpath,formsel,data)},
        });

        // show we're doing something
        $('#progressbar-container').after('<div id="progressbar"><div class="progress-label">Loading...</div></div>');
        progressbar = $('#progressbar').progressbar({value:false});

        // kludge because we're starting to move away from global toolbutton
        if (toolbutton.$tooldialog) {
            toolbutton.close();
        }
    };

    function ajax_update_progress(status_url, progressbar) {
        // send GET request to status URL
        $.getJSON(status_url, function(data) {
            // update UI
            var percent = parseInt(data.current * 100 / data.total);

            var current = data.current;
            var total = data.total;
            progressbar.progressbar({value:percent});

            // when we're done
            if (data.state != 'PENDING' && data.state != 'PROGRESS') {
                if (data.state == 'SUCCESS' && data.cause == '') {
                    // we're done, remove progress bar and redirect if necessary
                    $('#progressbar').progressbar('destroy');
                    $('#progressbar').remove();
                    if (data.redirect){
                        window.location.replace(data.redirect);
                    } else {
                        location.reload(true);
                    };
                }
                else {
                    // something unexpected happened
                    $("<div>Error Occurred: " + data.cause + "</div>").dialog({
                        dialogClass: 'no-titlebar',
                        height: "auto",
                        buttons: [
                            {   text:  'OK',
                                click: function(){
                                    $( this ).dialog('destroy');
                                    location.reload(true);
                                }
                            }
                        ],
                    });
                }
            }
            else {
                // rerun in 0.5 seconds
                setTimeout(function() {
                    ajax_update_progress(status_url, progressbar);
                }, 500);
            }
        });
    }

    function ajax_import_file_background_resp(urlpath,formsel,data) {
        window.console && console.log(data);
        if (data.success) {

            // show we're doing something and start updating progress
            $('#progressbar-container').after('<div id="progressbar"><div class="progress-label">Initializing...</div></div>');
            var status_url = data.location;
            var current = data.current;
            var total = data.total;
            var percent = current * 100 / total;
            var progressbar = $('#progressbar'),
                progressLabel = $('.progress-label');
            progressbar.progressbar({
                value: percent,
                // progressLabel needs style - see https://jqueryui.com/progressbar/#label
                change: function () {
                    progressLabel.text( progressbar.progressbar( 'value') + '%' )
                },
                complete: function () {
                    progressLabel.text( 'Complete!' )
                }
            });
            ajax_update_progress(status_url, progressbar);
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
                                ajax_import_file_background(urlpath,formsel,true);
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

    function ajax_import_file_background(urlpath,formsel,force) {
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
            async: true,
            success: function(data) {ajax_import_file_background_resp(urlpath,formsel,data)},
            error: function() {
                alert('Unexpected error');
            }
        });

        // kludge because we're starting to move away from global toolbutton
        if (toolbutton.$tooldialog) {
            toolbutton.close();
        }
    };


    // manageraces
    function manageraces( writeallowed, toolscontent ) {
        if (writeallowed) {
            var tools = new EditorButtonDialog({
                content: toolscontent,
                accordian: true,
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

            var $importraces = $('#manageracesImport');
            $importraces.click( function( event ) {
                event.preventDefault();
                url = $(this).attr('_rrwebapp-formaction')
                ajax_import_file(url,'#import-races',false);
                tools.close();
            });
        };

        // manageraces_tablebuttons (for both table and editor events, so only one parameter
        var manageraces_tablebuttons = function(selector) {
            selector.each(function(){
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

            selector.click(function(){
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
                        <p>Import the selected race's results as a CSV file. Please read the <a href='"+importdoc+"' target='_blank'>Import Guide</a> for information on the column headers and data format.</p>\
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
                            ajax_import_file_background(formaction,'#'+formid,false);
                        });
                }
                popupbutton.click(this, popupcontent, popupaction)
            });
        }

        // make sure table buttons are drawn and behave properly
        // note draw fires after edit, and edited value will come back with needswidget class
        function add_results_widget() {
            manageraces_tablebuttons($("._rrwebapp-needswidget"));
            $("._rrwebapp-needswidget").removeClass('_rrwebapp-needswidget')
        }
        _dt_table.on('draw.dt', add_results_widget);
        add_results_widget();
    };  // manageraces

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

    // clubaffiliations
    function clubaffiliations() {

        // force update of alternates
        editor.on('initEdit', function(e, node, data, items, type) {
            editor.field('alternates').update(data.alternates);
            editor.field('alternates').val(data.alternates);
        })

        clubaffiliations_copy_saeditor.init();

    };  // clubaffiliations

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

        // set series, division and gender based on caller's preferences
        var serieschoices = getchoicevalues('#_rrwebapp_filterseries select');
        var divchoices = getchoicevalues('#_rrwebapp_filterdivision select');
        var genchoices = getchoicevalues('#_rrwebapp_filtergender select');

        // set default series, division, gender if included in current filter
        filtercolumns = [];
        if ($.inArray(series, serieschoices) != -1) {
            filtercolumns.push([seriesCol,series])
        } else {
            if (serieschoices.length > 1) {
                filtercolumns.push([seriesCol,serieschoices[1]]);
            }
        }
        if ($.inArray(division, divchoices) != -1) {
            filtercolumns.push([divisionCol, division]);
        }
        if ($.inArray(gender, genchoices) != -1) {
            filtercolumns.push([genderCol, gender]);
        }

        // set up external filters
        yadcf.exFilterColumn(_rrwebapp_table, filtercolumns);

        // force always to have some Series filter
        //$("#_rrwebapp_filterseries select option[value='-1']").remove();

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


        // set filters based on caller's preference
        var filtercolumns = [];
        var namechoices = getchoicevalues('#_rrwebapp_filtername select');
        var serieschoices = getchoicevalues('#_rrwebapp_filterseries select');
        var divchoices = getchoicevalues('#_rrwebapp_filterdivision select');
        var genchoices = getchoicevalues('#_rrwebapp_filtergender select');

        // set default name, series, gender if included in current filter
        if ($.inArray(name, namechoices) != -1) {
            filtercolumns.push([nameCol, [name]]);  // name needs to be list for multi-select
        }
        if ($.inArray(series, serieschoices) != -1) {
            filtercolumns.push([seriesCol, series]);
        }
        if ($.inArray(division, divchoices) != -1) {
            filtercolumns.push([divisionCol, division]);
        }
        if ($.inArray(gender, genchoices) != -1) {
            filtercolumns.push([genderCol, gender]);
        }

        // set up external filters
        yadcf.exFilterColumn(_rrwebapp_table, filtercolumns);

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
                        <tr><td><div class="row-overall-award">blue</div></td><td>runner won overall award, not eligible for division award</td></tr>\
                        <tr><td><div class="row-division-award">green</div></td><td>runner won division award</td></tr>\
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
                // commented out due to #390, now lets standings table just get
                // pushed down when races accordian opened without trying to resize
                // activate: function(event,ui) {
                //   var oSettings = _rrwebapp_table.fnSettings();
                //   var newheight = gettableheight();
                //   oSettings.oScroll.sY = newheight;
                //   $('div.dataTables_scrollBody').height(newheight);
                // }
            });
        }

        // table needs to be after accordion declaration so size is set right
        var divisionCol = 0;
        var nameCol = 2;
        var genderCol = 3;
        var clubCol = 5;
        var columndefs = [
                    {targets: [divisionCol],bVisible:false},
                    {targets:['_rrwebapp-class-col-place',
                               '_rrwebapp-class-col-race',
                               '_rrwebapp-class-col-total',
                               '_rrwebapp-class-col-nraces'
                               ],type:'html-num'},
                    ];
        if (!printerfriendly){
            var tableparamupdates = {
                scrollY: gettableheight() - initialheightfudge,
                buttons: ['csv'],
                columnDefs: columndefs,
                fixedColumns: {
                                leftColumns: 3,
                                rightColumns: 1,
                              },
                };
        }
        else {
            var tableparamupdates = {
                columnDefs: columndefs,
            }
        }
        var yadcf_coldefs = [
            {
                column_number:divisionCol,
                filter_container_id:"_rrwebapp_filterdivision",
                column_data_type: "html",
                html_data_type: "text",
                filter_reset_button_text: false,    // no filter reset button
            },
            {
                column_number:genderCol,
                column_data_type: "html",
                html_data_type: "text",
                filter_container_id:"_rrwebapp_filtergender",
                filter_reset_button_text: 'all',
            }
        ]
        var clubfilterid = '#_rrwebapp_filterclub';
        if ($(clubfilterid).length) {
            yadcf_coldefs.push({
                column_number:clubCol,
                column_data_type: "html",
                html_data_type: "text",
                filter_container_id:"_rrwebapp_filterclub",
                filter_reset_button_text: 'all',
            });
        }
        _rrwebapp_table = $('#_rrwebapp-table-standings')
            .dataTable(getDataTableParams(tableparamupdates,printerfriendly))
            .yadcf(yadcf_coldefs);
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

        // set filters based on caller's preference
        filtercolumns = [];
        var divchoices = getchoicevalues('#_rrwebapp_filterdivision select');
        var genchoices = getchoicevalues('#_rrwebapp_filtergender select');

        // set default division, gender if included in current filter
        if ($.inArray(division, divchoices) != -1) {
            filtercolumns.push([divisionCol, division]);
        }
        if ($.inArray(gender, genchoices) != -1) {
            filtercolumns.push([genderCol, gender]);
        }

        yadcf.exFilterColumn(_rrwebapp_table, filtercolumns)

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

$(function() {
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

    // sort extension for 'agtrend'(nn%/yr)
    jQuery.extend( jQuery.fn.dataTableExt.oSort, {
        "agtrend-pre": function ( a ) {
            if (!a || a == '') {return -100};
            var x = (a == "-") ? 0 : a.replace( /%\/yr/, "" );
            return parseFloat( x );
        },

        "agtrend-asc": function ( a, b ) {
            return ((a < b) ? -1 : ((a > b) ? 1 : 0));
        },

        "agtrend-desc": function ( a, b ) {
            return ((a < b) ? 1 : ((a > b) ? -1 : 0));
        }
    } );


    // common functions

    // special processing for nav standings standalone editor
    var navstandingsdepth = 0;
    var dependentfields = ['club', 'year'];
    function navstandingsopen(editor, buttons) {
        function disable_buttons() {
            var localbuttons = _.cloneDeep(buttons);
            for (var i=0; i<localbuttons.length; i++) {
                localbuttons[i].className = 'disabled';
                localbuttons[i].action = function() {}; // no-op
            }
            editor.buttons(localbuttons);
        }
        function enable_buttons() {
            editor.buttons(buttons);
        }
        function navstandingsupdate() {
            // disable all buttons (should only be one 'Show Standings' button)
            navstandingsdepth += 1;
            disable_buttons();

            $.post('/standings/_getseries?' + $.param({club:editor.field('club').val(), year:editor.field('year').val()}),
                success=function(data, textStatus, jqXHR) {
                    navstandingsdepth -= 1;
                    if (data.success) {
                        editor.field('series').update(data.choices);
                        if (navstandingsdepth == 0) {
                            // buttons enabled in editor.dependent('series, ...)
                            // enable_buttons();
                        }
                    } else {
                        console.log('need error handling here');
                    }
                })
        };

        // when any dependent field update, change series options
        editor.dependent(dependentfields, function(val, data, callback) {
            navstandingsupdate();
            return {};
        });

        // disable all buttons if series not selected (should only be one 'Show Standings' button)
        editor.dependent('series', function(val, data, callback) {
            if (val) {
                enable_buttons();
            } else {
                disable_buttons();
            }
            return {};
        });

        // initial update to series pulldown
        navstandingsupdate();
    }
    function navstandingsclose(editor, buttons) {
        editor.undependent(dependentfields);
    }

    // special link processing for navigation
    $("a").click(function( event ){
        // for slow loading links
        var img = $(this).attr('_rrwebapp-loadingimg');
        if (img) {
            $(this).after('<div id="progressbar"><div class="progress-label">Loading...</div></div>');
            $('#progressbar').progressbar({
                value: false,
            });
        }

        // use form to gather url arguments
        var formopts = $(this).attr('popup_form')
        if (formopts) {
            event.preventDefault();
            var opts = JSON.parse(formopts);

            // convert functions for buttons - see http://stackoverflow.com/questions/3946958/pass-function-in-json-and-execute
            // this assumes buttons is array of objects
            // TODO: handle full http://editor.datatables.net/reference/api/buttons() capability, i.e., string or single object
            for (i=0; i<opts.buttons.length; i++) {
                // legacy https://editor.datatables.net/reference/type/button-options
                if (opts.buttons[i].fn) opts.buttons[i].fn = new Function(opts.buttons[i].fn);
                // updated - note eval doesn't work on 'function() { ... }' so we leave out the function() and create it here
                if (opts.buttons[i].action) opts.buttons[i].action = new Function(opts.buttons[i].action);
            }

            var naveditor = new $.fn.dataTable.Editor ( opts.editoropts )
                .title( opts.title )
                .buttons( opts.buttons )
                .edit( null, false )
                .open();
            if (opts.onopen) {
                var navonopen = eval(opts.onopen)
                // note we just opened the standalone editor
                // the link click is the only way this editor can be opened
                navonopen(naveditor, opts.buttons);
            }
            // onclose should do any cleanup required
            if (opts.onclose) {
                var navonclose = eval(opts.onclose)
                naveditor.on('close', function(e, mode, action) {
                    navonclose(naveditor, opts.buttons);
                })
            }
        }
    });

    // decorate buttons
    $("._rrwebapp-actionbutton").button();
    $("._rrwebapp-simplebutton").button();
    
    // get confirmation for any deletes
    $("._rrwebapp-deletebutton").on('click', function(event){getconfirmation(event,'Delete','Please confirm item deletion')});


});

