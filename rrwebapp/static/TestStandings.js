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
            height = height - (footerheight + 5); // 5 for some padding
        
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

    // redefine
    viewstandings = function(division,gender,printerfriendly) {
        // not sure why fudge is needed
        var initialheightfudge = -12;
        

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

        // table needs to be after accordion declaration so size is set right
        var divisionCol = 0;
        var genderCol = 3;
        var columndefs = [
                    {aTargets:[divisionCol],bVisible:false},
                    {aTargets:['_rrwebapp-class-col-place',
                               '_rrwebapp-class-col-race',
                               '_rrwebapp-class-col-total',
                               '_rrwebapp-class-col-nraces'
                               ],sType:'num-html'},
                    ];

        var tableparams = {
            //sDom: '<"H"Clpr>t',
            dom: 'lfrtip',
            jQueryUI: true,
            paging: false,
            // sScrollY: gettableheight(),
            // bScrollCollapse: true,
            scrollX: "100%",
            // sScrollXInner: "100%",
            infoCallback: function( oSettings, iStart, iEnd, iMax, iTotal, sPre ) {
                var info = "Showing ";
                if (oSettings.oFeatures.bPaginate) {
                    info = info + iStart +" to ";                        
                    info = info + iEnd +" of "+ iMax +" entries";
                } else {
                    info = info + iEnd +" entries";
                }

                return info;
              },
            scrollY: gettableheight() - initialheightfudge,
            //sScrollX: "100%",
            //sScrollXInner: "150%",
            columnDefs: columndefs,
            };

        _rrwebapp_table = $('#_rrwebapp-table-standings')
            .dataTable(tableparams)
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
        //resetDataTableHW();
        

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
            var usegender = divchoices[0];
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
        

        
    };  // viewstandings