import sys
from ast_extents import CodeAst

if __name__ == "__main__":
    code_str = open(sys.argv[1]).read()

    obj = CodeAst(code_str)

    obj.to_renderable_json()
