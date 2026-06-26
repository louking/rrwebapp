/**
 * @file provides functions which need to be available before datatables is loaded
 */

/**
 * @instance {SaEditor} clubaffiliations_copy_saeditor
 * 
 * also see RaceResults.clubaffiliations
 */
var clubaffiliations_copy_saeditor = new SaEditor({
    title: 'Copy Club Affiliations',
    fields: [
                {name: 'club', data: 'club', label: 'From club', 'type': 'select2', className: 'field_req'},
                {name: 'year', data: 'year', label: 'From year', 'type': 'select2', className: 'field_req'},
                {name: 'force', data: 'force', 'type': 'hidden'},
            ],
    buttons: [
                'Copy Club Affiliations',
                {
                    text: 'Cancel',
                    action: function() {
                        this.close();
                    }
                }
            ],
    get_urlparams: function(e, dt, node, config) {
        return {}
    },
    after_init: function() {
        var sae = this;
        sae.saeditor.dependent('club', function(val, data, callback) {
            var that = this;
            var select_tree = sae.select_tree;
            if (select_tree && val) {
                var text = that.field('club').inst('data')[0].text;
                sae.saeditor.field('year').update(select_tree[text].years);
            }
            return {}
        });
        sae.saeditor.on('initEdit', function(e, node, data, items, type){
            sae.saeditor.field('force').set('false');
        });
        var submit_data;
        sae.saeditor.on('preSubmit', function(e, data, action) {
            submit_data = sae.saeditor.get();
        });
        sae.saeditor.on('submitSuccess', function(e, json, data, action) {
            var that = this;
            if (json.cause) {
                // if overwrite requested, force the overwrite
                if (json.confirm) {
                    $("<div>"+json.cause+"</div>").dialog({
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
                                    $( this ).dialog('destroy');
                                    // no editing id, and don't show immediately, reset to what was submitted
                                    sae.saeditor.edit(null, false);
                                    sae.saeditor.set(submit_data);
                                    // now force the update
                                    sae.saeditor.field('force').set('true')
                                    sae.saeditor.submit();
                                }
                            }
                        ],
                    });
                } else {
                    $("<div>Error Occurred: "+json.cause+"</div>").dialog({
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

            } else {
                sae.saeditor.field('force').set('false');
                // show new data
                refresh_table_data(_dt_table, '/admin/clubaffiliations/rest')
            }
        });
    },
    form_values: function(json) {
        var that = this;
        var options = json.options;
        that.select_tree = options;
        var values = json.values;
        // update club select options based on json response
        club_options = [];
        for (const club in options) {
            if (options.hasOwnProperty(club)) {
                club_options.push(options[club].option)
            }
        }
        that.saeditor.field('club').update(club_options);

        // set to values from json response
        return values
    },
});

// need to create this function because of some funkiness of how eval works from the python interface
var clubaffiliations_copy_button = function(url) {
    return clubaffiliations_copy_saeditor.edit_button_hook(url);
}

/**
 * @instance {SaEditor} divisions_copy_saeditor
 * 
 * also see RaceResults.division()
 */
 var divisions_copy_saeditor = new SaEditor({
    title: 'Copy Divisions',
    fields: [
                {name: 'club', data: 'club', label: 'From club', 'type': 'select2', className: 'field_req'},
                {name: 'year', data: 'year', label: 'From year', 'type': 'select2', className: 'field_req'},
                {name: 'force', data: 'force', 'type': 'hidden'},
            ],
    buttons: [
                'Copy Divisions',
                {
                    text: 'Cancel',
                    action: function() {
                        this.close();
                    }
                }
            ],
    get_urlparams: function(e, dt, node, config) {
        return {}
    },
    after_init: function() {
        var sae = this;
        sae.saeditor.dependent('club', function(val, data, callback) {
            var that = this;
            var select_tree = sae.select_tree;
            if (select_tree && val) {
                var text = that.field('club').inst('data')[0].text;
                sae.saeditor.field('year').update(select_tree[text].years);
            }
            return {}
        });
        sae.saeditor.on('initEdit', function(e, node, data, items, type){
            sae.saeditor.field('force').set('false');
        });
        var submit_data;
        sae.saeditor.on('preSubmit', function(e, data, action) {
            submit_data = sae.saeditor.get();
        });
        sae.saeditor.on('submitSuccess', function(e, json, data, action) {
            var that = this;
            if (json.cause) {
                // if overwrite requested, force the overwrite
                if (json.confirm) {
                    $("<div>"+json.cause+"</div>").dialog({
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
                                    $( this ).dialog('destroy');
                                    // no editing id, and don't show immediately, reset to what was submitted
                                    sae.saeditor.edit(null, false);
                                    sae.saeditor.set(submit_data);
                                    // now force the update
                                    sae.saeditor.field('force').set('true')
                                    sae.saeditor.submit();
                                }
                            }
                        ],
                    });
                } else {
                    $("<div>Error Occurred: "+json.cause+"</div>").dialog({
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

            } else {
                sae.saeditor.field('force').set('false');
                // show new data
                refresh_table_data(_dt_table, '/admin/managedivisions/rest')
            }
        });
    },
    form_values: function(json) {
        var that = this;
        var options = json.options;
        that.select_tree = options;
        var values = json.values;
        // update club select options based on json response
        club_options = [];
        for (const club in options) {
            if (options.hasOwnProperty(club)) {
                club_options.push(options[club].option)
            }
        }
        that.saeditor.field('club').update(club_options);

        // set to values from json response
        return values
    },
});

// need to create this function because of some funkiness of how eval works from the python interface
var divisions_copy_button = function(url) {
    return divisions_copy_saeditor.edit_button_hook(url);
}

/**
 * @instance {SaEditor} series_copy_saeditor
 * 
 * also see RaceResults.series()
 */
 var series_copy_saeditor = new SaEditor({
    title: 'Copy Series',
    fields: [
                {name: 'club', data: 'club', label: 'From club', 'type': 'select2', className: 'field_req'},
                {name: 'year', data: 'year', label: 'From year', 'type': 'select2', className: 'field_req'},
                {name: 'force', data: 'force', 'type': 'hidden'},
            ],
    buttons: [
                'Copy Series',
                {
                    text: 'Cancel',
                    action: function() {
                        this.close();
                    }
                }
            ],
    get_urlparams: function(e, dt, node, config) {
        return {}
    },
    after_init: function() {
        var sae = this;
        sae.saeditor.dependent('club', function(val, data, callback) {
            var that = this;
            var select_tree = sae.select_tree;
            if (select_tree && val) {
                var text = that.field('club').inst('data')[0].text;
                sae.saeditor.field('year').update(select_tree[text].years);
            }
            return {}
        });
        sae.saeditor.on('initEdit', function(e, node, data, items, type){
            sae.saeditor.field('force').set('false');
        });
        var submit_data;
        sae.saeditor.on('preSubmit', function(e, data, action) {
            submit_data = sae.saeditor.get();
        });
        sae.saeditor.on('submitSuccess', function(e, json, data, action) {
            var that = this;
            if (json.cause) {
                // if overwrite requested, force the overwrite
                if (json.confirm) {
                    $("<div>"+json.cause+"</div>").dialog({
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
                                    $( this ).dialog('destroy');
                                    // no editing id, and don't show immediately, reset to what was submitted
                                    sae.saeditor.edit(null, false);
                                    sae.saeditor.set(submit_data);
                                    // now force the update
                                    sae.saeditor.field('force').set('true')
                                    sae.saeditor.submit();
                                }
                            }
                        ],
                    });
                } else {
                    $("<div>Error Occurred: "+json.cause+"</div>").dialog({
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

            } else {
                sae.saeditor.field('force').set('false');
                // show new data
                refresh_table_data(_dt_table, '/admin/manageseries/rest')
            }
        });
    },
    form_values: function(json) {
        var that = this;
        var options = json.options;
        that.select_tree = options;
        var values = json.values;
        // update club select options based on json response
        club_options = [];
        for (const club in options) {
            if (options.hasOwnProperty(club)) {
                club_options.push(options[club].option)
            }
        }
        that.saeditor.field('club').update(club_options);

        // set to values from json response
        return values
    },
});

// need to create this function because of some funkiness of how eval works from the python interface
var series_copy_button = function(url) {
    return series_copy_saeditor.edit_button_hook(url);
}

// render upload filename upon upload complete
// return anonymous function as this gets eval'd at initialization
function renderfileid() {
    return function(fileid) {
        var renderfile = fileid ? editor.file('data', fileid).filename : '';
        return renderfile;
    }
}

/**
 * @instance {SaEditor} agegrade_import_saeditor
 * 
 * also see afterdatatables if (location.pathname.includes('/ag_tables')) {
 */
var agegrade_import_saeditor = new SaEditor({
    title: 'Import Age Grade Factors',
    fields: [
                {name: 'table', data: 'table', label: 'Table', 'type': 'readonly'},
                {name: 'gender', data: 'gender', label: 'Gender', 'type': 'select2', 'options': ['F', 'M', 'X'], className: 'field_req'},
                {name: 'type', data: 'type', label: 'Type', 'type': 'select2', 'options': ['road', 'track'], className: 'field_req'},
                {name: 'file', data: 'file', label: 'File', 'type': 'upload', className: 'field_req', ajax: '/admin/agfactoruploads', display: renderfileid()},
            ],
    buttons: [
                {
                    'text': 'Import',
                    'action': function() {
                        this.submit(
                            // success
                            function(json){
                                rows = json.data || [];
                                for (i=0; i<rows.length; i++) {
                                    var rowId = '#' + rows[i].rowid;
                                    _dt_table.row( rowId ).data( rows[i] );
                                }
                                _dt_table.draw();
                        }, 
                            // error
                            null, 
                            // formatData
                            function(data){
                                var that = this;
                                data.action = 'import';
                            }
                        );
                    }
                },
                {
                    'text': 'Clear',
                    'action': function() {
                        confirmed = confirm('Are you sure you want to clear this data?');
                        if (confirmed) {
                            this.submit(
                                // success
                                function(json){
                                    rows = json.data || [];
                                    for (i=0; i<rows.length; i++) {
                                        var rowId = '#' + rows[i].rowid;
                                        _dt_table.row( rowId ).data( rows[i] );
                                    }
                                    _dt_table.draw();
                                }, 
                                // error
                                null, 
                                // formatData
                                function(data){
                                    var that = this;
                                    data.action = 'clear';
                                }
                            );    
                        }
                    }
                },
                {
                    text: 'Cancel',
                    action: function() {
                        this.close();
                    }
                }
            ],
    get_urlparams: function(e, dt, node, config) {
        // exactly one row will be selected
        var id = _dt_table.rows({selected:true}).ids()[0]
        return {
            factortable_id: id
        }
    },
    after_init: function() {
        var sae = this;
        var submit_data;
        sae.saeditor.on('preSubmit', function(e, data, action) {
            submit_data = sae.saeditor.get();
        });
        sae.saeditor.on('submitSuccess', function(e, json, data, action) {
            var that = this;
            if (json.cause) {
                // if overwrite requested, force the overwrite
                $("<div>Error Occurred: "+json.cause+"</div>").dialog({
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
            }
        });
    },
    form_values: function(json) {
        return json
    },
});
// need to create this function because of some funkiness of how eval works from the python interface
var agegrade_import_button = function(url) {
    return agegrade_import_saeditor.edit_button_hook(url);
}

var agegrade_display_button = function(url) {
    return function(e, dt, node, config) {
        var id = _dt_table.rows({selected:true}).ids()[0];

        function formatSecs(secs) {
            if (!secs && secs !== 0) return '';
            secs = Math.round(secs);
            var h = Math.floor(secs / 3600);
            var m = Math.floor((secs % 3600) / 60);
            var s = secs % 60;
            if (h > 0) {
                return h + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
            } else {
                return m + ':' + String(s).padStart(2, '0');
            }
        }

        function formatDist(dist_mm) {
            return parseFloat((dist_mm / 1000000).toFixed(4)) + ' km';
        }

        function buildTable(json) {
            if (!json.distances || json.distances.length === 0) {
                return '<p>No data available for this selection.</p>';
            }
            var th = 'style="padding:3px 8px;border:1px solid #ccc;background:#f0f0f0;white-space:nowrap;"';
            var td = 'style="padding:3px 8px;border:1px solid #ccc;text-align:right;"';
            var tdoc = 'style="padding:3px 8px;border:1px solid #ccc;text-align:right;background:#f8f8f0;"';
            var html = '<table style="border-collapse:collapse;font-size:0.85em;"><thead>';
            html += '<tr><th ' + th + '>Age</th>';
            json.distances.forEach(function(d) {
                html += '<th ' + th + '>' + formatDist(d) + '</th>';
            });
            html += '</tr><tr><th ' + th + '>OC</th>';
            json.distances.forEach(function(d) {
                html += '<td ' + tdoc + '>' + formatSecs(json.oc_secs[String(d)]) + '</td>';
            });
            html += '</tr></thead><tbody>';
            json.ages.forEach(function(age) {
                html += '<tr><th ' + th + '>' + age + '</th>';
                json.distances.forEach(function(d) {
                    var f = json.factors[String(age)] && json.factors[String(age)][String(d)];
                    html += '<td ' + td + '>' + (f !== undefined && f !== null ? f.toFixed(4) : '') + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table>';
            return html;
        }

        function loadFactors($container, $dialog) {
            var gender = $dialog.find('#ag-display-gender').val();
            var surface = $dialog.find('#ag-display-surface').val();
            $container.html('<p>Loading&hellip;</p>');
            $.ajax({
                url: url,
                type: 'get',
                dataType: 'json',
                data: {factortable_id: id, gender: gender, surface: surface},
                success: function(json) {
                    if (json.error) {
                        $container.html('<p>Error: ' + _.escape(json.error) + '</p>');
                    } else {
                        $dialog.dialog('option', 'title',
                            'Age Grade Factors: ' + json.name + ' (' + gender + ', ' + surface + ')');
                        $container.html(buildTable(json));
                    }
                },
                error: function() {
                    $container.html('<p>Request failed.</p>');
                }
            });
        }

        var $container = $('<div>').css({overflow: 'auto', maxHeight: '420px'});
        var $controls = $('<div>').css({'margin-bottom': '8px'}).html(
            'Gender:&nbsp;<select id="ag-display-gender">' +
            '<option value="M">M</option><option value="F">F</option><option value="X">X</option>' +
            '</select>&nbsp;&nbsp;' +
            'Surface:&nbsp;<select id="ag-display-surface">' +
            '<option value="road">road</option><option value="track">track</option>' +
            '</select>'
        );
        var $dialog = $('<div>').append($controls).append($container);

        $dialog.dialog({
            title: 'Age Grade Factors',
            width: 900,
            height: 560,
            modal: true,
            close: function() { $(this).dialog('destroy').remove(); },
            buttons: [
                {
                    text: 'Reload',
                    click: function() { loadFactors($container, $dialog); }
                },
                {
                    text: 'Close',
                    click: function() { $(this).dialog('close'); }
                }
            ]
        });

        loadFactors($container, $dialog);
    };
};

var agegrade_copy_button = function(url) {
    return function(e, dt, node, config) {
        var id = _dt_table.rows({selected:true}).ids()[0];
        var sourceName = (_dt_table.rows({selected:true}).data()[0] || {}).name || '';

        var $input = $('<input type="text">').css({width: '100%', boxSizing: 'border-box'})
                        .val(sourceName ? sourceName + ' (copy)' : '');
        var $msg = $('<p>').css({'margin-bottom': '6px'}).text('New table name:');
        var $dialog = $('<div>').append($msg).append($input);

        $dialog.dialog({
            title: 'Copy Age Grade Table: ' + sourceName,
            width: 420,
            height: 'auto',
            modal: true,
            close: function() { $(this).dialog('destroy').remove(); },
            open: function() {
                $input[0].select();
            },
            buttons: [
                {
                    text: 'Copy',
                    click: function() {
                        var newName = $input.val().trim();
                        if (!newName) {
                            $input.css('border-color', 'red').focus();
                            return;
                        }
                        var $dlg = $dialog;
                        $.ajax({
                            url: url + '?factortable_id=' + id,
                            type: 'post',
                            contentType: 'application/json',
                            dataType: 'json',
                            data: JSON.stringify({new_name: newName}),
                            success: function(json) {
                                if (json.error) {
                                    $msg.text('Error: ' + json.error).css('color', 'red');
                                } else {
                                    var rows = json.data || [];
                                    rows.forEach(function(row) {
                                        var rowId = '#' + row.rowid;
                                        if (_dt_table.row(rowId).any()) {
                                            _dt_table.row(rowId).data(row);
                                        } else {
                                            _dt_table.row.add(row);
                                        }
                                    });
                                    _dt_table.draw();
                                    $dlg.dialog('close');
                                }
                            },
                            error: function() {
                                $msg.text('Request failed.').css('color', 'red');
                            }
                        });
                    }
                },
                {
                    text: 'Cancel',
                    click: function() { $(this).dialog('close'); }
                }
            ]
        });
    };
};

// TODO: should this be moved to loutilities datatables.js?
/**
 * reset datatable data based on effective date
 *
 * @param effective_date_id - element for datepicker to hold effective date, e.g., '#effective-date'
 * @param todays_date_id - button to reset datepicker to today, e.g., '#todays-date-button'
 */
 function set_effective_date(effective_date_id, todays_date_id) {
    var effectivedate = $(effective_date_id);
    var todaysdate = $(todays_date_id);

    // set initial filter to today
    var today = new Date();
    today = today.toISOString().substring(0,10);

    // effective date is datepicker; todays date is button
    effectivedate.datepicker({dateFormat: 'yy-mm-dd'});
    effectivedate.val(today);
    todaysdate.button();

    // handle change of effective date by setting column filters appropriately
    effectivedate.change(function(e) {
        var ondate = effectivedate.val();
        var urlparams = allUrlParams();
        urlparams.ondate = ondate;
        resturl = window.location.pathname + '/rest?' + setParams(urlparams);
        _dt_table.one('draw.dt', function(e, settings) {
             $( '#spinner' ).hide();
        });
        $( '#spinner' ).show();
        // WARNING: nonstandard/nonpublic use of settings information
        var serverSide = _dt_table.settings()[0]['oFeatures']['bServerSide'];
        if (serverSide) {
            // add updated urlparams (with ondate) before sending the ajax request
            _dt_table.one('preXhr.dt', function(e, settings, data) {
                Object.assign(data, urlparams);
            });
            _dt_table.ajax.reload();
        } else {
            refresh_table_data(_dt_table, resturl);
        }
       
    });

    // reset the effective date
    todaysdate.click(function(e) {
        // reset today because window may have been up for a while
        today = new Date();
        today = today.toISOString().substr(0,10);
        effectivedate.val(today);
        effectivedate.change();
    })
}

