# malkovich malkovich malkovich malkovich malkovich malkovich
# malkovich malkovich malkovich malkovich malkovich malkovich
# malkovich malkovich malkovich malkovich malkovich malkovich
# malkovich malkovich malkovich malkovich malkovich malkovich
# malkovich malkovich malkovich malkovich malkovich malkovich
# malkovich malkovich malkovich malkovich malkovich malkovich

import ast
import ast_extents
from identifier_renamer import *
import sys


class FindAllIdentifiersVisitor(ast.NodeVisitor):
    def __init__(self):
        self.identifiers = []

    def visit_Name(self, node):
        #print 'Name:', node.id, node.lineno, node.start_col
        self.identifiers.append(node.id)


def malkovich_renamer(src_code):
    obj = ast_extents.CodeAst(src_code)

    v = FindAllIdentifiersVisitor()
    v.visit(obj.ast_root)

    renamed_code = src_code
    for i in v.identifiers:
        renamed_code = rename_identifier(renamed_code, i, 'malkovich')

    return renamed_code

if __name__ == "__main__":
    src_code = open(sys.argv[1], 'U').read()
    print malkovich_renamer(src_code)

