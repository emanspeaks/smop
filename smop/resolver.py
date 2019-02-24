#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Symbol resolution from raw parser output

SMOP -- Simple Matlab/Octave to Python compiler
Copyright 2018 Victor Leikehman

if i.defs:
    i is defined, possibly more than once.
    Typical for vairable references.

if i.defs is None:
    i is a definition (lhs)

if i.defs == set():
    i is used but not defined.
    Typical for function calls.

symtab is a temporary variable, which maps
variable names (strings) to sets of ident
instances, which possibly define the variable.
It is used in if_stmt, for_stmt, and while_stmt.
"""

import copy

from . import node
from .node import extend


def resolve(t, symtab=None, fp=None, func_name=None):
    if symtab is None:
        symtab = {}
    do_resolve(t, symtab)
    peep(t)


def peep(t):
    for u in node.postorder(t):
        # to_arrayref(u)
        colon_subscripts(u)
        # end_expressions(u)
        let_statement(u)


# def to_arrayref(u):
#     """
#     To the parser, funcall is indistinguishable
#     from rhs array reference.  But LHS references
#     can be converted to arrayref nodes.
#     """
#     if u.__class__ is node.funcall:
#         try:
#             if u.func_expr.props in "UR":  # upd,ref
#                 u.__class__ = node.arrayref
#         except Exception:
#             pass  # FIXME


def colon_subscripts(u):
    """
    Array colon subscripts foo(1:10) and colon expressions 1:10 look
    too similar to each other.  Now is the time to find out who is who.
    """
    if u.__class__ in (node.arrayref, node.cellarrayref):
        for w in u.args:
            if w.__class__ is node.expr and w.op == ":":
                w._replace(op="::")


# def end_expressions(u):
#     if u.__class__ in (node.arrayref, node.cellarrayref):
#         if u.__class__ is node.expr and u.op == "end":
#             u.args[0] = u.func_expr
#             u.args[1] = node.number(i)  # FIXME


def let_statement(u):
    """
    If LHS is a plain variable, and RHS is a matrix
    enclosed in square brackets, replace the matrix
    expr with a funcall.
    """
    if u.__class__ is node.let:
        if (u.ret.__class__ is node.ident and
                u.args.__class__ is node.matrix):
            u.args = node.funcall(func_expr=node.ident("matlabarray"),
                                  args=node.expr_list([u.args]))


def do_resolve(t, symtab):
    t._resolve(symtab)


def copy_symtab(symtab):
    new_symtab = copy.copy(symtab)
    for k, v in list(new_symtab.items()):
        new_symtab[k] = copy.copy(v)
    return new_symtab


@extend(node.arrayref, "_lhs_resolve")
@extend(node.cellarrayref, "_lhs_resolve")
@extend(node.funcall, "_lhs_resolve")
def ref_lhs_resolve(self, symtab):
    # Definitely lhs array indexing.  It's both a ref and a def.
    # Must properly handle cases such as foo(foo(17))=42
    # Does the order of A and B matter?
    if self.__class__ == node.funcall:
        self.__class__ = node.arrayref
    self.func_expr._resolve(symtab)  # A
    self.args._resolve(symtab)       # B
    self.func_expr._lhs_resolve(symtab)


@extend(node.expr, "_lhs_resolve")
def expr_lhs_resolve(self, symtab):
    if self.op == ".":  # see setfield
        self.args._resolve(symtab)
        self.args[0]._lhs_resolve(symtab)
    elif self.op == "[]":
        for arg in self.args:
            arg._lhs_resolve(symtab)


@extend(node.expr_stmt, "_resolve")
def expr_stmt_resolve(self, symtab):
    self.expr._resolve(symtab)


@extend(node.for_stmt, "_resolve")
def for_stmt_resolve(self, symtab):
    symtab_copy = copy_symtab(symtab)
    self.ident._lhs_resolve(symtab)
    self.expr._resolve(symtab)
    self.stmt_list._resolve(symtab)
    self.stmt_list._resolve(symtab)  # 2nd time, intentionally
    # Handle the case where FOR loop is not executed
    symtab.update(symtab_copy)


@extend(node.func_stmt, "_resolve")
def func_stmt_resolve(self, symtab):
    if self.ident:
        self.ident._lhs_resolve(symtab)
        self.ident.props = 'N'
    self.args._lhs_resolve(symtab)
    self.ret._resolve(symtab)


@extend(node.global_list, "_lhs_resolve")
@extend(node.concat_list, "_lhs_resolve")
@extend(node.expr_list, "_lhs_resolve")
def list_lhs_resolve(self, symtab):
    for expr in self:
        expr._lhs_resolve(symtab)


@extend(node.global_list, "_resolve")
@extend(node.concat_list, "_resolve")
@extend(node.expr_list, "_resolve")
def list_resolve(self, symtab):
    for expr in self:
        expr._resolve(symtab)


@extend(node.global_stmt, "_resolve")
def global_stmt_resolve(self, symtab):
    self.global_list._lhs_resolve(symtab)


@extend(node.ident, "_lhs_resolve")
def ident_lhs_resolve(self, symtab):
    # symtab[self.name] = [self]
    symtab.setdefault(self.name, [self])


@extend(node.if_stmt, "_resolve")
def if_stmt_resolve(self, symtab):
    symtab_copy = copy_symtab(symtab)
    self.cond_expr._resolve(symtab)
    self.then_stmt._resolve(symtab)
    if self.else_stmt:
        self.else_stmt._resolve(symtab_copy)
    symtab.update(symtab_copy)


@extend(node.let, "_lhs_resolve")
def let_lhs_resolve(self, symtab):
    self.args._resolve(symtab)
    self.ret._lhs_resolve(symtab)


@extend(node.let, "_resolve")
def let_resolve(self, symtab):
    self.args._resolve(symtab)
    self.ret._lhs_resolve(symtab)


@extend(node.null_stmt, "_resolve")
@extend(node.continue_stmt, "_resolve")
@extend(node.break_stmt, "_resolve")
def loop_ctrl_resolve(self, symtab):
    pass


@extend(node.setfield, "_resolve")  # a subclass of funcall
def setfield_resolve(self, symtab):
    self.func_expr._resolve(symtab)
    self.args._resolve(symtab)
    self.args[0]._lhs_resolve(symtab)


@extend(node.try_catch, "_resolve")
def try_catch_resolve(self, symtab):
    self.try_stmt._resolve(symtab)
    self.catch_stmt._resolve(symtab)  # ???


@extend(node.ident, "_resolve")
def ident_resolve(self, symtab):
    if self.defs is None:
        self.defs = []
    if self.init:
        self._lhs_resolve(symtab)
        self.init._resolve(symtab)
    else:
        try:
            self.defs += symtab[self.name]
        except KeyError:
            # defs == set() means name used, but not defined
            pass


@extend(node.arrayref, "_resolve")
@extend(node.cellarrayref, "_resolve")
@extend(node.funcall, "_resolve")
def ref_resolve(self, symtab):
    # Matlab does not allow foo(bar)(bzz), so func_expr is usually
    # an ident, though it may be a field or a dot expression.
    if self.func_expr:
        self.func_expr._resolve(symtab)
    self.args._resolve(symtab)


@extend(node.expr, "_resolve")
def expr_resolve(self, symtab):
    for expr in self.args:
        expr._resolve(symtab)


@extend(node.number, "_resolve")
@extend(node.string, "_resolve")
@extend(node.comment_stmt, "_resolve")
def literal_resolve(self, symtab):
        pass


# @extend(node.call_stmt)
# def _resolve(self,symtab):
#     # TODO: does the order of A and B matter? Only if the
#     # evaluation of function args may change the value of the
#     # func_expr.
#     self.func_expr._resolve(symtab) # A
#     self.args._resolve(symtab)      # B
#     self.ret._lhs_resolve(symtab)


@extend(node.return_stmt, "_resolve")
def return_stmt_resolve(self, symtab):
    self.ret._resolve(symtab)
    # symtab.clear()


@extend(node.stmt_list, "_resolve")
def stmt_list_resolve(self, symtab):
    for stmt in self:
        stmt._resolve(symtab)


@extend(node.where_stmt, "_resolve")  # FIXME where_stmt ???
@extend(node.while_stmt, "_resolve")
def loop_resolve(self, symtab):
    symtab_copy = copy_symtab(symtab)
    self.cond_expr._resolve(symtab)
    self.stmt_list._resolve(symtab)
    self.cond_expr._resolve(symtab)
    self.stmt_list._resolve(symtab)
    # Handle the case where WHILE loop is not executed
    symtab.update(symtab_copy)


@extend(node.function, "_resolve")
def function_resolve(self, symtab):
    self.head._resolve(symtab)
    self.body._resolve(symtab)
    self.head.ret._resolve(symtab)
