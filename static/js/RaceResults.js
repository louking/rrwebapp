$( document ).ready(function(){
    // layout.html
    $('.sessionoption')
        .on('change',
            function ( event ) {
                var apiurl = $( this ).attr('sessionoptionapi')
                var selected = $( this ).val()
                $.ajax({
                    url: $SCRIPT_ROOT + apiurl + '/' + selected,
                    type: 'POST',
                    dataType: 'json',
                    complete: function(data){
                        var success = data.success;
                        location.reload(true)
                        }
                });
            });

    // common
    var toolstatus = 0
    var $toolbutton = $('.toolbutton')
    var $toolcontent = $('.toolpopup').accordion()
    var $tooldialog = $('.tooldialog')
    $toolbutton
        .button({ icons: { secondary: "ui-icon-gear" } })
        .on('click',
            function() {
                if (toolstatus == 0) {
                    $tooldialog.dialog("open")
                    $toolcontent.show()
                    toolstatus = 1
                } else {
                    $tooldialog.dialog("close")
                    $toolcontent.hide()
                    toolstatus = 0
                }
            });
    $tooldialog.dialog({
                        dialogClass: "no-close",
                        draggable: false,
                        //resizeable: false,
                        open:$toolcontent,
                        autoOpen: false,
                        height: "auto",
                        width: "auto",
                        position:{
                                my: "left top",
                                at: "left bottom",
                                of: $toolbutton
                                }
                        })
    
    // manageraces
    if ($('#rr-page-manageraces').length > 0){
        $filterseries = $('#filterseries')
        $filterseries
            //.selectmenu({ icons: { secondary: "ui-icon-triangle-1-s" } })
            .on('change',
                function() {
                    this.form.submit()
                });
        
        // put toolbutton in the right place
        $toolbutton.position({
            my: "left center",
            at: "right+3 center",
            of: $filterseries
        })
    }
    
})

