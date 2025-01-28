// d3.legend.js 
// (C) 2012 ziggy.jonsson.nyc@gmail.com
// MIT licence
// from http://bl.ocks.org/ZJONSSON/3918369

(function() {
d3.legend = function(g) {
  g.each(function() {
    var g= d3.select(this),
        items = {},
        svg = d3.select(g.property("nearestViewportElement")),
        legendPadding = g.attr("data-style-padding") || 5;

    svg.selectAll("[data-legend]").each(function() {
        var self = d3.select(this)
        items[self.attr("data-legend")] = {
          pos : self.attr("data-legend-pos") || this.getBBox().y,
          color : self.attr("data-legend-color") != undefined ? self.attr("data-legend-color") : self.style("fill") != 'none' ? self.style("fill") : self.style("stroke"),
          icon : self.attr("data-legend-icon") != undefined ? self.attr("data-legend-icon") : "circle",
        }
      });

    items = Object.entries(items).sort((a,b) => a[1].pos-b[1].pos);

    // first create legend box if it doesn't exist
    var lbcreate = g.selectAll(".legend-box")
        .data(["g"])
      .enter().append("rect")
        .attr("class", "legend-box");
    lb = g.selectAll(".legend-box")

    // create g for legend-items if it doesn't exist
    var licreate = g.selectAll(".legend-items")
        .data(["g"])
      .enter()
        .append("g")
        .attr("class", "legend-items");
    var li = g.selectAll(".legend-items");

    var textli = li.selectAll("text")
        .data(items, d => d[0])

    textli.exit()
        .remove();
    
    textli
        .attr("y", (d,i) => i+"em")
        .attr("x","1em")
        .text( d => d[0]);

    textli.enter()
        .append("text")
        // .call(function(d) { d.enter().append("text")})
        // .call(function(d) { d.exit().remove()})
        .attr("y", (d,i) => i+"em")
        .attr("x","1em")
        .text(d => d[0]);

    var circleli = li.selectAll("circle")
        .data(items, d => d[0])

    circleli.exit()
        .remove();
    
    circleli
        .attr("cy", (d,i) => i-0.25+"em")
        .attr("cx",0)
        .attr("r","0.4em")
        .style("fill", d => d[1].color);
    
    circleli.enter()
        // .call(function(d) { d.enter().append("circle")})
        // .call(function(d) { d.exit().remove()})
        .append("circle")
        .attr("cy", (d,i) => i-0.25+"em")
        .attr("cx",0)
        .attr("r","0.4em")
        .style("fill", d => d[1].color );
    
    // Reposition and resize the box
    var lbbox = li.node().getBBox();

    lb.attr("x",(lbbox.x-legendPadding))
        .attr("y",(lbbox.y-legendPadding))
        .attr("height",(lbbox.height+2*legendPadding))
        .attr("width",(lbbox.width+2*legendPadding));
  });
  return g;
}
})()