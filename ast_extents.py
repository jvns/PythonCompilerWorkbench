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
# - decorators
# - list/dict/set comprehensions
# - generator comprehensions
# - context managers
# - advanced exceptions
'''
weird extra trailing spaces are bad too, e.g.,:

print x  ,
'''

# TODO: implement a paren_adjustment function that adjusts for parens
# that are commonly used around, say, BinOp, BoolOp, or CompareOp
#
# not (x or y)
# (x + 5) * (y + z)
# (one * (two + 3))
# x = (tokens[5] == 'male')

# TODO: this is also weirdly broken:
#
# one = call_foo(1 + 2, y, z+w-2)


import ast
import sys

__all__ = ['parse_and_add_extents']

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
               ast.alias,
               ast.excepthandler,
               ast.Set, # are these 'set' literals?
               ast.arguments,
               ast.IfExp,
               ast.Ellipsis, # a rarely-occuring bad egg; it doesn't have col_offset, ugh
               # TODO: is this still a legit comment?
               ast.Expr, # ALWAYS ignore this or else you get into bad conflicts
               ]


def copy_end_attrs(from_node, to_node):
    to_node.end_col = from_node.end_col
    to_node.end_lineno = from_node.end_lineno

def gen_children(node):
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item
        elif isinstance(value, ast.AST):
            yield value

def add_extent_attrs(node):
    if 'start_col' not in node._attributes:
        node._attributes = node._attributes + ('start_col', 'end_col', 'end_lineno')

# Adds start_col, end_col, and end_lineno fields to each AST node, as
# appropriate. After running, each node should have extent information
# in the form of either:
#   (lineno, start_col) to (end_lineno, end_col)
#   lineno, col_offset
#
# This visitor runs top-down, so we probably NEED to run several times to
# fixpoint adds extents and also adds lineno and col_offset to certain
# nodes that don't ordinarily have them
class AddExtentsVisitor(ast.NodeVisitor):
    def __init__(self, code_str):
        ast.NodeVisitor.__init__(self)
        # add sentinel to support one-indexing
        self.code_lines = [''] + code_str.split('\n')

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

    def visit_ExtSlice(self, node):
      raise NotImplementedError

    def visit_Repr(self, node):
      raise NotImplementedError

    def visit_Assert(self, node):
      raise NotImplementedError

    def visit_TryFinally(self, node):
      raise NotImplementedError

    def visit_Lambda(self, node):
      raise NotImplementedError

    def visit_Exec(self, node):
      raise NotImplementedError

    def visit_comprehension(self, node):
      raise NotImplementedError

    def visit_With(self, node):
      raise NotImplementedError

    def visit_GeneratorExp(self, node):
      raise NotImplementedError

    def visit_ListComp(self, node):
      raise NotImplementedError

    def visit_DictComp(self, node):
      raise NotImplementedError

    def visit_SetComp(self, node):
      raise NotImplementedError


    ### stuff below is implemented ...

    def visit_ExceptHandler(self, node):
        if node.type:
            self.standard_visitor(node, node.type)
        else:
            # naked 'except'
            self.keyword_visitor(node, 'except')

    def visit_Global(self, node):
        # TODO: this doesn't handle a multiline statement that uses '\'
        # operators
        add_extent_attrs(node)
        node.start_col = node.col_offset
        node.end_col = len(self.code_lines[node.lineno])
        node.end_lineno = node.lineno
        self.visit_children(node)

    def visit_Raise(self, node):
        if node.tback:
            self.standard_visitor(node, node.tback)
        elif node.inst:
            self.standard_visitor(node, node.inst)
        elif node.type:
            self.standard_visitor(node, node.type)
        else:
            # naked 'raise'
            self.keyword_visitor(node, 'raise')

    def visit_FunctionDef(self, node):
        self.visit_func_and_class_def(node)

    def visit_ClassDef(self, node):
        self.visit_func_and_class_def(node)

    def visit_func_and_class_def(self, node):
        # ok this is janky, but I think it works well in practice: just
        # scan until you find the next ':', either on this line or on a
        # subsequent line
        if not hasattr(node, 'start_col'):
            node.start_col = node.col_offset
            n = node.lineno
            while True:
                cur_line = self.code_lines[n]
                if ':' in cur_line:
                    node.end_col = cur_line.index(':')
                    node.end_lineno = n
                    break
                n += 1
        self.visit_children(node)

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

    def visit_Attribute(self, node):
        if hasattr(node.value, 'start_col'):
            add_extent_attrs(node)
            node.start_col = node.col_offset
            node.end_col = len(node.attr) + 1 + node.value.end_col
            node.end_lineno = node.lineno
        self.visit_children(node)

    def visit_Dict(self, node):
        # empty case
        if len(node.values) == 0:
            node.start_col = node.col_offset
            node.end_col = node.start_col + 2 # for '{}' case; doesn't handle blank spaces
            node.end_lineno = node.lineno
        else:
            last_elt = node.values[-1]
            if hasattr(last_elt, 'start_col'):
                add_extent_attrs(node)
                node.start_col = node.col_offset
                copy_end_attrs(last_elt, node)
                node.end_col += 1 # for the extra trailing '}' character
        self.visit_children(node)

    def visit_List(self, node):
        # empty case
        if len(node.elts) == 0:
            node.start_col = node.col_offset
            node.end_col = node.start_col + 2 # for '[]' case; doesn't handle blank spaces
            node.end_lineno = node.lineno
        else:
            last_elt = node.elts[-1]
            if hasattr(last_elt, 'start_col'):
                add_extent_attrs(node)
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

                add_extent_attrs(node)
                node.start_col = node.col_offset
                copy_end_attrs(last_elt, node)
                node.end_col += trailing_offset

                # adjust for parens
                if node.start_col > 0:
                    if self.code_lines[node.lineno][node.start_col - 1] == '(':
                        node.start_col -= 1
                        node.end_col += 1
        self.visit_children(node)

    # to make this more robust to parens, etc., we could simply search
    # for the next ':' character, like visit_func_and_class_def does
    def visit_If(self, node):
        if hasattr(node.test, 'start_col'):
            add_extent_attrs(node)
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


    def visit_Return(self, node):
        self.visit_return_or_yield(node, 'return')

    def visit_Yield(self, node):
        self.visit_return_or_yield(node, 'yield')

    def visit_return_or_yield(self, node, keyword):
        if node.value:
            self.standard_visitor(node, node.value)
        else:
            # naked
            self.keyword_visitor(node, keyword)

    # grab end_col and end_lineno from the rightmost attribute
    def standard_visitor(self, node, rightmost_attr, end_col_adjustment=0):
        if hasattr(rightmost_attr, 'start_col'):
            add_extent_attrs(node)
            node.start_col = node.col_offset
            copy_end_attrs(rightmost_attr, node)
            node.end_col += end_col_adjustment
        self.visit_children(node)

    def keyword_visitor(self, node, keyword, end_col_adjustment=0):
        add_extent_attrs(node)
        node.start_col = node.col_offset
        node.end_col = node.start_col + len(keyword) + end_col_adjustment
        node.end_lineno = node.lineno
        self.visit_children(node)

    def visit_Subscript(self, node):
        # super-special case of an empty slice like 'foo[:]', since
        # that doesn't have end_col and end_lineno fields of its own
        if (isinstance(node.slice, ast.Slice) and
            not node.slice.lower and
            not node.slice.upper and
            not node.slice.step):
            self.standard_visitor(node, node.value, len('[:]'))
        else:
            # add 1 for trailing ']'
            self.standard_visitor(node, node.slice, 1)

    # TODO: merge together with visit_Index
    def visit_keyword(self, node):
        # keyword nodes don't have a col_offset or lineno, so STEAL
        # those from child (warning: super hacky but should work!)
        # (this doesn't work if node.value starts on a different line as node)
        node.lineno = node.value.lineno
        node.col_offset = node.value.col_offset
        node._attributes = node._attributes + ('lineno', 'col_offset')
        self.standard_visitor(node, node.value)

    def visit_Index(self, node):
        # index nodes don't have a col_offset or lineno, so STEAL
        # those from child
        # (this doesn't work if node.value starts on a different line as node)
        node.lineno = node.value.lineno
        node.col_offset = node.value.col_offset
        node._attributes = node._attributes + ('lineno', 'col_offset')
        self.standard_visitor(node, node.value)

    def visit_Slice(self, node):
        # slice nodes don't have a col_offset or lineno, so STEAL
        # those from a child.
        # if there is a lower, use that
        if node.lower:
            node.lineno = node.lower.lineno
            node.col_offset = node.lower.col_offset
            node._attributes = node._attributes + ('lineno', 'col_offset')
        # otherwise, use upper - 1, to account for ':'
        # e.g., foo[:5]
        elif node.upper:
            node.lineno = node.upper.lineno
            node.col_offset = node.upper.col_offset - 1
            node._attributes = node._attributes + ('lineno', 'col_offset')
        # otherwise use step - 2, to account for '::'
        # e.g., foo[::3]
        elif node.step:
            node.lineno = node.step.lineno
            node.col_offset = node.step.col_offset - 2
            node._attributes = node._attributes + ('lineno', 'col_offset')
        else:
            # empty case like foo[:]
            # oh carp! this doesn't have any child nodes from whom to
            # steal lineno and col_offset, so leave them empty
            pass

        # now determine which is the rightmost node to visit
        if node.step:
            self.standard_visitor(node, node.step)
        elif node.upper:
            self.standard_visitor(node, node.upper)
        elif node.lower: 
            self.standard_visitor(node, node.lower, 1) # add 1 for trailing ':'
        else:
            # empty case like foo[:]
            pass

    # to make this more robust to parens, etc., we could simply search
    # for the next ':' character, like visit_func_and_class_def does
    def visit_For(self, node):
        self.standard_visitor(node, node.iter)
    def visit_While(self, node):
        self.standard_visitor(node, node.test)

    def visit_Delete(self, node):
        self.standard_visitor(node, node.targets[-1])
    def visit_Assign(self, node):
        self.standard_visitor(node, node.value)
    def visit_AugAssign(self, node):
        self.standard_visitor(node, node.value)
    def visit_BinOp(self, node):
        self.standard_visitor(node, node.right)
    def visit_UnaryOp(self, node):
        self.standard_visitor(node, node.operand)
    def visit_BoolOp(self, node):
        self.standard_visitor(node, node.values[-1])
    def visit_Compare(self, node):
        self.standard_visitor(node, node.comparators[-1])

    def visit_Import(self, node):
        self.visit_import_hack(node)
    def visit_ImportFrom(self, node):
        self.visit_import_hack(node)

    # ugh, we can't get precise line/col info about child nodes of
    # imports, so just punt and say that they take up the entire line
    # (up to an optional semicolon, which starts the next line)
    def visit_import_hack(self, node):
        cur_line = self.code_lines[node.lineno]
        node.start_col = node.col_offset
        node.end_col = len(cur_line)
        node.end_lineno = node.lineno

        # if there's a semicolon, then truncate there:
        if ';' in cur_line:
            node.end_col = cur_line.index(';')
        

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
          add_extent_attrs(node)
          node.start_col = node.col_offset
          node.end_col = node.start_col + len(node.id)
          node.end_lineno = node.lineno

    def visit_Str(self, node):
        if node.col_offset >= 0:
            # TRICKY TRICKY! don't run this more than once, ughhhhhh
            if hasattr(node, 'start_col'):
                return
            add_extent_attrs(node)
            node.start_col = node.col_offset
            # repr() will take escape characters and enclosing quotes into account!
            node.end_col = node.start_col + len(repr(node.s))
            node.end_lineno = node.lineno
        else:
            # multiline strings, which come with weird -1 column offsets!
            # UGH THIS IS REALLY AGGRAVATING with tons of corner cases
            add_extent_attrs(node)
            node.end_lineno = node.lineno
            lines = node.s.splitlines()
            # SUPER tricky -- if the last character is '\n', then add an
            # extra blank line to the end, ugh! really subtle.
            # e.g.,:
            # my_str = '''hello
            # world
            # goodbye
            # ''' # empty last line!
            if node.s[-1] == '\n':
                lines.append('')
            n_lines = len(lines)
            node.lineno = node.end_lineno - n_lines + 1
            full_original_line = self.code_lines[node.lineno]
            first_line = lines[0]
            if first_line == '': # if it's an empty first line, ugh!
                node.col_offset = len(full_original_line) - 3 # for leading """ or '''
            else:
                first_line_loc = full_original_line.index(first_line)
                assert first_line_loc >= 3
                node.col_offset = first_line_loc - 3 # for leading """ or '''
            node.start_col = node.col_offset
            node.end_col = len(lines[-1]) + 3 # for trailing """ or '''
            # sanity checks
            sanity_check_first_substr = self.code_lines[node.lineno][node.start_col:]
            sanity_check_last_substr = self.code_lines[node.end_lineno][:node.end_col]
            assert (sanity_check_first_substr.startswith('"""') or
                    sanity_check_first_substr.startswith("'''"))
            assert (sanity_check_last_substr.endswith('"""') or
                    sanity_check_last_substr.endswith("'''"))


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
        add_extent_attrs(node)
        node.start_col = node.col_offset
        node.end_col = node.start_col + len(str(node.n))
        node.end_lineno = node.lineno
        # adjustment for negative decimal numbers
        # (ASSUMING WE ARE WRITING IN DECIMAL FORMAT!)
        if node.n < 0:
            node.start_col -= 1
            node.end_col -= 1

    def visit_Pass(self, node):
      self.keyword_visitor(node, 'pass')

    def visit_Break(self, node):
      self.keyword_visitor(node, 'break')

    def visit_Continue(self, node):
      self.keyword_visitor(node, 'continue')

    def visit_TryExcept(self, node):
        self.keyword_visitor(node, 'try')


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



# ERGH nasty hack to get even simple cases like "d = a + b + c" working
# clean up extents by propagating the smallest start_col, lineno, and
# col_offset of each node's child to itself, if necessary
#
# again, we need to run this multiple times to fixpoint, ERGH!!!
class FixupExtentsVisitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)

    def visit(self, node):
        for child in gen_children(node):
            if hasattr(child, 'lineno'):
                # grab the minimum lineno and col_offset from any of
                # your children
                if not hasattr(node, 'lineno'):
                    node._attributes = node._attributes + ('lineno', 'col_offset')
                    node.lineno = child.lineno
                    node.col_offset = child.col_offset
                else:
                    node.lineno = min(node.lineno, child.lineno)
                    node.col_offset = min(node.col_offset, child.col_offset)

            # if BOTH you and your child have start_col, then grab the
            # smaller of the two
            if hasattr(node, 'start_col') and hasattr(child, 'start_col'):
                # VERY IMPORTANT guard condition!
                if node.lineno == child.lineno:
                    node.start_col = min(node.start_col, child.start_col)

        super(FixupExtentsVisitor, self).visit(node)


# create abs_start_index and abs_end_index attributes for nodes with
# extent information in the form of:
#   (lineno, start_col) to (end_lineno, end_col)
class AddAbsoluteExtentsVisitor(ast.NodeVisitor):
    def __init__(self, code_str):
        ast.NodeVisitor.__init__(self)
        # add sentinel to support one-indexing
        self.code_lines = [''] + code_str.split('\n')

    def visit(self, node):
        if hasattr(node, 'end_col'):
            node._attributes = node._attributes + ('abs_start_index', 'abs_end_index')

            node.abs_start_index = 0
            for i in range(1, node.lineno):
                # +1 for ending newline!
                node.abs_start_index += len(self.code_lines[i]) + 1
            node.abs_start_index += node.start_col

            node.abs_end_index = 0
            for i in range(1, node.end_lineno):
                # +1 for ending newline!
                node.abs_end_index += len(self.code_lines[i]) + 1
            node.abs_end_index += node.end_col

            assert node.abs_start_index <= node.abs_end_index

        super(AddAbsoluteExtentsVisitor, self).visit(node)


def extent_contains(parent, child):
    if hasattr(parent, 'abs_start_index') and hasattr(child, 'abs_start_index'):
        return (parent.abs_start_index <= child.abs_start_index <=
                child.abs_end_index <= parent.abs_end_index)
    return True

def extents_disjoint(parent, child):
    if hasattr(parent, 'abs_start_index') and hasattr(child, 'abs_start_index'):
        return ((parent.abs_end_index <= child.abs_start_index) or
                (child.abs_end_index <= parent.abs_start_index))
    return True

def extent_to_str(node):
    lab = ''
    if hasattr(node, 'end_col'):
        if node.lineno == node.end_lineno:
            lab += 'L{0}[{1}:{2}]'.format(node.lineno, node.start_col, node.end_col)
        else:
            lab += 'L{0}[{1}] - '.format(node.lineno, node.start_col)
            lab += 'L{0}[{1}]'.format(node.end_lineno, node.end_col)
    # fallback ...
    elif hasattr(node, 'lineno'):
        lab += 'L{0}[{1}]'.format(node.lineno, node.col_offset)
        lab += ' (no extents)'
    else:
        lab += '<NONE WTF>'

    return lab


# verifies the tree after AddExtentsVisitor finishes running on it
class ExtentsVerifierVisitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)

    def visit(self, node):
        if hasattr(node, 'end_col'):
            assert node.lineno <= node.end_lineno
            if node.lineno == node.end_lineno:
                assert node.start_col < node.end_col

            # make sure no child "overlaps" with myself. children that
            # are completely contained are okay, as are children that
            # have NO overlaps.
            for child in gen_children(node):
                #print '---'
                #print 'P:', extent_to_str(node)
                #print 'C:', extent_to_str(child)
                assert (extent_contains(node, child) or
                        extents_disjoint(node, child))

        elif hasattr(node, 'lineno'):
            pass

        super(ExtentsVerifierVisitor, self).visit(node)


def parse_and_add_extents(code_str):
    root_node = ast.parse(code_str)

    dcv = DepthCountingVisitor()
    dcv.visit(root_node)
    max_depth = dcv.max_depth

    # To be conservative, run the visitor max_depth number of times, which
    # should be enough to percolate ALL (start_col, extent) values up from
    # the leaves to the root of the tree
    v = AddExtentsVisitor(code_str)
    for i in range(max_depth):
        v.visit(root_node)

    # OH MY GODDD!!! FIXPOINT!!!
    v2 = FixupExtentsVisitor()
    for i in range(max_depth):
        v2.visit(root_node)

    v3 = AddAbsoluteExtentsVisitor(code_str)
    v3.visit(root_node)

    # sanity check!
    verifier = ExtentsVerifierVisitor()
    verifier.visit(root_node)

    return root_node


if __name__ == "__main__":
    code_str = open(sys.argv[1]).read()

    m = parse_and_add_extents(code_str)

    print code_str,
    print '==='
    pretty_dump(m, code_str)
