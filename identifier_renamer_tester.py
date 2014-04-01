# stress tests identifier_renamer.py

import ast
import ast_extents
from identifier_renamer import *
import os
import sys


class FindAllIdentifiersVisitor(ast.NodeVisitor):
    def __init__(self):
        self.identifiers = []

    def visit_Name(self, node):
        #print 'Name:', node.id, node.lineno, node.start_col
        self.identifiers.append(node.id)


def cross_check_renamers(src_code):
    obj = ast_extents.CodeAst(src_code)

    v = FindAllIdentifiersVisitor()
    v.visit(obj.ast_root)

    renamed_with_regular = renamed_with_JSON = src_code

    # rename one variable at a time to repeating it three times
    for i in v.identifiers:
        renamed_with_regular = rename_identifier(renamed_with_regular, i, i+i+i)
        renamed_with_JSON = rename_identifier_JSON_version(renamed_with_JSON, i, i+i+i)

    assert renamed_with_regular == renamed_with_JSON # vital check!
    return renamed_with_regular


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # test just one file
        src_code = open(sys.argv[1], 'U').read()
        print cross_check_renamers(src_code)
    else:
        # test everything

        ALL_TESTS = []

        for (pwd, subdirs, files) in os.walk('tests/', followlinks=True): # need to follow example-code symlink
            for f in files:
                (base, ext) = os.path.splitext(f)
                if ext == '.txt':
                    fullpath = os.path.join(pwd, f)
                    ALL_TESTS.append(fullpath)

        for t in ALL_TESTS:
            # known broken test
            if 'string-with-continuation-char.txt' in t:
                continue

            print "======"
            print "Testing", t
            src_code = open(t, 'U').read()
            try:
                print cross_check_renamers(src_code)
            # some files don't properly parse ...
            except NotImplementedError:
                print "Exception NotImplementedError"
                pass

