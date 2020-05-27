from inspect import cleandoc
import sublime

from tutkain import tutkain
from unittest import TestCase


from .util import ViewTestCase


class TestIndentInsertNewLineCommand(ViewTestCase):
    def newline(self):
        self.view.run_command('tutkain_insert_newline')

    def becomes(self, a, b, points=[0], newlines=1, clean=True):
        self.append_to_view(cleandoc(a) if clean else a)

        self.add_cursors(*points)

        for n in range(newlines):
            self.newline()

        self.assertEquals(
            cleandoc(b) if clean else b,
            self.view_content()
        )


    def test_outside_before(self):
        self.becomes(
            '''(foo)''',
            '''\n\n(foo)''',
            newlines=2, clean=False
        )

    def test_outside_after(self):
        self.becomes(
            '''(foo)''',
            '''(foo)\n\n''',
            newlines=2, points=[5], clean=False
        )

    def test_inside(self):
        self.becomes(
            '''
            (foo
              (bar))
            ''',
            '''
            (foo
            \x20\x20
              (bar))
            ''',
            points=[4]
        )

    def test_nested_sexp_a(self):
        self.becomes(
            '''
            (a (b (c)))
            ''',
            '''
            (a
              (b (c)))
            ''',
            points=[2]
        )

    def test_nested_sexp_b(self):
        self.becomes(
            '''
            (a
              (b (c)))
            ''',
            '''
            (a
              (b
                (c)))
            ''',
            points=[7]
        )

    def test_multiple_newlines_inside(self):
        self.becomes(
            '''{:a 1 :b 2}''',
            '''{:a 1\n\n :b 2}''',
            points=[5], newlines=2, clean=False
        )

    # Test cases from https://tonsky.me/blog/clojurefmt/

    def test_tonsky_1a(self):
        self.becomes(
            '''
            (when something body)
            ''',
            '''
            (when something
              body)
            ''',
            points=[15]
        )

    def test_tonsky_1b(self):
        self.becomes(
            '''
            ( when something body)
            ''',
            '''
            ( when something
              body)
            ''',
            points=[16]
        )

    def test_tonsky_2(self):
        self.becomes(
            '''
            (defn f [x] body)
            ''',
            '''
            (defn f [x]
              body)
            ''',
            points=[11]
        )

    def test_tonsky_2a(self):
        self.becomes(
            '''
            (defn f [x] body)
            ''',
            '''
            (defn f
              [x] body)
            ''',
            points=[7]
        )

    def test_tonsky_2b(self):
        self.becomes(
            '''
            (defn f
              [x] body)
            ''',
            '''
            (defn f
              [x]
              body)
            ''',
            points=[13]
        )

    def test_tonsky_3_many_args(self):
        self.becomes(
            '''
            (defn many-args [a b c d e f]
              body)
            ''',
            '''
            (defn many-args [a b c
                             d e f]
              body)
            ''',
            points=[22]
        )

    def test_tonsky_4a_multi_arity(self):
        self.becomes(
            '''
            (defn multi-arity ([x] body) ([x y] body))
            ''',
            '''
            (defn multi-arity
              ([x] body) ([x y] body))
            ''',
            points=[17]
        )

    def test_tonsky_4b_multi_arity(self):
        self.becomes(
            '''
            (defn multi-arity
              ([x] body) ([x y] body))
            ''',
            '''
            (defn multi-arity
              ([x] body)
              ([x y] body))
            ''',
            points=[30]
        )

    def test_tonsky_5(self):
        self.becomes(
            '''
            (let [x 1 y 2]
              body)
            ''',
            '''
            (let [x 1
                  y 2]
              body)
            ''',
            points=[9]
        )


    def test_tonsky_6(self):
        self.becomes(
            '''
            [1 2 3 4 5 6]
            ''',
            '''
            [1 2 3
             4 5 6]
            ''',
            points=[6]
        )

    def test_tonsky_7(self):
        self.becomes(
            '''
            {:key-1 v1 :key-2 v2}
            ''',
            '''
            {:key-1 v1
             :key-2 v2}
            ''',
            points=[10]
        )

    def test_tonsky_8(self):
        self.becomes(
            '''
            #{a b c d e f}
            ''',
            '''
            #{a b c
              d e f}
            ''',
            points=[7]
        )

    def test_multiple_cursors(self):
        self.becomes(
            '''
            {:key-1 v1 :key-2 v2}

            #{a b c d e f}
            ''',
            '''
            {:key-1 v1
             :key-2 v2}

            #{a b c
              d e f}
            ''',
            points=[10, 30]
        )


class TestIndentFormCommand(ViewTestCase):
    def becomes(self, a, b, points=[1]):
        self.append_to_view(cleandoc(a))
        self.add_cursors(*points)
        self.view.run_command('tutkain_indent_region')
        self.assertEquals(cleandoc(b), self.view_content())

    def test_1(self):
        self.becomes(
            '''
            (when
            {:key-1 v1
              :key-2 v2})
            ''',
            '''
            (when
              {:key-1 v1
               :key-2 v2})
            '''
        )

    def test_2(self):
        self.becomes(
            '''
            {:a :b

             :c :d}
            ''',
            '''
            {:a :b
            \x20
             :c :d}
            '''
        )

    def test_3(self):
        self.becomes(
            '''
            [:a
             (when b
                c)]
            ''',
            '''
            [:a
             (when b
               c)]
            '''
        )

    def test_multiple_cursors(self):
        self.becomes(
            '''
            {:key-1 v1
               :key-2 v2}

            #{a b c
            d e f}
            ''',
            '''
            {:key-1 v1
             :key-2 v2}

            #{a b c
              d e f}
            ''',
            points=[11, 30]
        )