# Created by Philip Guo on 2013-12-07

# Adapted from code in the Py2crazy project:
#   https://github.com/pgbovine/Py2crazy/blob/master/Python-2.7.5/Lib/ast_extents.py
# originally created by Philip Guo on 2013-07-10

# Operates on the built-in AST from 'import ast', using the lineno and
# col_offset fields in AST nodes. tested on Python 2.7

# FAIL FAST with NotImplementedError so that failures aren't masked


# broken tests:
# build-tuple.txt
# str = '%d %s %s' % (self.x, self.y, self.z)
#
# decorator_test.txt
#
# function definitions
#
'''
# broken tests
"""John's cat liked "The Matrix"
but his dog
preferred the sequels."""

weird extra trailing spaces are bad too, e.g.,:

print x  ,
'''

# TODO: implement a paren_adjustment function that adjusts for parens
# that are commonly used around, say, BinOp, BoolOp, or CompareOp
#
# not (x or y)
# (x + 5) * (y + z)
# (one * (two + 3))

import ast
import sys

# Limitations
# - doesn't support extents that span MULTIPLE LINES
# - BinOps involving ** and field attribute accesses interact funny
#   e.g., "self.val = self.val ** 2"
#
# see tests/known-broken-tests/ for other weirdness

'''
TODO: manually 'parse' the source code using heuristics to account for
trailing spaces, and other detailed patches
    e.g., '(x, y)' tuple vs 'x, y' naked tuple
'''


# NOPs
NOP_CLASSES = [ast.expr_context, ast.cmpop, ast.boolop,
               ast.unaryop, ast.operator,
               ast.Module, ast.Interactive, ast.Expression,
               ast.arguments, ast.alias,
               ast.excepthandler,
               ast.Set, # TODO: maybe keep extents for this, along with Dict, Tuple, and List
               ast.With, ast.GeneratorExp,
               ast.comprehension,
               ast.ListComp, ast.DictComp, ast.SetComp,
               ast.IfExp,
               ast.Ellipsis, # a rarely-occuring bad egg; it doesn't have col_offset, ugh

               # TODO: is this still a legit comment?
               ast.Expr, # ALWAYS ignore this or else you get into bad conflicts
               ]


def copy_end_attrs(from_node, to_node):
    to_node.end_col = from_node.end_col
    to_node.end_lineno = from_node.end_lineno


# This visitor runs top-down, so we might need to run several times to fixpoint
class AddExtentsVisitor(ast.NodeVisitor):
    def __init__(self, code_str):
        ast.NodeVisitor.__init__(self)
        # add sentinel to support one-indexing
        self.code_lines = [''] + code_str.split('\n')

    def add_attrs(self, node):
        if 'start_col' not in node._attributes:
            node._attributes = node._attributes + ('start_col', 'end_col', 'end_lineno')

    # this should NEVER be called, since all cases should be exhaustively handled
    def generic_visit(self, node):
        # exception: let these pass through unscathed, since we NOP on them
        for c in NOP_CLASSES:
            if isinstance(node, c):
                # recurse normally into children (if any)
                self.visit_children(node)
                return

        raise NotImplementedError, node.__class__

    # copied from Lib/ast.py generic_visit
    def visit_children(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    # always end with a call to self.visit_children(node) to recurse
    # (unless you know you're a terminal node)
    # TODO: encapsulate in a decorator

    def visit_Subscript(self, node):
      raise NotImplementedError
      if hasattr(node.value, 'extent') and hasattr(node.slice, 'extent'):
        self.add_attrs(node)
        node.start_col = node.value.start_col
        # add 1 for trailing ']'
        # of course, that doesn't work so well when you put spaces before
        # like '  ]', but it's okay for the common case.
        node.extent = node.slice.start_col + node.slice.extent + 1 - node.start_col
      self.visit_children(node)

    def visit_Index(self, node):
      raise NotImplementedError
      if hasattr(node.value, 'extent'):
        self.add_attrs(node)
        node.start_col = node.value.start_col
        node.extent = node.value.extent
      self.visit_children(node)

    def visit_Slice(self, node):
      raise NotImplementedError
      leftmost = node.lower
      right_padding = 0
      if node.step:
        rightmost = node.step  # A[i:j:k]
      elif node.upper:
        rightmost = node.upper # A[i:j]
      else:
        rightmost = node.lower # A[i:]
        right_padding = 1 # for trailing ':'

      if hasattr(leftmost, 'extent') and hasattr(rightmost, 'extent'):
        # TODO: to be really paranoid, check that they're on the same line
        self.add_attrs(node)
        node.start_col = leftmost.start_col
        node.extent = rightmost.start_col + rightmost.extent + right_padding - node.start_col

        # trickllllly! also add lineno and col_offset to Slice object,
        # since the AST doesn't keep this info for this class, sad :(
        node._attributes += ('lineno', 'col_offset')
        node.lineno = leftmost.lineno
        node.col_offset = leftmost.col_offset

      self.visit_children(node)

    def visit_ExtSlice(self, node):
      raise NotImplementedError
      # TODO: handle me in a similar way as visit_Slice if necessary
      self.visit_children(node)

    def visit_Attribute(self, node):
        raise NotImplementedError
        if hasattr(node.value, 'extent'):
            self.add_attrs(node)
            node.start_col = node.col_offset
            node.extent = node.value.extent + 1 + len(node.attr)
        self.visit_children(node)

    def visit_Repr(self, node):
      raise NotImplementedError
      if hasattr(node.value, 'extent'):
        self.add_attrs(node)
        node.start_col = node.col_offset
        node.extent = node.value.extent + 2 # add 2 for surrounding backquotes
      self.visit_children(node)

    def visit_Dict(self, node):
      raise NotImplementedError
      # empty case
      if len(node.values) == 0:
        node.start_col = node.col_offset
        node.extent = 2 # for '{}' case
      else:
        last_val = node.values[-1] # this is the best approximation I can come up with
        if hasattr(last_val, 'extent') and \
           hasattr(last_val, 'lineno') and \
           (node.lineno == last_val.lineno):
          self.add_attrs(node)
          node.start_col = node.col_offset
          node.extent = last_val.start_col + last_val.extent + 1 - node.start_col
      self.visit_children(node)


    # TODO: abstract out this recurring pattern ...
    def visit_FunctionDef(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('def')
      self.visit_children(node)

    def visit_ClassDef(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('class')
      self.visit_children(node)

    def visit_Raise(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('raise')
      self.visit_children(node)

    def visit_Assert(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('assert')
      self.visit_children(node)

    def visit_TryExcept(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('try')
      self.visit_children(node)

    def visit_TryFinally(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('try')
      self.visit_children(node)

    def visit_ExceptHandler(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('except')
      self.visit_children(node)

    def visit_Global(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('global')
      self.visit_children(node)

    def visit_Lambda(self, node):
      raise NotImplementedError
      if hasattr(node.body, 'extent'):
        self.add_attrs(node)
        node.start_col = node.col_offset
        node.extent = node.body.start_col + node.body.extent - node.start_col
      self.visit_children(node)

    def visit_Exec(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('exec')
      self.visit_children(node)

    def visit_Delete(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('del')
      self.visit_children(node)

    def visit_Return(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('return')
      self.visit_children(node)

    def visit_Import(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('import')
      self.visit_children(node)

    def visit_ImportFrom(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('from')
      self.visit_children(node)

    def visit_Yield(self, node):
      raise NotImplementedError
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.extent = len('yield')
      self.visit_children(node)


    ### stuff below is implemented ...

    def visit_Call(self, node):
        # empty case is a function call with NO arguments, keyword args,
        # starargs, or kwargs
        has_regular_args = node.args
        has_keyword_args = node.keywords
        has_starargs = node.starargs
        has_kwargs = node.kwargs

        # empty function call with NO args of any kind!
        if (not has_regular_args and
            not has_keyword_args and
            not has_starargs and
            not has_kwargs):
            if hasattr(node.func, 'start_col'):
                node.start_col = node.col_offset
                # for trailing '()'; doesn't handle blank spaces
                node.end_col = node.func.end_col + 2
                node.end_lineno = node.func.end_lineno
        # we want to give priority to kwargs since that's ALWAYS at the end ...
        elif has_kwargs:
            if hasattr(node.kwargs, 'start_col'):
                node.start_col = node.col_offset
                # for trailing ')'; doesn't handle blank spaces before ')'
                node.end_col = node.kwargs.end_col + 1
                node.end_lineno = node.kwargs.end_lineno
        # then second priority to starargs ...
        elif has_starargs:
            if hasattr(node.starargs, 'start_col'):
                node.start_col = node.col_offset
                # for trailing ')'; doesn't handle blank spaces before ')'
                node.end_col = node.starargs.end_col + 1
                node.end_lineno = node.starargs.end_lineno
        # then keyword args ...
        elif has_keyword_args:
            last_arg = node.keywords[-1]
            if hasattr(last_arg, 'start_col'):
                node.start_col = node.col_offset
                # for trailing ')'; doesn't handle blank spaces before ')'
                node.end_col = last_arg.end_col + 1
                node.end_lineno = last_arg.end_lineno
        # and finally the case with regular vanilla arguments like f(1, 2, 3)
        else:
            assert has_regular_args
            last_arg = node.args[-1]
            if hasattr(last_arg, 'start_col'):
                node.start_col = node.col_offset
                # for trailing ')'; doesn't handle blank spaces before ')'
                node.end_col = last_arg.end_col + 1
                node.end_lineno = last_arg.end_lineno

        self.visit_children(node)
        '''
      # find the RIGHTMOST argument and use that one for extent
      # (could be either in args, keywords, starargs, or kwargs)
      max_col_offset = -1
      max_elt = None

      # the 'value' field in each element of node.keywords is most relevant
      candidates = node.args + [e.value for e in node.keywords]
      if node.starargs:
        candidates.append(node.starargs)
      if node.kwargs:
        candidates.append(node.kwargs)

      for e in candidates:
        if e.col_offset > max_col_offset and e.lineno == node.lineno:
          max_col_offset = e.col_offset
          max_elt = e

      if max_elt and hasattr(max_elt, 'extent') and hasattr(node.func, 'extent'):
        self.add_attrs(node)
        node.start_col = node.func.start_col
        node.extent = max_elt.start_col + max_elt.extent + 1 - node.start_col
      elif hasattr(node.func, 'extent'):
        # punt and just use the function's info
        self.add_attrs(node)
        node.start_col = node.func.start_col
        node.extent = node.func.extent + 2 # 2 extra for '()'

      self.visit_children(node)
      '''

    def visit_List(self, node):
        # empty case
        if len(node.elts) == 0:
            node.start_col = node.col_offset
            node.end_col = node.start_col + 2 # for '[]' case; doesn't handle blank spaces
            node.end_lineno = node.lineno
        else:
            last_elt = node.elts[-1]
            if hasattr(last_elt, 'start_col'):
                self.add_attrs(node)
                node.start_col = node.col_offset
                copy_end_attrs(last_elt, node)
                # TODO: if someone writes extra trailing spaces before the ']',
                # then end_col needs to be adjusted to the index of the
                # first found ']'. Example: [1,2,3    ]
                # (but let's not worry about this weird case for now)
                node.end_col += 1 # for the extra trailing ']' character
        self.visit_children(node)

    def visit_Tuple(self, node):
        # empty case
        if len(node.elts) == 0:
            node.start_col = node.col_offset
            node.end_col = node.start_col + 2 # for '()' case; doesn't handle blank spaces
            node.end_lineno = node.lineno
        else:
            last_elt = node.elts[-1]
            if hasattr(last_elt, 'start_col'):
                trailing_offset = 0
                # a singleton tuple is like '(x,)', so add 1 more for the trailing comma
                if len(node.elts) == 1:
                    trailing_offset = 1

                self.add_attrs(node)
                node.start_col = node.col_offset
                copy_end_attrs(last_elt, node)
                node.end_col += trailing_offset

                # adjust for parens
                if node.start_col > 0:
                    if self.code_lines[node.lineno][node.start_col - 1] == '(':
                        node.start_col -= 1
                        node.end_col += 1
        self.visit_children(node)

    def visit_If(self, node):
        if hasattr(node.test, 'start_col'):
            self.add_attrs(node)
            node.start_col = node.col_offset
            copy_end_attrs(node.test, node)

            # special case! 'elif' statements have start_col starting
            # not at the 'elif' but instead at the test condition, so
            # make an adjustment backward
            if node.start_col > 0:
                l = self.code_lines[node.lineno]
                if not l[node.start_col].startswith('if'):
                    if 'elif' in l[:node.start_col]:
                        node.start_col = l.index('elif')

        self.visit_children(node)


    # grab end_col and end_lineno from the rightmost attribute
    def standard_visitor(self, node, rightmost_attr_name):
        rightmost_attr = getattr(node, rightmost_attr_name)
        if hasattr(rightmost_attr, 'start_col'):
            self.add_attrs(node)
            node.start_col = node.col_offset
            copy_end_attrs(rightmost_attr, node)
        self.visit_children(node)

    def visit_keyword(self, node):
        # keyword nodes don't have a col_offset or lineno, so STEAL
        # those from child (warning: super hacky but should work!)
        node.lineno = node.value.lineno
        node.col_offset = node.value.col_offset
        node._attributes = node._attributes + ('lineno', 'col_offset')
        self.standard_visitor(node, 'value')

    def visit_For(self, node):
        self.standard_visitor(node, 'iter')
    def visit_While(self, node):
        self.standard_visitor(node, 'test')
    def visit_Assign(self, node):
        self.standard_visitor(node, 'value')
    def visit_AugAssign(self, node):
        self.standard_visitor(node, 'value')
    def visit_BinOp(self, node):
        self.standard_visitor(node, 'right')
    def visit_UnaryOp(self, node):
        self.standard_visitor(node, 'operand')

    def visit_BoolOp(self, node):
        if hasattr(node.values[-1], 'start_col'):
            self.add_attrs(node)
            node.start_col = node.col_offset
            copy_end_attrs(node.values[-1], node)
        self.visit_children(node)

    def visit_Compare(self, node):
        assert len(node.comparators) > 0
        rightmost = node.comparators[-1]
        if hasattr(rightmost, 'start_col'):
            self.add_attrs(node)
            node.start_col = node.col_offset
            copy_end_attrs(rightmost, node)
        self.visit_children(node)

    def visit_Print(self, node):
        if len(node.values):
            if hasattr(node.values[-1], 'start_col'):
                node.start_col = node.col_offset
                copy_end_attrs(node.values[-1], node)
                # adjustment for comma
                if not node.nl:
                    node.end_col += 1
        else:
            # naked print
            node.start_col = node.col_offset
            node.end_col = node.start_col + len('print')
            node.end_lineno = node.lineno
            # adjustment for comma
            if not node.nl:
                node.end_col += 1
        self.visit_children(node)

    # terminal nodes
    def visit_Name(self, node):
          self.add_attrs(node)
          node.start_col = node.col_offset
          node.end_col = node.start_col + len(node.id)
          node.end_lineno = node.lineno

    def visit_Str(self, node):
        if node.col_offset >= 0:
            self.add_attrs(node)
            node.start_col = node.col_offset
            # repr() will take escape characters and enclosing quotes into account!
            node.end_col = node.start_col + len(repr(node.s))
            node.end_lineno = node.lineno
        else:
            raise NotImplementedError
            # TODO: doesn't work for multi-line strings
            # (those seem to have col_offset as -1, so ignore them)

    def visit_Num(self, node):
        '''For starters, just handle basic DECIMAL numbers:
  3
  3.0
  3.14
  -3
  -3.14
  3.14159
  3.
  -3.
        '''
        self.add_attrs(node)
        node.start_col = node.col_offset
        node.end_col = node.start_col + len(str(node.n))
        node.end_lineno = node.lineno
        # adjustment for negative decimal numbers
        if node.col_offset > 0:
            char_before = self.code_lines[node.lineno][node.col_offset-1]
            if char_before == '-':
                node.start_col -= 1

    def visit_Pass(self, node):
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.end_col = node.start_col + len('pass')
      node.end_lineno = node.lineno

    def visit_Break(self, node):
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.end_col = node.start_col + len('break')
      node.end_lineno = node.lineno

    def visit_Continue(self, node):
      self.add_attrs(node)
      node.start_col = node.col_offset
      node.end_col = node.start_col + len('continue')
      node.end_lineno = node.lineno


# copied from ast.NodeVisitor
class DepthCountingVisitor(object):
    def __init__(self):
        self.max_depth = 0
    def visit(self, node, depth=1):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item, depth+1)
            elif isinstance(value, ast.AST):
                self.visit(value, depth+1)
        else:
            # terminal node
            if depth > self.max_depth:
                self.max_depth = depth


# adapted from ast.dump
def pretty_dump(node, code_str):
    # add sentinel to support one-indexing
    lines = [''] + code_str.split('\n')

    def _format(node, indent=0, newline=False):
        ind = ('  ' * indent)
        next_ind = ('  ' * (indent+1))

        if isinstance(node, ast.AST):
            if newline:
                print ind + node.__class__.__name__,
            else:
                print node.__class__.__name__,

            if hasattr(node, 'lineno'):
                if hasattr(node, 'start_col'):
                    # common case: single line
                    if node.lineno == node.end_lineno:
                        contents = lines[node.lineno][node.start_col:node.end_col]
                        print '>>', repr(contents)
                    # multiline
                    else:
                        assert node.end_lineno > node.lineno
                        contents = ''
                        for i in range(node.lineno, node.end_lineno+1):
                            l = lines[i]
                            if i == node.lineno:
                                contents += l[node.start_col:]
                            elif i == node.end_lineno:
                                contents += l[:node.end_col]
                            else:
                                contents += l
                            contents += '\n'
                        # strip off final \n
                        if contents[-1] == '\n':
                            contents = contents[:-1]
                        print 'ML>>', repr(contents)
                else:
                    print
            else:
                print

            for (fieldname, f) in ast.iter_fields(node):
                print next_ind + fieldname + ':',
                _format(f, indent+1)

        elif isinstance(node, list):
            print '['
            for e in node:
                _format(e, indent+1, True)
            print ind + ']'
        else:
            print repr(node)

    if not isinstance(node, ast.AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)

    return _format(node, 0)


if __name__ == "__main__":
    code_str = open(sys.argv[1]).read()

    m = ast.parse(code_str)

    dcv = DepthCountingVisitor()
    dcv.visit(m)
    max_depth = dcv.max_depth

    # To be conservative, run the visitor max_depth number of times, which
    # should be enough to percolate ALL (start_col, extent) values up from
    # the leaves to the root of the tree
    v = AddExtentsVisitor(code_str)
    for i in range(max_depth):
        v.visit(m)

    print code_str,
    print '==='
    pretty_dump(m, code_str)
