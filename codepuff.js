// taken from http://www.toao.net/32-my-htmlspecialchars-function-for-javascript
function htmlspecialchars(str) {
  if (typeof(str) == "string") {
    str = str.replace(/&/g, "&amp;"); /* must do &amp; first */

    // ignore these for now ...
    //str = str.replace(/"/g, "&quot;");
    //str = str.replace(/'/g, "&#039;");

    str = str.replace(/</g, "&lt;");
    str = str.replace(/>/g, "&gt;");

    // replace spaces:
    str = str.replace(/ /g, "&nbsp;");

    // replace tab as four spaces:
    str = str.replace(/\t/g, "&nbsp;&nbsp;&nbsp;&nbsp;");

    // replace newlines
    str = str.replace(new RegExp('\n', 'g'), '<br/>');
  }
  return str;
}


// remember, d3 thinks of everything as lists
function renderCodePuff(astJson) {
  var ast = $.parseJSON(astJson);

  $("#codePuffPane").empty();

  // from pair programming with Tom Lieber
  function renderNodes(cur, nodes) {
    // old code: grab all of the (not-yet-existent) child nodes of this node
    //var lis = cur.selectAll(function () { return cur[0][0].childNodes })
    //             .data(nodes);

    var lis = cur.selectAll("div")
                 .data(nodes);

    lis.enter()
       .append("div")
       .each(makeNodeView);
  }

  function makeNodeView(node) {
    var disNode = d3.select(this);

    if (typeof node == "string") {
      // a terminal node
      disNode.attr("class", "string");

      // escape all weird characters
      var s = htmlspecialchars(node);
      disNode.html(s);
    }
    else {
      // a compound object
      disNode.attr("id", node.id);
      disNode.attr("class", node.name);

      // ... so recurse into either value or contents
      if (node.value !== undefined) {
        renderNodes(disNode, [node.value]); // need a singleton list
      }
      else {
        renderNodes(disNode, node.contents);
      }
    }
  }

  var base = d3.select("#codePuffPane");
  renderNodes(base, [ast] /* d3 expects a list, eeek! */);
}
