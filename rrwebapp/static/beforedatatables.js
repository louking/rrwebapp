/**
 * @file provides functions which need to be available before datatables is loaded
 */

// also see RaceResults.clubaffiliations 
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
