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
  $("#codePuffJSON").html(astJson);

  var ast = $.parseJSON(astJson);

  $("#codePuffPane").empty();

  // pair programming with Tom Lieber
  function renderNodes(ul, nodes) {
    // select all li's inside of THIS ul
    var lis = ul.selectAll(function () { return ul[0][0].childNodes })
                .data(nodes);

    lis.enter()
       .append("span")
       .each(makeNodeView);
  }

  function makeNodeView(node) {
    if (typeof node == "string") {
      // escape all weird characters
      var s = htmlspecialchars(node);
      d3.select(this).html(s);
    }
    else {
      // object
      var ul = d3.select(this).append("span");
      ul.attr("id", node.id);
      ul.attr("class", node.name);
      renderNodes(ul, node.contents);
    }
  }

  var ul = d3.select("#codePuffPane").insert("span");
  renderNodes(ul, [ast]);
}
