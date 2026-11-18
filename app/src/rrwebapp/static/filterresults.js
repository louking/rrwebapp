/**
 * handle filterresults page (#700)
 */
function filterresults() {
    var error_container = $('#error-container');
    var summary = $('#filterresults-summary');
    var warning = $('#filterresults-warning');
    var raceselect = $('#raceid');
    var button = $('#filterresults-button');
    button.button();
    raceselect.select2({
        placeholder: 'select race',
        width: '400px',
    });

    function showerror(cause) {
        error_container.text(cause);
        error_container.show();
    }

    function removeprogress() {
        var progressbar = $('#progressbar');
        if (progressbar.length) {
            progressbar.progressbar('destroy');
            progressbar.remove();
        }
    }

    function done() {
        removeprogress();
        button.button('enable');
    }

    raceselect.on('change', function() {
        var membersonly = raceselect.find('option:selected').attr('data-membersonly');
        if (membersonly == 'false') {
            warning.show();
        } else {
            warning.hide();
        }
    });

    function updateprogress(status_url, progressbar) {
        $.getJSON(status_url, function(data) {
            progressbar.progressbar({value: parseInt(data.current * 100 / data.total)});

            if (data.state == 'PENDING' || data.state == 'PROGRESS') {
                setTimeout(function() { updateprogress(status_url, progressbar); }, 500);
                return;
            }

            done();
            if (data.state == 'SUCCESS' && data.cause == '') {
                var text = data.kept + ' of ' + data.read + ' results kept as possible matches.';
                if (data.agefrommember) {
                    text += ' ' + data.agefrommember + ' kept results had no age group in the file; their age came from the member record.';
                }
                // the file is removed from the server once sent, so the link only works once
                var link = $('<a>').attr('href', data.download).text('Download filtered results');
                link.on('click', function() {
                    link.replaceWith($('<span>').text('Downloaded. Run the filter again if another copy is needed.'));
                    window.location.href = data.download;
                    return false;
                });
                summary.empty()
                    .append($('<p>').text(text))
                    .append($('<p>').append(link))
                    .show();
            } else {
                showerror('Error Occurred: ' + data.cause);
            }
        }).fail(function() {
            done();
            showerror('Error retrieving filter status');
        });
    }

    button.on('click', function() {
        error_container.hide();
        summary.hide();

        if (!raceselect.val()) {
            showerror('Choose a race');
            return;
        }
        if (!$('#file').val()) {
            showerror('Choose a results file');
            return;
        }

        // disable synchronously to prevent duplicate requests
        button.button('disable');
        $('#progressbar-container').after('<div id="progressbar"><div class="progress-label">Uploading...</div></div>');
        var progressbar = $('#progressbar'),
            progressLabel = $('.progress-label');
        progressbar.progressbar({
            value: false,
            // progressLabel needs style - see https://jqueryui.com/progressbar/#label
            change: function() {
                var value = progressbar.progressbar('value');
                if (value !== false) {
                    progressLabel.text(value + '%');
                }
            },
            complete: function() {
                progressLabel.text('Complete!');
            }
        });

        $.ajax({
            type: 'POST',
            url: '/admin/_filterresults',
            data: new FormData($('#filterresults-form')[0]),
            contentType: false,
            cache: false,
            processData: false,
            success: function(data) {
                if (data.success) {
                    updateprogress(data.location, progressbar);
                } else {
                    done();
                    showerror(data.cause);
                }
            },
            error: function(xhr) {
                done();
                if (xhr.status == 413) {
                    showerror('Results file is too large to upload');
                } else {
                    showerror('Unexpected error: ' + xhr.status + ' ' + xhr.statusText);
                }
            }
        });
    });
}
