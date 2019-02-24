#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
SMOP compiler -- Simple Matlab/Octave to Python compiler
Copyright 2011-2019 Victor Leikehman
'''

from . import (backends,
               lexer,
               libsmop,
               node,
               parser,
               recipes,
               resolver,
               )
assert all((backends,
            lexer,
            libsmop,
            node,
            parser,
            recipes,
            resolver,
            ))

from .parser import parse  # noqa: E402
assert parse

from .resolver import resolve  # noqa: E402
assert resolve

from .backends import backend  # noqa: E402
assert backend
