// linear regression for trendline
// see http://stackoverflow.com/questions/20507536/d3-js-linear-regression
// see http://trentrichardson.com/2010/04/06/compute-linear-regressions-in-javascript/
function linearRegression(y,x){

    var lr = {};
    var n = y.length;
    var sum_x = 0;
    var sum_y = 0;
    var sum_xy = 0;
    var sum_xx = 0;
    var sum_yy = 0;

    for (var i = 0; i < y.length; i++) {

        sum_x += x[i];
        sum_y += y[i];
        sum_xy += (x[i]*y[i]);
        sum_xx += (x[i]*x[i]);
        sum_yy += (y[i]*y[i]);
    } 

    lr['slope'] = (n * sum_xy - sum_x * sum_y) / (n*sum_xx - sum_x * sum_x);
    lr['intercept'] = (sum_y - lr.slope * sum_x)/n;
    lr['r2'] = Math.pow((n*sum_xy - sum_x*sum_y)/Math.sqrt((n*sum_xx-sum_x*sum_x)*(n*sum_yy-sum_y*sum_y)),2);
    lr['fn'] = function (x) { return this.slope * x + this.intercept; };

    return lr;

};

// escape html in a string
function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// methods to .call to allow element to be dragged by mouse
// see http://bl.ocks.org/enjalot/1378144
// to drag div element
var dragdiv = d3.drag()
    .on("drag", function(event, d,i) {
        d.x += event.dx
        d.y += event.dy
        d3.select(this)
            .style("left", d.x+'px')
            .style("top", d.y+'px');
    });

// to drag svg element
var drag = d3.drag()
    .on("drag", function(d,i) {
        d.x += d3.event.dx
        d.y += d3.event.dy
        d3.select(this).attr("transform", function(d,i){
            return "translate(" + [ d.x,d.y ] + ")"
        })
    });

// set up chart and table handling
// table should be initially hidden with dom = '<"dt-chart-table dt-chart-tabledisplay dt-hide"t>'

// table / chart button
$(function () {
    $( ".dt-chart-display-button" ).click( function( event ) {
        // if currently displaying chart
        if ($(this).text() == "table") {
            $(".dt-chart-chartdisplay").toggleClass("dt-hide",true);
            $(".dt-chart-tabledisplay").toggleClass("dt-hide",false);
            $(this).text("chart")


        // if currently displaying table
        } else {
            $(".dt-chart-chartdisplay").toggleClass("dt-hide",false);
            $(".dt-chart-tabledisplay").toggleClass("dt-hide",true);
            $(this).text("table")
        }
    } );
});