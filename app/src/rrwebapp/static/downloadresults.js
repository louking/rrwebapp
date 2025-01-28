/**
 * handle downloadresults page
 * 
 * @param {boolean} writeallowed - true if write allowed
 */
function downloadresults() {
    // set up select2 options
    var rsu_year = $('#rsu_year');
    var rsu_distance = $('#rsu_distance');
    var rsu_resultsset = $('#rsu_resultsset');
    var error_container = $('#error-container');
    var progressbar_container = $('#progressbar-container');
    var submit_button = $('.submitbutton input');
    submit_button.button();
    submit_button.button('disable');

    function create_rsu_year() {
        rsu_year.select2({
            placeholder: 'select year',
            width: '100px',
        });
    };

    function create_rsu_distance() {
        rsu_distance.select2({
            placeholder: 'select distance',
            width: '200px',
        });
    };

    function create_rsu_resultsset() {
        rsu_resultsset.select2({
            placeholder: 'select results',
            multiple: true,
            width: '300px',
        });
    };

    $("#url").on('change', function(){
        // hide all hidden fields
        $('.submitbutton').hide();
        submit_button.button('disable');
        $('.runsignup').hide();
        error_container.text('');
        error_container.hide();

        // prepare for new change handling
        rsu_year.off('change');
        rsu_distance.off('change');

        // determine url
        var url = $("#url").val();
        url = encodeURIComponent(url)

        // let user know we're doing something
        progressbar_container.after('<div id="progressbar"><div class="progress-label">Loading...</div></div>');
        var progressbar = $('#progressbar');
        progressbar.progressbar();

        // get data for pulldowns
        $.getJSON('/admin/_downloadresults?url='+url, function(data) {
            // we're done getting data
            progressbar.progressbar('destroy');
            progressbar.remove();

            // maybe an error occurred
            if (data.error) {
                // indicate what the error was
                error_container.text(data.error);
                error_container.show();
                return;
            };

            // if we've come here we have a url we understand, set options based on returned data
            rsu_year.empty().trigger('change');
            rsu_distance.empty().trigger('change');
            rsu_resultsset.empty().trigger('change');

            // set pulldowns to appropriate options
            var years = Object.keys(data.options);
            years.sort().reverse();
            for (var i=0; i<years.length; i++) {
                var year = years[i];
                var newoption = new Option(year, year);
                rsu_year.append(newoption).trigger('change');
            };
            create_rsu_year();

            // handle distance change
            rsu_distance.on('change', function() {
                rsu_resultsset.empty().trigger('change');
                var year = rsu_year.val();
                var distance = rsu_distance.val();
                // there may not be a distance after year is first loaded
                if (distance) {
                    var resultssets = data.options[year][distance];
                    resultssets.sort((a, b) => (a.text > b.text) ? 1 : ((a.text < b.text) ? -1 : 0) );
                    for (var i=0; i<resultssets.length; i++) {
                        var resultsset = resultssets[i];
                        var newoption = new Option(resultsset.text, resultsset.id);
                        rsu_resultsset.append(newoption).trigger('change');
                    };
                    create_rsu_resultsset();
                };
            });

            // handle year change, and set most recent year
            rsu_year.on('change', function() {
                rsu_distance.empty().trigger('change');
                rsu_resultsset.empty().trigger('change');
                var year = rsu_year.val();
                var distances = Object.keys(data.options[year]);    
                // should distances be sorted somehow? not clear what the format is, 
                // or what to do for mixed units (miles vs km)
                for (var i=0; i<distances.length; i++) {
                    var distance = distances[i];
                    var newoption = new Option(distance, distance);
                    rsu_distance.append(newoption).trigger('change');
                };
                create_rsu_distance();
                rsu_distance.val(distances[0]).trigger('change');
            });
            rsu_year.val(years[0]).trigger('change');
            
            // show hidden fields
            $('.submitbutton').show();
            submit_button.button('enable');
            if (data.service == 'runsignup') {
                // update service
                $('#service').val('runsignup');
                
                // show selects
                $('.runsignup').show();

            } else {
                // indicate we don't know the service
                error_container.text('internal error: unknown service: ' + data.service);
                error_container.show();
                return;
            }
        });
    });
}