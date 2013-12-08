# forked from the astmonkey project on 2013-12-05
# https://pypi.python.org/pypi/astmonkey
import ast
import pydot

# copied and customized from astmonkey
class PGGraphNodeVisitor(ast.NodeVisitor):
    def __init__(self, graph):
        self.graph = graph

    def visit(self, node):
        # only add a GraphViz node if this node has some fields;
        # otherwise it should have already been inlined into its
        # parent node
        if node._fields:
            self.graph.add_node(self._dot_node(node))
        super(PGGraphNodeVisitor, self).visit(node)

    def _dot_node(self, node):
        return pydot.Node(str(node),
                          label=self._dot_node_label(node),
                          **self._dot_node_kwargs(node))

    def _dot_node_label(self, node):
        if isinstance(node, str):
            return node

        fields_labels = []
        for field, value in ast.iter_fields(node):
            # not a list attribute, so possibly inline attrs ...
            if not isinstance(value, list):
                value_label = None
                if not isinstance(value, ast.AST):
                    value_label = repr(value)
                # if value has no fields of its own, then just inline
                # its label into this node
                elif not (hasattr(value, '_fields') and value._fields):
                    value_label = self._dot_node_label(value)

                if value_label:
                    fields_labels.append('{0}={1}'.format(field, value_label))
            # if it's a list, then inline barren children (i.e., those
            # with no children of their own)
            else:
                value_label_lst = []
                for i, e in enumerate(value):
                    if not (hasattr(e, '_fields') and e._fields):
                        value_label_lst.append('{0}={1}'.format(i, self._dot_node_label(e)))
                if value_label_lst:
                    lst_label = field + '[' + ',\n'.join(value_label_lst) + ']'
                    fields_labels.append(lst_label)

        if fields_labels:
          lab = '{0}\n({1})'.format(node.__class__.__name__, ',\n'.join(fields_labels))
        else:
          lab = '{0}'.format(node.__class__.__name__)

        if hasattr(node, 'lineno'):
            lab += '\n{0}:{1}'.format(node.lineno, node.col_offset)

        return lab

    def _dot_node_kwargs(self, node):
        return {
            'shape': 'box',
            'fontname': 'times',
            'fontsize': 9.0,
        }


class PGGraphEdgeVisitor(ast.NodeVisitor):
    def __init__(self, graph):
        self.graph = graph

    def visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for i, e in enumerate(value):
                    if hasattr(e, '_fields') and e._fields: # don't add edges to barren children
                        my_edge = pydot.Edge(str(node), str(e),
                                             label='{0}[{1}]'.format(field, i),
                                             **self._dot_edge_kwargs(node))
                        self.graph.add_edge(my_edge)
            elif isinstance(value, ast.AST):
                if value._fields: # don't add edges to barren children
                    my_edge = pydot.Edge(str(node), str(value),
                                         label=field,
                                         **self._dot_edge_kwargs(node))
                    self.graph.add_edge(my_edge)

        super(PGGraphEdgeVisitor, self).visit(node)

    def _dot_edge_kwargs(self, node):
        return {
            'fontname': 'times',
            'fontsize': 9.0,
            'arrowsize': 0.4,
        }


class PGGraphvizCreator(object):
    def __init__(self, ast_node):
        self.graph = pydot.Dot(graph_type='digraph')
        # lay out the graph horizontally and make it more compact, so
        # that it saves screen real estate
        self.graph.set_rankdir('LR')
        self.graph.set_ranksep('0.1')

        PGGraphNodeVisitor(self.graph).visit(ast_node)
        PGGraphEdgeVisitor(self.graph).visit(ast_node)

