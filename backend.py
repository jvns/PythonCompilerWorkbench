# Created by Philip Guo on 2013-12-03, with help from Kyle Murray

# to invoke, run 'python backend.py'
# and visit http://localhost:8080/index.html
#
# external dependencies: bottle, pydot, GraphViz executable
#
# easy_install pip
# pip install bottle
# pip install pydot

import ast
import byteplay
import json

from bottle import route, get, request, run, template, static_file
from pg_astmonkey import PGGraphvizCreator
from ast_extents import CodeAst


@route('/<filepath:path>')
def index(filepath):
    return static_file(filepath, root='.')

@get('/compile')
def get_compile():
    source_code = request.query.program

    # empty
    if not source_code.strip():
        return json.dumps({'status': 'success',
                           'ast_svg': '',
                           'bytecode_str': ''})

    try:
        obj = CodeAst(source_code)
        node = obj.get_ast()

        g = PGGraphvizCreator(node)
        ast_svg = g.graph.create_svg()

        codeobject = compile(node, '<string>', 'exec')
        c = byteplay.Code.from_code(codeobject)
        bytecode_str = str(c.code)

        return json.dumps({'status': 'success',
                           'ast_svg': ast_svg,
                           'bytecode_str': bytecode_str})
    except SyntaxError:
        return json.dumps({'status': 'error', 'data': 'SyntaxError'})


if __name__ == "__main__":
    run(host='localhost', port=8080, reloader=True)
