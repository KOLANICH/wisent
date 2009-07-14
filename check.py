#! /usr/bin/env python
# check.py - some checks for the parsers generated by Wisent
#
# Copyright (C) 2008  Jochen Voss <voss@seehuhn.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
from os import remove, rmdir
from os.path import join
from tempfile import mkdtemp

from grammar import Grammar
from lr1 import Automaton


testdir = mkdtemp()
sys.path = [testdir] + sys.path

errors = 0


class FakeEOF(object):

    def set_real_eof(self, EOF):
        self.EOF = EOF

    def __eq__(self, other):
        return other == self.EOF

    def __hash__(self):
        return hash(self.EOF)

    def __repr__(self):
        return "EOF"

EOF = FakeEOF()

ignore = object()

def check(rules, tests, parser_args={}):
    print "-"*70
    g = Grammar(rules)
    a = Automaton(g)
    fd = open(join(testdir,"tmp.py"), "w")
    a.write_parser(fd)
    fd.close()
    del a, g

    import tmp
    reload(tmp)
    p = tmp.Parser(**parser_args)

    EOF.set_real_eof(p.EOF)

    for input,e_tree,e_err in tests:
        e_err = [ (x[0], frozenset(x[1])) for x in e_err ]

        print "input: "+repr(input)
        try:
            tree = p.parse((x,k) for k,x in enumerate(input))
            err = []
        except p.ParseErrors, e:
            tree = e.tree
            err = e.errors
            err = [ (x[0], frozenset(x[1])) for x in err ]

        success = True
        for e in e_err:
            if e not in err:
                print "  missed error: "+repr(e)
                success = False
        for e in err:
            if e not in e_err:
                print "  unexpected error: "+repr(e)
                success = False
        if e_tree != ignore and tree != e_tree:
            print "  unexpected result:"
            print "    expected: "+repr(e_tree)
            print "    got: "+repr(tree)
            success = False

        if success:
            print "  success"
        else:
            print "  failure"
            global errors
            errors += 1
    try:
        remove(join(testdir,"tmp.py"))
        remove(join(testdir,"tmp.pyc"))
    except OSError:
        pass


rules = [
    ('one', 1),
    ]
tests = [
    ([1], ('one', (1,0)), []),
    ([], ('one', (1,)), [((EOF,), [1])]),
    ([2], ('one', (1,)), [((2,0), [1])]),
    ([1,1], ('one', (1,0)), [((1,1), [EOF])]),
    ]
check(rules, tests)


rules = [
    ('A',),
    ('A', 'A', 'B'),
    ('B', 1),
    ('B', 2),
    ]
tests = [
    ([], ('A',), []),
    ([1], ('A', ('A',), ('B', (1,0))), []),
    ([1, 2], ('A', ('A', ('A',), ('B', (1,0))), ('B', (2,1))), []),
    ([1, 2, 3], ignore, [((3,2), [EOF, 2, 1])]),
    ]
check(rules, tests)


rules = [
    ('A', 0, 1, 2, 3),
    ]
tests = [
    ([0,1,2,3], ('A', (0,0), (1,1), (2,2), (3,3)), []),
    ([], ignore, [((EOF,), [0])]),
    # check insertion of tokens
    ([1,2,3], ('A', (0,), (1,0), (2,1), (3,2)), [((1,0), [0])]),
    # check removal of tokens
    ([5,0,1,2,3], ('A', (0,1), (1,2), (2,3), (3,4)), [((5,0), [0])]),
    # check replacement of tokens
    ([5,1,2,3], ('A', (0,), (1,1), (2,2), (3,3)), [((5,0), [0])]),
    ]
check(rules, tests)


# check errcorr_pre
rules = [
    ('A', 1, 'pad', 1, 1),
    ('A', 2, 'pad'),
    ('pad', 0, 0, 0),
    ]

tests = [
    ([1, 0, 0, 0], None, [((EOF,), [1])]),
    ]
check(rules, tests, {'errcorr_pre':3})

tests = [
    ([1, 0, 0, 0],
     ('A', (2,), ('pad', (0, 1), (0, 2), (0, 3))), [((EOF,), [1])]),
    ]
check(rules, tests, {'errcorr_pre':4})

# check errcorr_post
rules = [
    ('A', 1, 0, 0, 1),
    ('A', 2, 0, 0, 2),
    ]

tests = [
    ([3, 0, 0, 1], ('A', (1,), (0,1), (0,2), (1,3)), [((3,0), [1, 2])]),
    ([3, 0, 0, 2], ('A', (1,), (0,1), (0,2), (1,)), [((3,0), [1, 2]),
                                                     ((2,3), [1])]),
    ]
check(rules, tests, {'errcorr_post':2})

tests = [
    ([3, 0, 0, 1], ('A', (1,), (0,1), (0,2), (1,3)), [((3,0), [1, 2])]),
    ([3, 0, 0, 2], ('A', (2,), (0,1), (0,2), (2,3)), [((3,0), [1, 2])]),
    ]
check(rules, tests, {'errcorr_post':3})

rmdir(testdir)

if errors:
    raise SystemExit(1)
