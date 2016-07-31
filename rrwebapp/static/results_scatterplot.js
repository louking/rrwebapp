// dtchart is used to create the chart from datatables.js
function dtchart() {
    var margin = {top: 40, right: 80, bottom: 45, left: 50},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom,
        viewbox_width = width + margin.left + margin.right,
        viewbox_height = height + margin.top + margin.bottom,
        minagegrade = 20,
        maxagegrade = 100,
        initialdraw = true;

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
            .tickFormat(d3.timeFormat("%b '%y"));

    // set up y
    var yValue = function(d) { return d.agpercent; }, // data -> value
        yScale = d3.scaleLinear().range([height, 0]), // value -> display
        yMap = function(d) { return yScale(yValue(d)); }, // data -> display
        yAxis = d3.axisLeft(yScale);

    // set up y domain, fixed to be the same for all runners
    yScale.domain([minagegrade, maxagegrade])

    // add the graph canvas to the body of the webpage
    var dtchart = d3.select(".dt-chart");

    var svg = dtchart
      .append("svg")
        .attr("class", "chart")
        .attr("width", viewbox_width)
        .attr("height", viewbox_height)
        .attr("viewBox", "0 0 " + viewbox_width + " " + viewbox_height)
        .attr("preserveAspectRation", "xMidYMid")
      .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // make responsive, fit within parent
    var aspect = viewbox_width / viewbox_height,
        chart = d3.select(".chart"),
        entrycontent = d3.select(".dt-chart");
    window.onresize = function() {
        var targetWidth = parseFloat(entrycontent.style("width"));  // assumes width in px
        chart.attr("width", targetWidth);
        chart.attr("height", targetWidth / aspect);
    };

    // dates
    var formatDate = d3.timeFormat("%m/%d/%y"),
        parseDate = d3.timeParse("%Y-%m-%d"),
        bisectDate = d3.bisector(function(d) { return d.date; }).left;

    // set up fill color
    // colors are logarighmic from blue to red
    // domain is in miles (race distance)
    var cValue = function(d) { return d.miles; },
        // color = d3.scaleLog()
        //     .domain([.01,100])
        //     .range(['green', 'red']);
        color = function(d) {
            scale = d3.scaleLog().domain([100,1]);
            return d3.interpolateSpectral( scale(d) );
        };

    // add the tooltip area to the webpage
    var tooltip = d3.select("body").append("div")
        .attr("class", "dt-chart-tooltip")
        .style("opacity", 0);

    // when any ajax request is received back from the server, update the chart
    _dt_table.on( 'xhr.dt', function ( e, settings, json, xhr ) {
        // add tableselect keys if no xhr error
        if (!json) throw "error response from api";               

        data = json.data;

        // can assume that all data is for same person
        name = data[0].name;

        // data is list of result objects
        // convert agpercent and miles (distance) to number
        alldata = []
        for (i = 0; i < data.length; i++) {
            // do deep copy of data[i]. Shallow would probably be ok, but why not do deep?
            d = jQuery.extend(true, {}, data[i]);
            d.date = parseDate(d.date);
            // remove % if present, and convert to number
            d.agpercent = +d.agpercent.replace(/\%/g,"");
            d.miles = +d.miles;
            alldata.push(d);
        };
    
        // set up x domain, giving buffer so dots don't overlap axis
        xScale.domain(d3.extent(alldata, function(d) { return d.date; }));
    
        // initial draw or transition to new data
        // see http://bl.ocks.org/d3noob/7030f35b72de721622b8
        svg.append("g")
            .attr("class", "dt-chart-axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis)
          .selectAll(".tick text")
            .style("text-anchor", "end")
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");
    
        svg.append("g")
            .attr("class", "dt-chart-axis")
            .call(yAxis)
          .append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text("Age Grade");
    
        svg.append("g")
            .attr("class", "heading")
          .append("text")
            .attr("transform", "translate(" + width/2 + ",-10)")
            .style("text-anchor", "middle")
            .text("age grade performance for " + name);
    
        // draw scatterplot
        svg.selectAll(".dt-chart-dot")
            .data(alldata)
          .enter().append("circle")
            .attr("class", "dt-chart-dot")
            .attr("r", 4.5)
            .attr("cx", xMap)
            .attr("cy", yMap)
            .style("fill", function(d) { return color(cValue(d));}) 
            .on("mouseover", function(d) {
                tooltip.transition()
                     .duration(200)
                     .style("opacity", .9);
                tooltip.html(d.race + "<br/>" + formatDate(d.date) + " " + d.time + " " + round(yValue(d),1) + "%")
                     .style("left", (d3.event.pageX + 5) + "px")
                     .style("top", (d3.event.pageY - 28) + "px");
            })
            .on("mouseout", function(d) {
                tooltip.transition()
                     .duration(500)
                     .style("opacity", 0);
            });

        // need legend
        // TO BE ADDED
    });
}

