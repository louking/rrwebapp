$( function() {
    $( "#navigation>ul").addClass("sm sm-blue");
    $( "#navigation>ul" ).smartmenus({
			subMenusSubOffsetX: 1,
			subMenusSubOffsetY: -8
    });

    // all navbar links which are not on this site (i.e., don't start with '/') open in new tab
    $( '.navbar a' ).not('[href^="/"]').attr('target', '_blank');
    // prevent click behavior for empty navigation items which have submenu
    $( '.navbar a[href="#"].has-submenu').click(function(e) {
        e.preventDefault();
    });

    // // register interest group for all links
    // register_group('interest', '#metanav-select-interest', 'a' );
});

// a[hreflang|='en']