// dtchart is used to create the chart from datatables.js
function datatables_chart() {
    var margin = {top: 40, right: 100, bottom: 60, left: 50},
        viewbox_width = 960,
        viewbox_height = 500,
        width = viewbox_width - margin.left - margin.right,
        height = viewbox_height - margin.top - margin.bottom;
    var minagegrade = 20,
        maxagegrade = 100;
    var dot_size = 4.5;

    /* 
     * value accessor - returns the value to encode for a given data object.
     * scale - maps value to a visual display encoding, such as a pixel position.
     * map function - maps from data value to display value
     * axis - sets up axis
     */ 

    // set up x
    // time labels: https://bl.ocks.org/d3noob/0e276dc70bb9184727ee47d6dd06e915
    var xValue = function(d) { return d.date; }, // data -> value
        xScale = d3.scaleTime().range([0, width]), // value -> display
        xMap = function(d) { return xScale(xValue(d));}, // data -> display
        xAxis = d3.axisBottom(xScale)
            .tickFormat(d3.timeFormat("%m/%d/%y"));

    // set up y
    var yValue = function(d) { return d.agpercent; }, // data -> value
        yScale = d3.scaleLinear().range([height, 0]), // value -> display
        yMap = function(d) { return yScale(yValue(d)); }, // data -> display
        yAxis = d3.axisLeft(yScale);

    // set up y domain, fixed to be the same for all runners
    yScale.domain([minagegrade, maxagegrade])

    // add the graph canvas to the body of the webpage
    var dtchart = d3.select(".dt-chart");

    var viewbox = dtchart
      .append("svg")
        .attr("class", "chart")
        .attr("width", viewbox_width)
        .attr("height", viewbox_height)
        .attr("viewBox", "0 0 " + viewbox_width + " " + viewbox_height)
        .attr("preserveAspectRation", "xMidYMid")

    var svg = viewbox.append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var xaxisg = svg.append("g")
            .attr("class", "x dt-chart-axis")
            .attr("transform", "translate(0," + height + ")");
        
    var yaxisg =  svg.append("g")
            .attr("class", "y dt-chart-axis")
            .call(yAxis);

    // y axis label
    viewbox.append("text")
        .style("text-anchor", "middle")
        .attr("transform", "translate("+(margin.left/3)+","+(height/2+margin.top)+")rotate(-90)")
        .text("age grade %age");
    
    // heading
    var headerg = svg.append("g")
            .attr("class", "dt-chart-heading")
          .append("text");
    
    // return text for legend
    function legend_text(d) {
        var meterspermile = 1609.344,
            epsion = 1e-1;
        var subs = {401: '400m', 1001: '1000m', 1609:'1M',3219:'2M',4989:'5K',
                    2993: '3000m', 5000:'5K',8047:'5M',
                    10000:'10K', 15000:'15K',
                    16093:'10M',21082:'HM',21097:'HM',42165:'Marathon',42195:'Marathon',
                    80467:'50M',160934:'100M'};

        var nummeters = Math.round(d.miles*meterspermile);
        if (nummeters in subs) {
            return subs[nummeters];
        } else if (nummeters < 5* meterspermile) {
            return nummeters + 'm';
        } else {
            return d.miles + "M";
        };
    };

    // make responsive, fit within parent
    var aspect = viewbox_width / viewbox_height,
        chart = d3.select(".chart"),
        entrycontent = d3.select(".dt-chart");
    window.onresize = function() {
        var targetWidth = parseFloat(entrycontent.style("width"));  // assumes width in px
        chart.attr("width", targetWidth);
        chart.attr("height", targetWidth / aspect);
    };  // window.onresize

    // dates
    var formatDate = d3.timeFormat("%m/%d/%y"),
        parseDate = d3.timeParse("%Y-%m-%d"),
        bisectDate = d3.bisector(function(d) { return d.date; }).left;

    // set up fill color
    // colors are logarighmic from blue to red
    // domain is in miles (race distance)
    var cValue = function(d) { return d.miles; },
        color = function(d) {
            scale = d3.scaleLog().domain([100,1]);
            return d3.interpolateSpectral( scale(d) );
        };  // color

    // add the tooltip area to the webpage
    var tooltip = d3.select("body").append("div")
        .attr("class", "dt-chart-tooltip")
        .style("opacity", 0);

    function dt_chart_update(data) {
        // set up transition parameters
        var t = d3.transition()
            .duration(0);

        // set up x domain
        xScale.domain(d3.extent(data, function(d) { return d.date; }));

        // update x axis
        xaxisg
          .transition(t)
            .call(xAxis)
          .selectAll(".tick text")
            .style("text-anchor", "end")
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");

        // update y axis
        yaxisg
          .transition(t)
            .call(yAxis);

        // update header
        // can assume that all data is for same person
        var heading = "please make a selection which includes some data";
        if (data.length >= 1) {
            var name = data[0].name;
            var heading = name;
        };
        headerg
          .transition(t)
            .attr("transform", "translate(" + width/2 + ",-10)")
            .style("text-anchor", "middle")
            .text(heading);

        // JOIN new data with old elements
        var dots = svg.selectAll("circle")
            .data(data, function(d) { return d; });

        // EXIT old elements not present in new data
        dots.exit()
            .attr("class", "dt-chart-dots-exit")
          .transition(t)
            .style("fill-opacity", 1e-6)
            .remove();

        // UPDATE old elements present in new data
        dots.attr("class", "dt-chart-dots-update dt-chart-dot")
            .style("fill-opacity", 1)
          .transition(t)
            .attr("cx", xMap)
            .attr("cy", yMap)
            .on("end", function(d,i) {legend.call(d3.legend)});

        // ENTER new elements present in new data
        dots.enter().append("circle")
            .attr("class", "dt-chart-dots-enter dt-chart-dot")
            .attr("r", dot_size)
            .attr("cx", xMap)
            .attr("cy", yMap)
            .attr("data-legend", legend_text)
            .attr("data-legend-pos", function(d) { return d.miles; })
            .style("fill", function(d) { return color(cValue(d));}) 
            .style("fill-opacity", 1e-6)
            .on("mouseover", function(d) {
                tooltip.transition()
                     .duration(200)
                     .style("opacity", .9);
                tooltip.html(d.race + "<br/>" + formatDate(d.date) + " " + d.time + " " + round(yValue(d),1) + "%")
                     .style("left", (d3.event.pageX + 5) + "px")
                     .style("top", (d3.event.pageY - 50) + "px");
            })  // .on("mouseover"
            .on("mouseout", function(d) {
                tooltip.transition()
                     .duration(500)
                     .style("opacity", 0);
            })  // .on("mouseout"
          // give a little extra on final transition before calling d3.legend
          .transition(t)
            .style("fill-opacity", 1)
            .on("end", function(d,i) {legend.call(d3.legend)})

        // update legend after updating dots
        // remove and replace legend for case where empty
        viewbox.selectAll(".legend").remove()
        var legend = viewbox.append("g")
              .attr("class","legend")
              .attr("transform","translate(" + (width + margin.left + 25) + "," + margin.top + ")")
              .style("font-size","12px");

    }   // dt_chart_update

    // when any ajax request is received back from the server, update the chart
    _dt_table.on( 'xhr.dt', function ( e, settings, json, xhr ) {
        // add tableselect keys if no xhr error
        if (!json) throw "error response from api";               

        var data = json.data;

        // data is list of result objects
        // convert agpercent and miles (distance) to number
        var alldata = []
        for (i = 0; i < data.length; i++) {
            // do deep copy of data[i]. Shallow would probably be ok, but why not do deep?
            d = jQuery.extend(true, {}, data[i]);
            d.date = parseDate(d.date);
            // remove % if present, and convert to number
            d.agpercent = +d.agpercent.replace(/\%/g,"");
            d.miles = +d.miles;
            alldata.push(d);
        };  // for
    

        // initial draw or transition to new data
        // see http://bl.ocks.org/d3noob/7030f35b72de721622b8
        dt_chart_update(alldata);

    });    // _dt_table.on( 'xhr.dt'
}

