import unittest
from . import parser
# from . import node


class TestParse(unittest.TestCase):
    def test_p03(self):
        """Expected failure"""
        s = """[1 ; 1; 1 ; ];"""
        t = parser.parse(s)
        self.assertTrue(t)

# FIXME
#   def test_p04(self):
#       """Dot has higher precedence than other operations"""
#       s = "a+b.c.d;"
#       t = parser.parse(s)
#       u = [node.expr_stmt(node.expr=[('+', parser.ident(name='a'),
#       parser.field(expr=parser.field(expr=parser.ident(name='b')
#       lineno=1, lexpos=2), ident=node.ident(name='.c'),
#           ident=parser.ident(name='.d')))])]
#       self.assertEqual(t,u)

#    def test_p05(self):
#        """Iterate over LHS nodes (TBD)"""
#        s = "[foo(A.x(B.y)).bar(C.z).bzz,hello.world] =1;"
#        t = parser.parse(s)
#        u = ["foo",".bar",".bzz","hello",".world"]
#        self.assertEqual([v[1] for v in dataflow.lhs(t[1][1])],u)
#
#    def test_p06(self):
#        """Cell arrays"""
#        s = """
#        {1 ...
#    'foo' ...
#        'bar' ...
#        'bzz'};
#        """
#        t = parser.parse(s)
#        self.assert_(t)


if __name__ == "__main__":
    unittest.main()
