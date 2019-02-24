#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backends to write out Python from the MATLAB parsed objects

SMOP -- Simple Matlab/Octave to Python compiler
Copyright 2011-2016 Victor Leikehman
"""

# """
# Calling conventions:

# call site:  nargout=N is passed if and only if N > 1
# func decl:  nargout=1 must be declared if function may return
#             more than one return value.  Otherwise optional.
# return value:  return (x,y,z)[:nargout] or return x
# """

import logging

from . import node
from . import options
from .node import extend

import numpy
from . import libsmop

logger = logging.getLogger(__name__)
indent = " "*4

newline = "\n"

optable = {"!": "not",
           "~": "not",
           "~=": "!=",
           "|": "or",
           "&": "and",
           "||": "or",
           "&&": "and",
           "^": "**",
           "**": "**",
           ".^": "**",
           "./": "/",
           ".*": "*",
           ".*=": "*",
           "./=": "/",
           }
"""Table of operators and their Python equivalents"""


def backend(t, *args, **kwargs):
    return t._backend(level=0, *args, **kwargs)


# Sometimes user's variable names in the matlab code collide with Python
# reserved words and constants.  We handle this in the backend rather than in
# the lexer, to keep the target language separate from the lexer code.

# Some names, such as matlabarray, may collide with the user defined names.
# Both cases are solved by appending a trailing underscore to the user's names.

reserved = set(
    """
    and    assert  break class continue
    def    del     elif  else  except
    exec   finally for   from  global
    if     import  in    is    lambda
    not    or      pass  print raise
    return try     while with

    Data  Float Int   Numeric Oxphys
    array close float int     input
    open  range type  write

    len
    """.split())
# acos  asin atan  cos e
# exp   fabs floor log log10
# pi    sin  sqrt  tan


@extend(node.add, "_backend")
def add_backend(self, level=0):
    if (self.args[0].__class__ is node.number and
            self.args[1].__class__ is node.number):
        return node.number(self.args[0].value +
                           self.args[1].value)._backend()
    else:
        return "(%s + %s)" % (self.args[0]._backend(),
                              self.args[1]._backend())


@extend(node.arrayref, "_backend")
def arrayref_backend(self, level=0, lhs=None, dot=False):
    fmt = "%s.get(%s)" if dot else "%s[%s]"
    funcinit = "libsmop.matlabarray"
    func = self.func_expr

    args = self.args._backend()
    if lhs is None:
        funcstr = func._backend()
    else:
        lhs2 = list()
        if isinstance(func, node.ident):
            funcstr = func._backend()
            if not func.defs:
                lhs2.append('%s = %s()' % (funcstr, funcinit))
        elif isinstance(func, node.expr) and func.op == '.':
            funcexpr = func.args[0]._backend(lhs=lhs2)
            # assume the end of the chain is an ident
            funcname = repr(func.args[1]._backend())
            funcstr = '%s[%s]' % (funcexpr, funcname)
            if dot:
                lhs2.append('%s.setdefault(%s, %s(dtype=object))'
                            % (funcexpr, funcname, funcinit))
                lhs2.append('%s.setdefault(%s, dict())' % (funcstr, args))
            else:
                lhs2.append('%s.setdefault(%s, %s())'
                            % (funcexpr, funcname, funcinit))
        else:
            # i dunno...
            raise NotImplementedError
        lhs[0:0] = lhs2

    return fmt % (funcstr, args)


@extend(node.break_stmt, "_backend")
def break_stmt_backend(self, level=0):
    return "break"


@extend(node.builtins, "_backend")
def builtins_backend(self, level=0):
    # if not self.ret:
        return "%s(%s)" % (self.__class__.__name__,
                           self.args._backend())


@extend(node.cellarray, "_backend")
def cellarray_backend(self, level=0):
    return "libsmop.cellarray([%s])" % self.args._backend()


@extend(node.cellarrayref, "_backend")
def cellarrayref_backend(self, level=0, lhs=None, dot=False):
    fmt = "%s.get(%s)" if dot else "%s[%s]"
    funcinit = "libsmop.cellarray"
    func = self.func_expr

    args = self.args._backend()
    if lhs is None:
        funcstr = func._backend()
    else:
        lhs2 = list()
        if isinstance(func, node.ident):
            funcstr = func._backend()
            if not func.defs:
                lhs2.append('%s = %s' % (funcstr, funcinit))
        elif isinstance(func, node.expr) and func.op == '.':
            funcexpr = func.args[0]._backend(lhs=lhs2)
            # assume the end of the chain is an ident
            funcname = repr(func.args[1]._backend())
            lhs2.append('%s.setdefault(%s, %s)'
                        % (funcexpr, funcname, funcinit))
            funcstr = '%s[%s]' % (funcexpr, funcname)
            lhs2.append('%s.setdefault(%s, dict())' % (funcstr, args))
        else:
            # i dunno...
            raise NotImplementedError
        lhs[0:0] = lhs2

    return fmt % (funcstr, args)


@extend(node.comment_stmt, "_backend")
def comment_stmt_backend(self, level=0):
    s = self.value.strip()
    if not s:
        return ""
    if s[0] in "%#":
        return "# " + s
    return self.value


@extend(node.concat_list, "_backend")
def concat_list_backend(self, level=0):
    # import pdb; pdb.set_trace()
    return ", ".join(["[%s]" % t._backend() for t in self])


@extend(node.continue_stmt, "_backend")
def continue_stmt_backend(self, level=0):
    return "continue"


@extend(node.expr, "_backend")
def expr_backend(self, level=0, lhs=None, dot=False):
    if self.op in ("!", "~"):
        return "libsmop.logical_not(%s)" % self.args[0]._backend()

    if self.op == "&":
        return "libsmop.logical_and(%s)" % self.args._backend()

    if self.op == "&&":
        return "%s and %s" % (self.args[0]._backend(),
                              self.args[1]._backend())
    if self.op == "|":
        return "libsmop.logical_or(%s)" % self.args._backend()

    if self.op == "||":
        return "%s or %s" % (self.args[0]._backend(),
                             self.args[1]._backend())

    if self.op == '@':  # FIXME
        return self.args[0]._backend()

    if self.op == "\\":
        return "np.linalg.solve(%s, %s)" % (self.args[0]._backend(),
                                            self.args[1]._backend())
    if self.op == "::":
        if not self.args:
            return ":"
        elif len(self.args) == 2:
            return "%s:%s" % (self.args[0]._backend(),
                              self.args[1]._backend())
        elif len(self.args) == 3:
            return "%s:%s:%s" % (self.args[0]._backend(),
                                 self.args[2]._backend(),
                                 self.args[1]._backend())
    if self.op == ":":
        return "libsmop.arange(%s)" % self.args._backend()

    if self.op == "end":
        # if self.args:
        #     return "%s.shape[%s]" % (self.args[0]._backend(),
        #                              self.args[1]._backend())
        # else:
            return "libsmop.end()"

    if self.op == ".":
        # import pdb; pdb.set_trace()
        try:
            is_parens = self.args[1].op == "parens"
        except Exception:
            is_parens = False
        if not is_parens:
            if lhs is None:
                return "%s.%s" % (self.args[0]._backend(),
                                  self.args[1]._backend())
            else:
                lhs2 = list()
                if isinstance(self.args[0], node.ident):
                    args0 = self.args[0]._backend()
                    if not self.args[0].defs:
                        lhs2.append('%s = dict()' % args0)
                else:
                    args0 = self.args[0]._backend(lhs=lhs2, dot=True)

                if isinstance(self.args[1], node.ident):
                    ident = repr(self.args[1]._backend())
                    lhs2.append('%s.setdefault(%s, dict())'
                                % (args0, ident))
                    args1 = '[%s]' % ident
                else:  # arrayref or cellarrayref
                    func = repr(self.args[1].func_expr._backend())
                    if isinstance(self.args[1], node.cellarrayref):
                        functype = 'cellarray'
                    else:
                        functype = 'matlabarray'
                    lhs2.append('%s.setdefault(%s, libsmop.%s([]))'
                                % (args0, func, functype))
                    args1 = '[%s][%s]' % (func, self.args[1].args._backend())
                lhs[0:0] = lhs2
                return "%s%s" % (args0, args1)
        else:
            return "getattr(%s, %s)" % (self.args[0]._backend(),
                                        self.args[1]._backend())

#     if self.op == "matrix":
#         return "[%s]" % ",".join([t._backend() for t in self.args])
    if self.op == "parens":
        return "(%s)" % self.args[0]._backend()
#    if self.op == "[]":
#        return "[%s]" % self.args._backend()
    if not self.args:
        return self.op
    if len(self.args) == 1:
        return "%s%s" % (optable.get(self.op, self.op),
                         self.args[0]._backend())
    if len(self.args) == 2:
        return "%s %s %s" % (self.args[0]._backend(),
                             optable.get(self.op, self.op),
                             self.args[1]._backend())
    # import pdb;pdb.set_trace()
    ret = "%s = " % self.ret._backend() if self.ret else ""
    return ret+"%s(%s)" % (self.op,
                           ", ".join([t._backend() for t in self.args]))


@extend(node.expr_list, "_backend")
def expr_list_backend(self, level=0):
    return ", ".join([t._backend(level=level) for t in self])


@extend(node.expr_stmt, "_backend")
def expr_stmt_backend(self, level=0):
    return self.expr._backend(level=level)


@extend(node.for_stmt, "_backend")
def for_stmt_backend(self, level=0):
    fmt = "for %s in %s.reshape(-1):%s%s"
    return fmt % (self.ident._backend(),
                  self.expr._backend(),
                  newline,
                  self.stmt_list._backend(level+1))


@extend(node.func_stmt, "_backend")
def func_stmt_backend(self, level=0):
    self.args.append(node.ident("*args"))
    self.args.append(node.ident("**kwargs"))
    s = "def %s(%s):" % (self.ident._backend(), self.args._backend())
    s += newline + indent*(level + 1)
    s += "varargin = libsmop.cellarray(args)"
    s += newline + indent*(level + 1)
    s += "varargin"
    s += newline + indent*(level + 1)
    s += "nargin = len(args)"
    s += newline + indent*(level + 1)
    s += "nargin"
    s += newline
    return s


@extend(node.funcall, "_backend")
def funcall_backend(self, level=0):
    # import pdb; pdb.set_trace()

    funcname = self.func_expr._backend()
    if hasattr(libsmop, funcname):
        funcname = "libsmop." + funcname
    elif hasattr(numpy, funcname):
        funcname = "np." + funcname

    if not self.nargout or self.nargout == 1:
        return "%s(%s)" % (funcname,
                           self.args._backend())
    elif not self.args:
        return "%s(nargout=%s)" % (funcname,
                                   self.nargout)
    else:
        return "%s(%s, nargout=%s)" % (funcname,
                                       self.args._backend(),
                                       self.nargout)


@extend(node.global_list, "_backend")
def global_list_backend(self, level=0):
    return ", ".join([t._backend() for t in self])


@extend(node.ident, "_backend")
def ident_backend(self, level=0):
    name = self.name
    if name in reserved:
        name += "_"
    if self.init:
        return "%s = %s" % (name,
                            self.init._backend())
    return name


@extend(node.if_stmt, "_backend")
def if_stmt_backend(self, level=0):
    s = "if %s:%s%s" % (self.cond_expr._backend(),
                        newline,
                        self.then_stmt._backend(level+1))
    if self.else_stmt:
        # Eech. This should have been handled in the parser.
        if self.else_stmt.__class__ == node.if_stmt:
            self.else_stmt = node.stmt_list([self.else_stmt])
        s += newline + indent*level
        s += "else:%s%s" % (newline, self.else_stmt._backend(level+1))
    return s


@extend(node.lambda_expr, "_backend")
def lambda_expr_backend(self, level=0):
    return 'lambda %s: %s' % (self.args._backend(),
                              self.ret._backend())


@extend(node.let, "_backend")
def let_backend(self, level=0):
    if not options.no_numbers:
        t = "# %s:%s:%s" % (options.filename,
                            self.lineno,
                            newline + level*indent)
    else:
        t = ''

    s = ''
    # if self.args.__class__ is node.funcall:
    #    self.args.nargout = self.nargout
    if (isinstance(self.args, node.atom)
        or (isinstance(self.args, node.expr)
            and isinstance(self.args.args[1], node.atom))):
        args = "%s" % self.args._backend()
    else:
        args = "libsmop.copy(%s)" % self.args._backend()

    declist = list()
    if self.ret.__class__ is node.expr and self.ret.op == ".":
        ret = self.ret._backend(lhs=declist)
    else:
        ret = self.ret._backend(lhs=declist)

    for dec in declist:
            s += dec + newline + indent*level

    s += "%s = %s" % (ret, args)
    return t + s


@extend(node.logical, "_backend")
def logical_backend(self, level=0):
    if self.value == 0:
        return "False"
    else:
        return "True"


@extend(node.matrix, "_backend")
def matrix_backend(self, level=0):
    # TODO empty array has shape of 0 0 in matlab
    # size([])
    # 0 0
    if not self.args:
        return "[]"
    elif any(isinstance(a, node.string) for a in self.args[0]):
        return " + ".join(a._backend() for a in self.args[0])
    else:
        # import pdb; pdb.set_trace()
        return "libsmop.concat([%s], axis=0)" % self.args[0]._backend()


@extend(node.null_stmt, "_backend")
def null_stmt_backend(self, level=0):
    return ""


@extend(node.number, "_backend")
def number_backend(self, level=0):
    # if type(self.value) == int:
    #    return "%s.0" % self.value
    return str(self.value)


@extend(node.pass_stmt, "_backend")
def pass_stmt_backend(self, level=0):
    return "pass"


@extend(node.persistent_stmt, "_backend")  # FIXME
@extend(node.global_stmt, "_backend")
def persistent_global_stmt_backend(self, level=0):
    return "global %s" % self.global_list._backend()


@extend(node.return_stmt, "_backend")
def return_stmt_backend(self, level=0):
    if not self.ret:
        return "return"
    else:
        return "return %s" % self.ret._backend()


@extend(node.stmt_list, "_backend")
def stmt_list_backend(self, level=0):
    # check for all empty or block comment only
    for t in self:
        if not isinstance(t, (node.null_stmt,
                              node.comment_stmt)):
            break
    else:
        self.append(node.pass_stmt())
    s = ""
    n = len(self) - 1
    blankcount = 0
    for i, t in enumerate(self):
        if isinstance(t, node.null_stmt):
            if i == n:
                blankcount = 2
            else:
                blankcount += 1
        elif isinstance(t, node.stmt_list):
            if level > 0 or (level == 0 and i < n):
                blankcount = 0
            else:
                blankcount += 1
        elif isinstance(t, (node.for_stmt,
                            node.while_stmt,
                            node.try_catch,
                            node.func_stmt,
                            node.if_stmt)):
            blankcount = 1
        else:
            blankcount = 0

        if not isinstance(t, node.null_stmt):
            if level == 0 and i > 0:
                s += "\n"
            s += indent*level
        s += t._backend(level)
        if isinstance(t, node.func_stmt):
            level += 1
        elif isinstance(t, node.return_stmt):
            level -= 1

        if blankcount == 0:
            s += newline
        elif blankcount == 1:
            s += "\n"
    return s


@extend(node.string, "_backend")
def string_backend(self, level=0):
    # try:
    #     return "'%s'" % str(self.value).encode("string_escape")
    # except:
    #     return "'%s'" % str(self.value)
    # return "list(%s)" % repr(self.value)
    return repr(self.value)


@extend(node.sub, "_backend")
def sub_backend(self, level=0):
    return "(%s - %s)" % (self.args[0]._backend(),
                          self.args[1]._backend())


@extend(node.transpose, "_backend")
def transpose_backend(self, level=0):
    return "%s.T" % self.args[0]._backend()


@extend(node.try_catch, "_backend")
def try_catch_backend(self, level=0):
    fmt = "try: %s%sfinally: %s"
    return fmt % (self.try_stmt._backend(level+1),
                  newline + indent*level,
                  self.finally_stmt._backend(level+1))


@extend(node.while_stmt, "_backend")
def while_stmt_backend(self, level=0):
    fmt = "while %s:%s%s%s"
    return fmt % (self.cond_expr._backend(),
                  newline,
                  self.stmt_list._backend(level+1),
                  newline)
