// datatables_chart is used to create the chart from datatables.js
function datatables_chart() {
    var margin = {top: 40, right: 100, bottom: 60, left: 50},
        viewbox_width = 960,
        viewbox_height = 500,
        width = viewbox_width - margin.left - margin.right,
        height = viewbox_height - margin.top - margin.bottom;
    var minagegrade = 20,
        maxagegrade = 100;
    var dot_size = 4.5;
    var meterspermile = 1609.344;

    var progressbar = $("#progressbar");
    progressbar.css("width", viewbox_width);
    var inprogress = 0,
        progressbarcreated = false;

    var trendlimits = [
            //                             [min, max)
            { name: '<5K',          range: [0,5000],            color: 'blue' },
            { name: '5K to <HM',    range: [5000,21082],        color: 'green' },
            { name: 'HM to Mara',   range: [21082, 42196],      color: 'orange' },
            { name: 'Ultra',        range: [42196, 200000],     color: 'red' },
        ],
        trendbucket = {};

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
    var dtchart = d3.select(".dt-chart")
        .attr("class", "chart dt-chart-chart dt-chart-chartdisplay");

    // table is in same position as chart
    var chartposition = $(".dt-chart-chart").position();

    $('#datatable').on( 'init.dt', function (e, settings, json) {
        // following code doesn't work for some reason, putting in dt_chart.css for now
        $(".dataTables_wrapper")
            .css("position", "absolute")
            .css("top", 0);
        $(".dt-chart-table")
            .css("left", chartposition.left)
            .css("top", chartposition.top+5);
    } );

    var viewbox = dtchart
      .append("svg")
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
    
    // make responsive, fit within parent
    var aspect = viewbox_width / viewbox_height,
        chart = d3.select(".chart"),
        entrycontent = d3.select(".dt-chart-chart");
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
            var scale = d3.scaleLog().domain([0.1,1,5,10,13,26,100]);
            scale.range([
                    d3.rgb(0,0,255),
                    d3.rgb(0,140,255),
                    d3.rgb(140,255,0),
                    d3.rgb(255,255,0),
                    d3.rgb(255,150,0),
                    d3.rgb(255,0,140),
                    d3.rgb(255,0,255)
                ]);
            // return d3.interpolateSpectral( scale(d) );
            return scale(d);
        };  // color

    // add the tooltip area to the webpage
    var tooltip = d3.select("body").append("div")
        .attr("class", "dt-chart-tooltip dt-chart-chartdisplay")
        .style("opacity", 0);

    // add trendtable. draggable
    var divx = $(entrycontent.node()).position().left+margin.left,
        divy = $(entrycontent.node()).position().top+height+margin.top-200;

    var trendtableopacity = 0;
    var trendtable = d3.select("body").append("table")
        .attr("class", "dt-chart-trendtable dt-chart-trendtablehandle dt-chart-chartdisplay")
        .data( [ {"x": divx, "y": divy} ])
        .style("left", divx+'px')
        .style("top",  divy+'px')
        .style("opacity", 0)
        .call(dragdiv)
        .on("mouseover", function(d) {
            thispos = $(trendtable.node()).position()
            tooltip.transition()
                 .duration(200)
                 .style("opacity", trendtableopacity);
            tooltip.html("drag me wherever you want")
                 .style("left", (thispos.left + 70) + "px")
                 .style("top", (thispos.top - 30) + "px");
        })  // .on("mouseover"
        .on("mouseout", function(d) {
            tooltip.transition()
                 .duration(500)
                 .style("opacity", 0)
        }); // .on("mouseout"

        // .style("opacity", 0);
    var trendtablehdr = trendtable.append("tr");
    trendtablehdr.append("th").text("")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("line")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("num")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("avg")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("min")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("max")
    trendtablehdr.append("th").attr("class","dt-chart-trenddata").text("trend")

    // return text for legend
    function legend_text(d) {
        var subs = {1609:'1M', 3001:'3000m', 3219:'2M', 4989:'5K', // 3001 because of data error in scoretility
                    5000:'5K', 5001:'5K', 8047:'5M', // 5001 because of data error in scoretility
                    10000:'10K', 10002:'10K', 15000:'15K',  // 10002 because of data error in scoretility
                    16093:'10M', 21082:'HM', 21097:'HM', 42165:'Marathon', 42195:'Marathon',
                    80467:'50M', 160934:'100M'};

        var nummeters = Math.round(d.miles*meterspermile);
        if (nummeters in subs) {
            return subs[nummeters];
        } else if (nummeters < 5000) {
            return nummeters + 'm';
        } else {
            return round(d.miles,1) + "M";
        };
    };

    // deduplicate data
    function deduplicate(data) {
        // sort by date-distance-time
        // when distance is within epsilon and time is the same, assume same race
        stats = data.slice()
        stats.sort(function(a,b) {
            if (a.date < b.date) { return -1; } 
            if (a.date > b.date) { return 1;  } 
            // dates are equal
            if (a.miles < b.miles) { return -1; }
            if (a.miles > b.miles) { return 1;  }
            // miles are equal, check time
            return a.timesecs - b.timesecs;
        })

        // TODO: add true priority handling
        // deduplicate stats, paying attention to priority when races determined to be the same
        var EPS = .1;   // if event distance is within this tolerance, assumed the same
        var deduped = [];
        var stat, prio;
        while (stats.length > 0) {
            thisstat = stats.shift();
            var sameraces = [{prio:1, stat:thisstat}];

            // pull races off stats when the race date, distance, time are the same
            // distance has to be within epsilon to be deduced to be the same
            while (stats.length > 0
                    && thisstat.date.getTime() == stats[0].date.getTime()
                    && Math.abs((thisstat.miles - stats[0].miles) / thisstat.miles) <= EPS
                    && thisstat.timesecs == stats[0].timesecs) {
                stat = stats.shift();
                sameraces.push( {'prio':1, 'stat':stat} );
            }

            sameraces.sort(function(a,b) { return a.prio - b.prio; });
            prio = sameraces[0].prio;
            stat = sameraces[0].stat;
            deduped.push(stat);
        }

        var dupremoved = data.length - deduped.length;
        if (dupremoved > 0) {
            console.log(dupremoved + ' duplicate points removed');
        }

        return deduped;
    };

    // draw a trend line
    function drawTrendLine(container, classname, data, color, label) {
        var stats = {};
        stats.n = data.length;

        // calculate states even for one point
        // but trendline needs to be at least two points
        if (stats.n > 0) {
            var X = data.map( xMap );
            var Y = data.map( yMap );
            var lr = linearRegression(Y, X);
            var minXmap = d3.min(data, xMap);
            var maxXmap = d3.max(data, xMap);
            var maxY = d3.max(data, yValue);
            var meanY = d3.mean(data, yValue);
            var minY = d3.min(data, yValue);
            if (stats.n > 1) {
                var trendline = container.append("line")
                    .attr("class", classname)
                    .attr("x1", minXmap )
                    .attr("y1", lr.fn(minXmap) )
                    .attr("x2", maxXmap )
                    .attr("y2", lr.fn(maxXmap) )
                    .style("stroke", color)
                    .style("stroke-width", 1.5);
            }

            stats.min = minY;
            stats.max = maxY;
            stats.mean = meanY;
            stats.slope = -lr.slope;    // slope is inverted because y=0 at top

            // determine improvement, which is percentage per year
            var x1 = d3.min(data, xValue).getTime();
            var y1 = yScale.invert(lr.fn(minXmap));
            var x2 = d3.max(data, xValue).getTime();
            var y2 = yScale.invert(lr.fn(maxXmap));
            var years = (x2-x1)/(1000*60*60*24*365); // convert milliseconds to year;
            stats.improvement = (y2-y1)/years;  // 100 is 100% improvement per year
        };
        
        return stats;
    };

    // clear trends
    function clearTrendBuckets() {
        trendbucket = {};
        for (var i=0; i<trendlimits.length; i++) {
            trendbucket[trendlimits[i].name] = [];
        }
    };

    // add point to trendbucket bucket
    function addResultsToTrendBuckets(data) {
        for (var i=0; i<data.length; i++) {
            d = data[i];

            // loop through trend limits
            for (var j=0; j<trendlimits.length; j++) {
                // when we find the right bucket, add point to bucket and break out
                // note bottom of range is greater or equal and top of range is strictly less than
                if (d.meters >= trendlimits[j].range[0] && d.meters < trendlimits[j].range[1]) {
                    trendbucket[trendlimits[j].name].push(d);
                    break
                }
            }
        }
    }

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
        var heading = "no results found for current selection";
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
            .attr("data-legend", legend_text)
            .attr("data-legend-pos", function(d) { return d.miles; })
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
                     .style("opacity", 1);
                tooltip.html(d.race + "<br/>" + formatDate(d.date) + " " + d.time + " " + round(yValue(d),1) + "%")
                     .style("left", (d3.event.pageX + 10) + "px")
                     .style("top", (d3.event.pageY - 50) + "px");
            })  // .on("mouseover"
            .on("mouseout", function(d) {
                tooltip.transition()
                     .duration(500)
                     .style("opacity", 0);
            })  // .on("mouseout"
          .transition(t)
            .style("fill-opacity", 1)
            .on("end", function(d,i) {legend.call(d3.legend)})

        // draw trend lines
        trendlines = d3.selectAll(".dt-chart-trendline").remove();
        clearTrendBuckets();
        addResultsToTrendBuckets(data);
        trendrows = d3.selectAll(".dt-chart-trendrow").remove();
        trendtableopacity = 0;
        trendtable.style("opacity", trendtableopacity);

        var thisdata;
        if (data.length > 0) {
            stats = drawTrendLine(svg, "dt-chart-trendline", data, "black", "overall");
            trendtableopacity = 1;
            trendtable.style("opacity", trendtableopacity);
            var thisrow = trendtable
                .append("tr")
                .attr("class", "dt-chart-trendrow");
            thisrow.append("td").attr("class","dt-chart-trendstat").text("overall");
            thisrow.append("td").attr("class","dt-chart-trenddata").append("hr").style("background-color", "black");
            thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.n);
            thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.mean.toFixed(1)+"%");
            thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.min.toFixed(1)+"%");
            thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.max.toFixed(1)+"%");
            if (stats.n > 1) {
                thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.improvement.toFixed(1)+"%/yr");
            } else {
                thisrow.append("td").attr("class","dt-chart-trenddata").text("");
            }
            for (var i=0; i<trendlimits.length; i++) {
                thisdata = trendbucket[trendlimits[i].name];
                if (thisdata.length > 0) {
                    stats = drawTrendLine(svg, "dt-chart-trendline", thisdata, trendlimits[i].color, trendlimits[i].name);
                    thisrow = trendtable.append("tr")
                        .attr("class", "dt-chart-trendrow");
                    thisrow.append("td").attr("class","dt-chart-trendstat").text(trendlimits[i].name);
                    thisrow.append("td").attr("class","dt-chart-trenddata").append("hr").style("background-color", trendlimits[i].color);
                    thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.n);
                    thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.mean.toFixed(1)+"%");
                    thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.min.toFixed(1)+"%");
                    thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.max.toFixed(1)+"%");
                    if (stats.n > 1) {
                        thisrow.append("td").attr("class","dt-chart-trenddata").text(stats.improvement.toFixed(1)+"%/yr");
                    } else {
                        thisrow.append("td").attr("class","dt-chart-trenddata").text("");
                    }
                }
            }
        }

        // update legend after updating dots
        // remove and replace legend for case where empty
        viewbox.selectAll(".legend").remove()
        var legend = viewbox.append("g")
              .attr("class","legend")
              .attr("transform","translate(" + (width + margin.left + 25) + "," + margin.top + ")")
              .style("font-size","12px");

    }   // dt_chart_update

    // when any ajax request is sent to the server, show progress is happening
    _dt_table.on( 'preXhr.dt', function ( e, settings, data ) {
        console.log('preXhr Date.now()='+Date.now())
        progressbar.progressbar({value:false, disabled:false})
        inprogress += 1;
        if (inprogress == 1) {
            d3.selectAll("#progressbar").append("div").attr("class","progress-label").text("Loading");
        }
        progressbarcreated = true;
    });

    // when any ajax request is received back from the server, update the chart
    _dt_table.on( 'xhr.dt', function ( e, settings, json, xhr ) {
        // done processing
        console.log('xhr Date.now()='+Date.now())
        if (inprogress > 0) { inprogress -= 1; }
        if (progressbarcreated && inprogress == 0) {
            progressbar.progressbar("destroy");
            d3.selectAll(".progress-label").remove();
            progressbarcreated = false;
        }

        // add tableselect keys if no xhr error
        if (!json) throw "error response from api";               

        var data = json.data;

        // data is list of result objects
        // convert agpercent and miles (distance) to number
        var alldata = [];
        var timesplit;
        for (var i = 0; i < data.length; i++) {
            // do deep copy of data[i]. Shallow would probably be ok, but why not do deep?
            d = jQuery.extend(true, {}, data[i]);
            d.date = parseDate(d.date);
            // remove % if present, and convert to number
            d.agpercent = +d.agpercent.replace(/\%/g,"");
            d.miles = +d.miles;
            d.meters = d.miles * meterspermile;
            d.timesecs = 0;
            timesplit = d.time.split(':');
            for (var j=0; j<timesplit.length; j++) {
                d.timesecs += d.timesecs*60 + (+timesplit[j]);
            }
            alldata.push(d);
        };  // for

        // deduplicate data
        dedupdata = deduplicate(alldata);

        // initial draw or transition to new data
        // see http://bl.ocks.org/d3noob/7030f35b72de721622b8
        dt_chart_update(dedupdata);

    });     // _dt_table.on( 'xhr.dt'

}

