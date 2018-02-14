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
        // set up import button
        $('#_rrwebapp-button-import').button()
            .click( function( event ) {
                event.preventDefault();
                url = $(this).attr('_rrwebapp-formaction')
                ajax_import_file_background(url,'#_rrwebapp-import-results',false);
            });

        // set up tabulate button
        $('#_rrwebapp-button-tabulate').button()
            .click( function( event ) {
                event.preventDefault();
                url = $('#_rrwebapp-button-tabulate').attr('_rrwebapp-tabulate-url')
                ajax_update_db_noform(url,{},'#_rrwebapp-button-tabulate',false)
            });

        // handle checkbox update
        $('._rrwebapp-editparticipants-checkbox-confirmed')
            .on('click',
                function(){
                    setchecked(this);
                });

        // set up for editing
        var editor = new $.fn.dataTable.Editor( {
            ajax:  crudapi + raceid,
            table: '#_rrwebapp-table-editparticipants',
            display: 'jqueryui',
            idSrc:  'id',
            formOptions: {
                main: {
                    onReturn: 'none'
                }
            },
            fields: [
                { label: 'Result Name:', name: 'resultname',
                  type: 'selectize', options: membernames,
                  opts: { 
                        searchField: 'label',
                        openOnFocus: false
                        },
                },
                { label: 'Place:', name: 'place' },
                { label: 'Age:',  name: 'age' },
                { label: 'Gender:',  name: 'gender',
                  type: 'select', options: {'': 'None', 'M':'M', 'F':'F'},
                },
                { label: 'Time:',  name: 'time'  },
                { label: 'Hometown:',  name: 'hometown'  },
                { label: 'Club:',  name: 'club'  }
            ]
        } );

        // function to set age and gender fields
        function setagegen(name, index) {
            var age = memberagegens[name][index].age;
            var gender = memberagegens[name][index].gender;
            editor.set('age',age);
            editor.set('gender',gender);
        }

        // grab selectize instance and age field
        var $resultname = editor.field('resultname').inst();
        var $age = editor.field('age').input();

        // function to update age and gender based on resultname
        // if multiple members of same name, allow cycle through age/genders
        // if age already in field, default to closest age found
        function updateagegen(e) {
            var name = editor.field('resultname').get().toLowerCase();

            // reset age field
            $('._rrwebapp_button_age_cycle').remove();
            $age.removeClass("_rrwebapp_CRUD_input_short")

            if (name !== '') {
                // only one person with this name
                if (memberagegens[name].length == 1) {
                    setagegen(name, 0);

                // multiple people with this name, create a button to switch between
                } else if (memberagegens[name].length > 1) {
                    var agegen_index;
                    // pick default age/gen to display
                    agegen_index = 0;

                    // if an age is already in the field, find the closest one among the members matching name
                    if (editor.get('age') != '') {
                        agediff = 200;
                        for (i=0; i<memberagegens[name].length; i++) {
                            thisagediff = Math.abs(editor.get('age') - memberagegens[name][i].age);
                            if (thisagediff < agediff) {
                                agediff = thisagediff;
                                agegen_index = i;
                            }
                        }
                    };

                    // update the age and gender fields
                    setagegen(name, agegen_index);

                    // add button to cycle through members of same name
                    $age
                        .addClass("_rrwebapp_CRUD_input_short")
                        .after('<button class=_rrwebapp_button_age_cycle title="More than one member matches this name. Click here to cycle through members">')
                    $('._rrwebapp_button_age_cycle')
                        .button( {
                            icons: {
                                primary: "ui-icon-arrowthick-1-e"
                            }
                        } )
                        .on('click', function() {
                            agegen_index += 1;
                            agegen_index %= memberagegens[name].length;
                            setagegen(name, agegen_index);
                        });

                // not sure how this can happen, but handle gracefully
                } else {                        
                    editor.set('age','');
                    editor.set('gender','');
                }
            
            // nothing in resultname field, clear age, gender
            } else {
                editor.set('age','');
                editor.set('gender','');
            };
        };

        // update tableselects when receive response from server
        editor.on('postSubmit', function(e, json, data, action){
            for (var key in json.choices) {
                if (json.choices.hasOwnProperty(key)) {
                    tableselects[key] = json.choices[key];
                }
            }                
        });

        // update age and gender when editor form is opened or resultname is changed
        editor.on('open', updateagegen);
        $resultname.on('change', updateagegen);
    }
    
    // initialize table before everything else
    var matchCol = getColIndex('Match');
    var typeCol = getColIndex('Type');
    var timeCol = getColIndex('Time');
    var placeCol = getColIndex('Place');
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
                    filter_reset_button_text: 'all', 
                }];

    _rrwebapp_table = $('#_rrwebapp-table-editparticipants')
        // when the ajax request is received back from the server, update the tableselects object
        .on( 'xhr.dt', function ( e, settings, json, xhr ) {
            // add tableselect keys if no xhr error
            if (json) {
                for (key in json.tableselects) {
                    tableselects[key] = json.tableselects[key];
                }                    
            }
        })

        // when the page has been drawn, need to do a lot of housekeeping
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

            // handle changes of selected runner and confirm checkbox
            $('._rrwebapp-editparticipants-select-runner, ._rrwebapp-editparticipants-checkbox-confirmed')
                .off('change')  // remove any listeners left over from previous draw
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
            serverSide: true,
            ajax: tabledata,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
            columns: [
                {
                    data: null,
                    defaultContent: '',
                    className: 'select-checkbox',
                    orderable: false
                },
                // when Editor idSrc option is used with select, this column gets removed from the table
                // { data: 'id',           name: 'id',          visible: false },   
                { data: 'place',        name: 'place',       className: 'dt-body-center',
                  render: function ( data, type, row, meta ) {
                    if (Math.round(data) == data) {
                        return Math.round(data)
                    } else {
                        return data                            
                    }
                  }
                 },
                { data: 'resultname',   name: 'resultname' },
                { data: 'gender',       name: 'gender',      className: 'dt-body-center' },
                { data: 'age',          name: 'age',         className: 'dt-body-center' },
                { data: 'disposition',  name: 'disposition', className: 'dt-body-center' },
                { data: 'membertype',   name: 'membertype',  className: 'dt-body-center', visible: !membersonly },
                { data: 'confirm',      name: 'confirm',     className: 'dt-body-center',
                  render: function ( data, type, row, meta ) {
                    var val = '' 
                        + '<input class="_rrwebapp-editparticipants-checkbox-confirmed" type="checkbox" ' 
                        + ((data) ? 'checked ' : ' ') 
                        + 'id="_rrwebapp-editparticipants-checkbox-confirmed-' + row.id + '" ' 
                        + '_rrwebapp-field=\'confirmed\' ' 
                        + '_rrwebapp-apiurl=' + fieldapi + row.id + '>\n' 
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
                            + ((!membersonly) ? ' _rrwebapp-newrunner-name="' + row.resultname + '" _rrwebapp-newrunner-gender="' + row.gender + '"' : '')
                            + ' _rrwebapp-apiurl=' + fieldapi + row.id + '>\n'
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
            order: [placeCol, 'asc'], 
        }))
        .yadcf(yadcffilters);

    // set initial table height
    resetDataTableHW();

    // set up widgets at top of page
    if (writeallowed) {
        toolbutton.$widgets.css({height:"0px"});   // no more widgets in container            
        toolbutton.position({my: "left center", at: "right+3 center", of: '#_rrwebapp_filtermatch'});                
    }

};  // editparticipants

