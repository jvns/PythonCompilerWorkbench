// Created by Philip Guo on 2013-12-03, with help from Kyle Murray

var pyInputCodeMirror; // CodeMirror object that contains the input Python code
var pyTransformedCodeMirror; // contains the transformed Python code

var priorTimerId = null;
var redAlertSoundTimerId = null;

// turn this to true for a real kick :)
//var CRAZY_COMPILER_ERRORS = true;
var CRAZY_COMPILER_ERRORS = false;

// Code Mirror custom options
var cmOptions = {
  mode: 'python',
  lineNumbers: true,
  tabSize: 4,
  indentUnit: 4,
  // convert tab into four spaces:
  extraKeys: {Tab: function(cm) {cm.replaceSelection("    ", "end");}},
}


$(document).ready(function() {
  pyInputCodeMirror = CodeMirror(document.getElementById('codeInputPane'),
                                 cmOptions);
  pyInputCodeMirror.setSize(null, '200px'); // height

  /*
  pyTransformedCodeMirror = CodeMirror(document.getElementById('transformedCodePane'),
                                       cmOptions);
  pyTransformedCodeMirror.setSize(null, '200px'); // height
  */

  // only load the sounds if CRAZY_COMPILER_ERRORS is on, to save bandwidth
  if (CRAZY_COMPILER_ERRORS) {
    $("#sounds").html('<audio id="consoleExplosionSound" controls>\
      <source src="sounds/console_explo_03.mp3" type="audio/mpeg"/>\
      </audio>\
      <audio id="rikerRedAlertSound" controls>\
      <source src="sounds/redalert.mp3" type="audio/mpeg"/>\
      </audio>\
      <audio id="redAlertSirenSound" controls>\
      <source src="sounds/tng_red_alert2.mp3" type="audio/mpeg"/>\
      </audio>');
  }


  pyInputCodeMirror.on('change', function(editor, e) {
    // clear the prior timer to prevent multiple firings
    if (priorTimerId) {
      clearTimeout(priorTimerId);
    }

    priorTimerId = setTimeout(function() {
      // send to server:
      $.getJSON('compile',
            {program : pyInputCodeMirror.getValue(),
            },
            function(dat) {
              if (dat.status == 'success') {
                $('#codeInputPane').removeClass('redBorder');

                if (CRAZY_COMPILER_ERRORS) {
                  $('body').removeClass('redBlinkingBackground');
                  clearTimeout(redAlertSoundTimerId);
                  $('#redAlertSirenSound').get(0).pause();
                }

                $('#astPane').html(dat.ast_svg);
                $('#bytecodeOutput').html(dat.bytecode_str);
                $("#codePuffJSON").html(dat.ast_json);

                renderCodePuff(dat.ast_json);
              }
              else {
                $('#codeInputPane').addClass('redBorder');

                if (CRAZY_COMPILER_ERRORS) {
                  $('body').addClass('redBlinkingBackground');
                  $('body').effect('shake');
                  $('#consoleExplosionSound').get(0).play();
                  setTimeout(function() {$('#rikerRedAlertSound').get(0).play();}, 1000);
                  function playRedAlertSound() {
                    $('#redAlertSirenSound').get(0).play();
                    redAlertSoundTimerId = setTimeout(playRedAlertSound, 3000);
                  }
                  setTimeout(playRedAlertSound, 3000);
                }
              }
            });
    }, 300);
  });

  pyInputCodeMirror.focus();
});
