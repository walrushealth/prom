# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import datetime
import decimal

import testdata

from . import BaseTestCase, EnvironTestCase
import prom
from prom.model import Orm
from prom.config import Schema, Connection, DsnConnection, Index
from prom.config import Field
from prom.compat import *


class SchemaTest(BaseTestCase):
    def test_field_index_property(self):
        s = self.get_schema(
            foo=Field(str, index=True)
        )
        self.assertTrue("foo", s.indexes)
        self.assertFalse(s.indexes["foo"].unique)

    def test___init__(self):
        """
        I had set the class .fields and .indexes attributes to {} instead of None, so you
        could only ever create one instance of Schema, this test makes sure that's been fixed
        """
        s = Schema("foo")
        self.assertTrue(isinstance(s.fields, dict))
        self.assertTrue(isinstance(s.indexes, dict))

        s2 = Schema("bar")
        self.assertTrue(isinstance(s.fields, dict))
        self.assertTrue(isinstance(s.indexes, dict))

        s = Schema(
            "foo",
            bar=Field(int),
            che=Field(str, True),
            barche=Index("bar", "che")
        )
        self.assertTrue("bar" in s.fields)
        self.assertTrue("che" in s.fields)
        self.assertTrue("barche" in s.indexes)

    def test___getattr__(self):
        s = Schema("foo")

        with self.assertRaises(AttributeError):
            s.foo

        s.set_field("foo", Field(int, True))
        self.assertTrue(isinstance(s.foo, Field))

    def test_set_field(self):
        s = Schema("foo")

        with self.assertRaises(ValueError):
            s.set_field("", int)

        with self.assertRaises(ValueError):
            s.set_field("foo", "bogus")

        s.set_field("foo", Field(int))
        with self.assertRaises(ValueError):
            s.set_field("foo", int)

        s = Schema("foo")
        s.set_field("foo", Field(int, unique=True))
        self.assertTrue("foo" in s.fields)
        self.assertTrue("foo" in s.indexes)

        s = Schema("foo")
        s.set_field("foo", Field(int, ignore_case=True))
        self.assertTrue(s.foo.options["ignore_case"])

    def test_set_index(self):
        s = Schema("foo")
        s.set_field("bar", Field(int, True))
        s.set_field("che", Field(str))

        with self.assertRaises(ValueError):
            s.set_index("foo", Index())

        with self.assertRaises(ValueError):
            s.set_index("", Index("bar", "che"))

        s.set_index("bar_che", Index("che", "bar"))
        with self.assertRaises(ValueError):
            s.set_index("bar_che", Index("che", "bar"))

        s.set_index("testing", Index("che", unique=True))
        self.assertTrue(s.indexes["testing"].unique)

    def test_aliases_1(self):
        s = self.get_schema(
            foo=Field(int, aliases=["bar", "che"])
        )

        self.assertEqual(s.pk, s._id)
        self.assertEqual(s.foo, s.bar)
        self.assertEqual(s.foo, s.che)

        with self.assertRaises(AttributeError):
            s.faosdfjadkfljlk_does_not_exist

    def test_aliases_primary_key(self):
        s = self.get_schema()
        self.assertEqual(s._id, s.pk)

    def test_aliases_created_updated(self):
        orm_class = self.get_orm_class()
        s = orm_class.schema

        self.assertEqual(s._created, s.created)
        self.assertEqual(s._updated, s.updated)

        q = orm_class.query.lte_created(datetime.datetime.utcnow())
        self.assertTrue("_created" in q.fields_where)

        q = orm_class.query.lte_updated(datetime.datetime.utcnow())
        self.assertTrue("_updated" in q.fields_where)

    def test_create_orm_1(self):
        s = self.get_schema()
        o = s.create_orm()
        self.assertEqual(s, o.schema)
        self.assertEqual(s.table_name, o.table_name)
        self.assertEqual(s.fields.keys(), o().fields.keys())

    def test_create_orm_2(self):
        self.assertTrue(hasattr(Orm, "_id"))

        s = self.get_schema(_id=None)
        o = s.create_orm()

        self.assertEqual(None, o._id)
        self.assertTrue(hasattr(Orm, "_id"))


class DsnConnectionTest(BaseTestCase):
    def test_environ(self):
        os.environ['PROM_DSN'] = "prom.interface.postgres.PostgreSQL://localhost:5000/database#i0"
        os.environ['PROM_DSN_1'] = "prom.interface.postgres.PostgreSQL://localhost:5000/database#i1"
        os.environ['PROM_DSN_2'] = "prom.interface.postgres.PostgreSQL://localhost:5000/database#i2"
        os.environ['PROM_DSN_4'] = "prom.interface.postgres.PostgreSQL://localhost:5000/database#i4"
        prom.configure_environ()
        self.assertTrue('i0' in prom.get_interfaces())
        self.assertTrue('i1' in prom.get_interfaces())
        self.assertTrue('i2' in prom.get_interfaces())
        self.assertTrue('i3' not in prom.get_interfaces())
        self.assertTrue('i4' not in prom.get_interfaces())

        prom.interface.interfaces.pop('i0', None)
        prom.interface.interfaces.pop('i1', None)
        prom.interface.interfaces.pop('i2', None)
        prom.interface.interfaces.pop('i3', None)
        prom.interface.interfaces.pop('i4', None)

    def test_dsn_options_type(self):
        dsn = "prom.interface.sqlite.SQLite:///tmp/sqlite.db?timeout=20.0"
        c = DsnConnection(dsn)
        self.assertTrue(isinstance(c.options["timeout"], float))

    def test_readonly(self):
        dsn = "SQLite:///tmp/sqlite.db?readonly=1"
        c = DsnConnection(dsn)
        self.assertTrue(c.readonly)

    def test_dsn(self):
        tests = [
            (
                "prom.interface.postgres.PostgreSQL://username:password@localhost:5000/database?option=1&var=2#fragment",
                {
                    'username': "username",
                    'interface_name': "prom.interface.postgres.PostgreSQL",
                    'database': "database",
                    'host': "localhost",
                    'port': 5000,
                    'password': "password",
                    'name': 'fragment',
                    'options': {
                        'var': 2,
                        'option': 1
                    }
                }
            ),
            (
                "prom.interface.postgres.PostgreSQL://localhost:5/database2",
                {
                    'interface_name': "prom.interface.postgres.PostgreSQL",
                    'database': "database2",
                    'host': "localhost",
                    'port': 5,
                }
            ),
            (
                "prom.interface.postgres.PostgreSQL://localhost/db3",
                {
                    'interface_name': "prom.interface.postgres.PostgreSQL",
                    'database': "db3",
                    'host': "localhost",
                }
            ),
            (
                "prom.interface.postgres.PostgreSQL://localhost/db3?var1=1&var2=2&var3=true&var4=False#name",
                {
                    'interface_name': "prom.interface.postgres.PostgreSQL",
                    'database': "db3",
                    'host': "localhost",
                    'name': "name",
                    'options': {
                        'var1': 1,
                        'var2': 2,
                        'var3': True,
                        'var4': False
                    }
                }
            ),
            (
                "prom.interface.sqlite.SQLite://../this/is/the/path",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': '../this/is/the/path'
                }
            ),
            (
                "prom.interface.sqlite.SQLite://./this/is/the/path",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': './this/is/the/path'
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///this/is/the/path",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': '/this/is/the/path'
                }
            ),
            (
                "prom.interface.sqlite.SQLite://:memory:#fragment_name",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': ":memory:",
                    'name': 'fragment_name'
                }
            ),
            (
                "prom.interface.sqlite.SQLite://:memory:?option=1&var=2#fragment_name",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': ":memory:",
                    'name': 'fragment_name',
                    'options': {
                        'var': 2,
                        'option': 1
                    }
                }
            ),
            (
                "prom.interface.sqlite.SQLite://:memory:",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': ":memory:",
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///db4",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/db4",
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///relative/path/to/db/4.sqlite",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/relative/path/to/db/4.sqlite",
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///abs/path/to/db/4.sqlite",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/abs/path/to/db/4.sqlite",
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///abs/path/to/db/4.sqlite?var1=1&var2=2",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/abs/path/to/db/4.sqlite",
                    'options': {
                        'var1': 1,
                        'var2': 2
                    }
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///abs/path/to/db/4.sqlite?var1=1&var2=2#name",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/abs/path/to/db/4.sqlite",
                    'name': "name",
                }
            ),
            (
                "prom.interface.sqlite.SQLite:///abs/path/to/db/4.sqlite?var1=1&var2=2#name",
                {
                    'interface_name': "prom.interface.sqlite.SQLite",
                    'host': None,
                    'database': "/abs/path/to/db/4.sqlite",
                    'name': "name",
                    'options': {
                        'var1': 1,
                        'var2': 2
                    }
                }
            ),
        ]

        for t in tests:
            c = DsnConnection(t[0])
            for attr, val in t[1].items():
                self.assertEqual(val, getattr(c, attr))


class ConnectionTest(BaseTestCase):
    def test_interface_is_unique_each_time(self):
        c = Connection(
            interface_name="prom.interface.sqlite.SQLite",
            database=":memory:",
        )

        iids = set()
        inters = set()
        for x in range(10):
            inter = c.interface
            iid = id(inter)
            self.assertFalse(iid in iids)
            iids.add(iid)
            inters.add(inter)

    def test___init__(self):

        c = Connection(
            interface_name="prom.interface.sqlite.SQLite",
            database="dbname",
            port=5000,
            some_random_thing="foo"
        )

        self.assertEqual(5000, c.port)
        self.assertEqual("dbname", c.database)
        self.assertEqual({"some_random_thing": "foo"}, c.options)


class FieldTest(EnvironTestCase):
    def test_modified_pk(self):
        orm_class = self.get_orm_class()
        o = orm_class(foo=1, bar="2")
        f = o.schema.pk

        im = f.modified(o, 100)
        self.assertTrue(im)

        im = f.modified(o, None)
        self.assertFalse(im)

        o.save()

        im = f.modified(o, None)
        self.assertTrue(im)

        im = f.modified(o, o.pk + 1)
        self.assertTrue(im)

        im = f.modified(o, o.pk)
        self.assertFalse(im)

    def test_help(self):
        help_str = "this is the foo field"
        orm_class = self.get_orm_class(
            foo=Field(int, help=help_str)
        )

        f = orm_class.schema.foo
        self.assertEqual(help_str, f.help)

    def test_type_std(self):
        std_types = (
            bool,
            long,
            int,
            float,
            bytearray,
            decimal.Decimal,
            datetime.datetime,
            datetime.date,
        )
        if is_py2:
            std_types = (basestring,) + std_types
        else:
            std_types = basestring + std_types

        for field_type in std_types:
            f = Field(field_type)
            self.assertEqual(field_type, f.type)
            self.assertEqual(field_type, f.interface_type)
            self.assertIsNone(f.schema)
            self.assertFalse(f.is_serialized())

    def test_type_json(self):
        json_types = (
            dict,
            list,
        )

        for field_type in json_types:
            f = Field(field_type)
            self.assertEqual(field_type, f.original_type)
            self.assertEqual(str, f.interface_type)
            self.assertEqual(str, f.type)
            self.assertIsNone(f.schema)
            self.assertTrue(f.is_serialized())

    def test_type_pickle(self):
        class Foo(object): pass
        pickle_types = (
            set,
            Foo,
        )

        for field_type in pickle_types:
            f = Field(field_type)
            self.assertEqual(field_type, f.original_type)
            self.assertEqual(str, f.interface_type)
            self.assertEqual(str, f.type)
            self.assertIsNone(f.schema)
            self.assertTrue(f.is_serialized())

    def test_type_fk(self):
        orm_class = self.get_orm_class()

        f = Field(orm_class)
        self.assertEqual(orm_class, f.original_type)
        self.assertEqual(long, f.interface_type)
        self.assertEqual(long, f.type)
        self.assertIsNotNone(f.schema)
        self.assertFalse(f.is_serialized())

    def test_serialize_lifecycle(self):
        orm_class = self.get_orm_class(
            foo=Field(dict, False)
        )

        o = orm_class()
        self.assertIsNone(o.foo)

        o.foo = {"bar": 1, "che": "two"}
        self.assertTrue(isinstance(o.foo, dict))
        o.save()
        self.assertTrue(isinstance(o.foo, dict))

        o2 = o.query.eq_pk(o.pk).one()
        self.assertTrue(isinstance(o2.foo, dict))
        self.assertEqual(1, o2.foo["bar"])
        self.assertEqual("two", o2.foo["che"])

    def test_choices(self):
        orm_class = self.get_orm_class(
            foo=Field(int, choices=set([1, 2, 3]))
        )
        o = orm_class()

        for x in range(1, 4):
            o.foo = x
            self.assertEqual(x, o.foo)

        o.foo = 1
        with self.assertRaises(ValueError):
            o.foo = 4
        self.assertEqual(1, o.foo)

        o.foo = None
        self.assertEqual(None, o.foo)

    def test_iget(self):
        orm_class = self.get_orm_class(
            foo=Field(int, iget=lambda o, v: bool(v))
        )

        o = orm_class()

        o.from_interface({"foo": 1})
        self.assertTrue(o.foo)
        self.assertTrue(isinstance(o.foo, bool))

    def test_iset(self):
        dt = datetime.datetime.utcnow()
        orm_class = self.get_orm_class(
            foo=Field(int, iset=lambda o, v: datetime.datetime.utcnow())
        )

        o = orm_class()
        self.assertIsNone(o.foo)

        fields = o.to_interface()
        self.assertLess(dt, fields["foo"])

        fields2 = o.to_interface()
        self.assertLess(fields["foo"], fields2["foo"])

    def test_iquery(self):
        class IqueryOrm(Orm):
            foo = Field(int)

            @foo.iquerier
            def foo(query, v):
                return 10

        q = IqueryOrm.query.is_foo("foo")
        self.assertEqual(10, q.fields_where[0].value)

    def test_datetime_jsonable_1(self):
        class FDatetimeOrm(Orm):
            foo = Field(datetime.datetime)

        o = FDatetimeOrm()
        o.foo = datetime.datetime.min
        r = o.jsonable()
        self.assertTrue("foo" in r)

    def test_default(self):
        class FDefaultOrm(Orm):
            foo = Field(int, default=0)
            bar = Field(int)

        o = FDefaultOrm()
        foo = o.schema.foo
        self.assertEqual(0, foo.fdefault(o, None))
        self.assertEqual(0, o.foo)

        bar = o.schema.bar
        self.assertEqual(None, bar.fdefault(o, None))
        self.assertEqual(None, o.bar)

    def test_fcrud(self):

        class FCrudOrm(Orm):
            foo = Field(int)

            @foo.fsetter
            def foo(self, v):
                return 0 if v is None else v

            @foo.fgetter
            def foo(self, v):
                ret = None if v is None else v + 1
                return ret

            @foo.fdeleter
            def foo(self, val):
                return None

        o = FCrudOrm(foo=0)

        self.assertEqual(1, o.foo)
        self.assertEqual(1, o.foo)

        pk = o.save()
        self.assertEqual(2, o.foo)
        self.assertEqual(2, o.foo)

        del o.foo
        self.assertEqual(None, o.foo)
        pk = o.save()
        self.assertEqual(1, o.foo)

        o.foo = 10
        self.assertEqual(11, o.foo)
        self.assertEqual(11, o.foo)

        o.foo = None
        self.assertEqual(1, o.foo)

    def test_icrud(self):
        class ICrudOrm(Orm):
            foo = Field(int)

            @foo.isetter
            def foo(self, v):
                if self.is_update():
                    v = v - 1
                else:
                    v = 0
                return v

            @foo.igetter
            def foo(self, v):
                if v > 1:
                    v = v * 100
                return v

        o = ICrudOrm()
        self.assertEqual(None, o.foo)

        o.save()
        self.assertEqual(0, o.foo)

        o.foo = 5
        self.assertEqual(5, o.foo)

        o.save()
        self.assertEqual(400, o.foo)

        o2 = o.query.one_pk(o.pk)
        self.assertEqual(400, o2.foo)

    def test_fdel(self):
        orm_class = self.get_orm_class()

        o = orm_class()

        self.assertFalse(o.schema.fields["foo"].modified(o, o.foo))

        o.foo = 1
        self.assertTrue(o.schema.fields["foo"].modified(o, o.foo))

        del o.foo
        self.assertFalse(o.schema.fields["foo"].modified(o, o.foo))

        with self.assertRaises(KeyError):
            o.to_interface()

    def test_fdeleter(self):
        class FDOrm(Orm):
            foo = Field(int)

            @foo.fdeleter
            def foo(self, val):
                return None

        o = FDOrm()
        o.foo = 1
        del o.foo
        self.assertEqual(None, o.foo)

    def test_property(self):
        class FieldPropertyOrm(Orm):
            foo = Field(int)

            @foo.fgetter
            def foo(self, val):
                return val

            @foo.fsetter
            def foo(self, val):
                return int(val) + 10 if (val is not None) else val

        o = FieldPropertyOrm()

        o.foo = 1
        self.assertEqual(11, o.foo)

        o.foo = 2
        self.assertEqual(12, o.foo)

        o.foo = None
        self.assertEqual(None, o.foo)

    def test_ref(self):
        m = testdata.create_module([
            "import prom",
            "class Foo(prom.Orm):",
            "    che = prom.Field(str)",
            "",
            "class Bar(prom.Orm):",
            "    foo_id = prom.Field(Foo)",
            ""
        ])

        Foo = m.module().Foo
        Bar = m.module().Bar

        self.assertTrue(isinstance(Bar.schema.fields['foo_id'].schema, Schema))
        self.assertTrue(issubclass(Bar.schema.fields['foo_id'].interface_type, long))

    def test_string_ref(self):
        modname = testdata.get_module_name()
        d = testdata.create_modules({
            "foo": [
                "import prom",
                "class Foo(prom.Orm):",
                "    interface = None",
                "    bar_id = prom.Field('{}.bar.Bar')".format(modname),
                ""
            ],
            "bar": [
                "import prom",
                "class Bar(prom.Orm):",
                "    interface = None",
                "    foo_id = prom.Field('{}.foo.Foo')".format(modname),
                ""
            ],
        }, modname)

        Foo = d.module("{}.foo".format(modname)).Foo
        Bar = d.module("{}.bar".format(modname)).Bar

        self.assertTrue(isinstance(Foo.schema.fields['bar_id'].schema, Schema))
        self.assertTrue(issubclass(Foo.schema.fields['bar_id'].interface_type, long))
        self.assertTrue(isinstance(Bar.schema.fields['foo_id'].schema, Schema))
        self.assertTrue(issubclass(Bar.schema.fields['foo_id'].interface_type, long))

    def test___init__(self):
        f = Field(str, True)
        self.assertTrue(f.required)
        self.assertTrue(issubclass(f.type, str))

        with self.assertRaises(TypeError):
            f = Field()

        f = Field(int, max_length=100)
        self.assertTrue(issubclass(f.type, int))
        self.assertEqual(f.options['max_length'], 100)


class SerializedFieldTest(EnvironTestCase):
    def get_orm(self, field_type=dict, default=None):
        orm_class = self.get_orm_class(
            body=Field(field_type, default=default)
        )
        return orm_class()

    def test_default(self):
        o = self.get_orm(default=dict)
        o.body["foo"] = 1
        self.assertEqual(1, o.body["foo"])

    def test_imethods_pickle(self):
        o = self.get_orm()
        o.body = {"foo": 1}
        o.save()

        o2 = o.requery()
        self.assertEqual(o.body, o2.body)

    def test_modify(self):
        o = self.get_orm()
        o.body = {"bar": 1}
        o.save()

        o.body["che"] = 2
        o.save()

        o2 = o.requery()
        self.assertEqual(o.body, o2.body)

    def test_other_types(self):
        types = (
            list,
            set
        )

        for field_type in types:
            o = self.get_orm(field_type)
            o.body = field_type(range(100))
            o.save()

            o2 = o.requery()
            self.assertEqual(o.body, o2.body)

