import sys
from ast_extents import CodeAst

if __name__ == "__main__":
    code_str = open(sys.argv[1]).read()

    obj = CodeAst(code_str)

    print obj.to_renderable_json(compact=False, debug=False)
