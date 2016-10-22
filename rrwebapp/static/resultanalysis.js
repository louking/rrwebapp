// define start, cancel button handling for resultanalysis

var task_id = null;

$.fn.dataTable.ext.buttons.start = {
    text: 'Start',
    name: 'start',
    action: function ( e, dt, node, config ) {
        $.post( config.url, function( data ) { 
            task_id = data.task_id;
            _dt_table.button('cancel:name').enable();
            _dt_table.button('start:name').disable();
            ajax_update_progress(config.statusurl + '?task_id=' + data.task_id);
            // alert ( 'Started task ' + data.task_id);
        } )
    }
};

$.fn.dataTable.ext.buttons.cancel = {
    text: 'Cancel',
    name: 'cancel',
    action: function ( e, dt, node, config ) {
        var old_task_id = task_id;
        task_id = null;
        $.post( config.url + '&task_id=' + old_task_id, function( data ) { 
            _dt_table.rows().remove().draw();
            // alert ( 'Canceled task ' + task_id );
        } )
        _dt_table.button('cancel:name').disable();
        _dt_table.button('start:name').enable();
    }
};

function ajax_update_progress(status_url) {
    // maybe the task was canceled. If so just return
    if (task_id == null) { return }

    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
        var percent = parseInt(data.current * 100 / data.total);

        var current = data.current;
        var total = data.total;
        
        var rows = [];
        // loop through status object. See http://stackoverflow.com/questions/921789/how-to-loop-through-plain-javascript-object-with-objects-as-members
        for (var key in data.progress) {
            // skip loop if the property is from prototype
            if (!data.progress.hasOwnProperty(key)) continue;

            var obj = data.progress[key];
            var row = {source: key, 
                       status: obj.status, 
                       lastnameprocessed: obj.lastname,
                       records: obj.processed + ' / ' + obj.total
                      };
            rows.push(row);
        }

        // refresh the rows, draw the table
        // _dt_table is defined globally in datatables.js
        _dt_table.rows().remove();
        _dt_table.rows.add(rows).draw();

        // when we're done
        if (data.state != 'PENDING' && data.state != 'PROGRESS') {
            if (data.state == 'SUCCESS' && data.cause == '') {
                // we're done, desensitize Cancel, sensitize Start
                _dt_table.button('cancel:name').disable();
                _dt_table.button('start:name').enable();
            }
            // assumes 'cause' in data, but
            // what does it mean if data.state != 'SUCCESS'?
            else {
                // something unexpected happened
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
            }
        }
        else {
            // rerun in 0.5 seconds, if there's still a task to check progress on
            setTimeout(function() {
                ajax_update_progress(status_url);
            }, 500);
        }
    });
}

