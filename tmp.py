import ast

from pg_astmonkey import PGGraphvizCreator

class PGPrintVisitor(ast.NodeVisitor):
    def __init__(self):
        pass

    def visit(self, node):
        print id(node), node.__class__.__name__,
        if hasattr(node, 'parent_field_index'):
            print node.parent_field_index
        else:
            print

        super(PGPrintVisitor, self).visit(node)


if __name__ == "__main__":
    node = ast.parse('w = x < y < z')
    g = PGGraphvizCreator(node)
    g.graph.write_svg('test.svg')

