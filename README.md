# Prom

An opinionated lightweight orm for Postgres

## Example -- Create a User class

Prom tries to make it as easy as possible on the developer to set common options, so you don't have to constantly look at the documentation until you need to change something significant.

Here is how you would define a new Orm class:

```python
# app.models (app/models.py)
import prom

class User(prom.Orm):

    schema = prom.Schema(
        "user_table_name", # the db table name
        username=(str, True), # string field (required)
        password=(str, True), # string field (required)
        email=(str,), # string field (not required)
        unique_user=('username',) # set a unique index on username field
        index_email=('email',) # set a normal index on email field
    )
```

You can specify the connection using a prom dsn url:

    <full.python.path.InterfaceClass>://<username>:<password>@<host>:<port>/<database>?<options=val&query=string>#<name>

So to use the builtin Postgres interface on `testdb` database on host `localhost` with username `testuser` and password `testpw`:

    prom.interface.postgres.Interface://testuser:testpw@localhost/testdb

To use our new User class:

```python
# testprom.py
import prom
from app.models import User

prom.configure("prom.interface.postgres.Interface://testuser:testpw@localhost/testdb")

# create a user
u = User(username='foo', password='awesome_and_secure_pw_hash', email='foo@bar.com')
u.set()

# query for our new user
u = User.query.is_username('foo').get_one()
print u.username # foo

# get the user again via the primary key:
u2 = User.query.get_pk(u.pk)
print u.username # foo

# let's add a bunch more users:
for x in xrange(10):
    username = "foo{}".format(x)
    ut = User(username=username, password="...", email="{}@bar.com".format(username))
    ut.set()

# now let's iterate through all our new users:
for u in User.query.get():
    print u.username
```

## The Query class

You can access the query, or table, instance for each `prom.Orm` child you create by calling its `.query` class property:

```python
print User.query # prom.Query
```

Through the power of magic, everytime you call this property, a new `prom.Query` instance will be created.

### Customize the Query class

By default, Prom will look for a `<name>Query` class in the same module as your `prom.Orm` child, so, continuing the User example from above, if you wanted to make a custom `UserQuery` class:

```python
# app.models (app/models.py)

class UserQuery(prom.Query):
    def get_by_emails(self, *emails):
        """get all users with matching emails, ordered by last updated first"""
        return self.in_email(*emails).desc_updated().get()
```

Now, we can further use the power of magic:

```python
print User.query # app.models.UserQuery
```

And boom, we were able to customize our queries by just adding a class. If you want to explicitely set the class your `prom.Orm` child should use (eg, you want all your models to use `random.module.CustomQuery` which wouldn't be auto-discovered by prom), you can set the `query_class` class property to whatever you want:

```python
class DemoOrm(prom.Orm):
    query_class = random.module.CustomQuery
```

and then every instance of `DemoOrm` (or child that derives from it) will forever use `random.module.CustomQuery`.

### Using the Query class

You should check the actual code for the query class in `prom.query.Query` for all the methods you can use to create your queries, Prom allows you to set up the query using psuedo method names in the form:

    command_fieldname(field_value)

So, if you wanted to select on the `foo` fields, you could do:

```python
query.is_foo(5)
```

or, if you have the name in the field as a string:

    command_field(fieldname, field_value)

so, we could also select on `foo` this way:

```python
name = 'foo'
query.is_field(name, 5)
```

The different WHERE commands:

  * `in` -- `in_field(fieldname, *field_vals)` -- do a sql `fieldname IN (field_val1, ...)` query
  * `nin` -- `nin_field(fieldname, *field_vals)` -- do a sql `fieldname NOT IN (field_val1, ...)` query
  * `is` -- `is_field(fieldname, field_val)` -- do a sql `fieldname = field_val` query
  * `not` -- `not_field(fieldname, field_val)` -- do a sql `fieldname != field_val` query
  * `gt` -- `gt_field(fieldname, field_val)` -- do a sql `fieldname > field_val` query
  * `gte` -- `gte_field(fieldname, field_val)` -- do a sql `fieldname >= field_val` query
  * `lt` -- `lt_field(fieldname, field_val)` -- do a sql `fieldname < field_val` query
  * `lte` -- `lte_field(fieldname, field_val)` -- do a sql `fieldname <= field_val` query

The different ORDER BY commands:

  * `asc` -- `asc_field(fieldname)` -- do a sql `ORDER BY fieldname ASC` query
  * `desc` -- `desc_field(fieldname)` -- do a sql `ORDER BY fieldname DESC` query

And you can also set limit and page in the get query:

```python
query.get(10, 1) # get 10 results for page 1 (offset 0)
query.get(10, 2) # get 10 results for page 2 (offset 10)
```

They can be changed together:

```python
# SELECT * from table_name WHERE foo=10 AND bar='value 2' ORDER BY che DESC LIMIT 5
query.is_foo(10).is_bar("value 2").desc_che().get(5)
```

You can also write your own queries by hand:

```python
query.get_query("SELECT * FROM table_name WHERE foo = %s", [foo_val])
```

The `prom.Query` has a couple helpful query methods to make grabbing rows easy:

  * `get` -- `get(limit=None, page=None)` -- run the select query.
  * `get_one` -- `get_one()` -- run the select query with a LIMIT 1.
  * `has` -- `has()` -- return True if there is atleast one row in the db matching query
  * `get_pk` -- `get_pk(pk)` -- run the select query with a `WHERE _id = pk`
  * `get_query` -- `get_query(query_str, *query_args, **query_options)` -- run a raw query
  * `all` -- `all()` -- return an iterator that can move through every row in the db matching query

**NOTE**, Doing custom queries using `get_query` would be the only way to do join queries.

### The Iterator class

the `get` and `all` query methods return a `prom.query.Iterator` instance. This instance has a useful attribute `has_more` that will be true if there are more rows in the db that match the query.

## Multiple db interfaces or connections

It's easy to have one set of `prom.Orm` children use one connection and another set use a different connection, the fragment part of a Prom dsn url sets the name:

```python
import prom
prom.configure("Interface://testuser:testpw@localhost/testdb#connection_1")
prom.configure("Interface://testuser:testpw@localhost/testdb#connection_2")

class Orm1(prom.Orm):
    connection_name = "connection_1"
  
class Orm2(prom.Orm):
    connection_name = "connection_2"
```

Now, any class that extends `Orm1` will use `connection_1` and any orm that extends `Orm2` will use `connection_2`.

## Using for the first time

Prom takes the approach that you don't want to be hassled with installation while developing, so when it tries to do something and sees that the table doesn't exist, it will use your defined `prom.Schema` for your `prom.Orm` child and create a table for you, that way you don't have to remember to run a script or craft some custom db query to add your tables, Prom takes care of that for you automatically.

If you want to install the tables manually, you can create a script or something and use the `install()` method:

    SomeOrm.install()

## Schema class

### Foreign Keys

You can have a field reference the primary key of another field:

```python
s1 = prom.Schema(
    "table_1",
    foo=(int,)
)

s2 = prom.Schema(
    "table_2",
    s1_id=(int, True, dict(ref=s1))
)
```

the `ref` option creates a strong reference, which will delete the row from `s2` if the row from `s1` is deleted, if you would rather have the `s1_id` just set to None you can use the `weak_ref` option:

```python
s2 = prom.Schema(
    "table_2",
    s1_id=(int, False, dict(weak_ref=s1))
)
```

## Other things

Prom has a very similar interface to [Mingo](https://github.com/Jaymon/Mingo).

I built Prom because I didn't feel like Python had a good "get out of your way" relational db orm that wasn't tied to some giant framework or that didn't try to be all things to all people.

Prom is really super beta right now, built for [First Opinion](http://firstopinion.co/).

Prom assumes you want to do certain things, and so it tries to make those things really easy to do, while assuming you don't want to do things like `JOIN` queries, so those are harder to do.

## Installation

Prom currently requires psycopg2 since it only works with Postgres right now:

    $ apt-get install libpq-dev python-dev
    $ pip install psycopg

Then you can also use pip to install Prom:

    $ pip install prom

## License

MIT

## Todo

### Schema installation queries

You could do something like this:

    s = prom.Schema(
      "table_name"
      field_name=(int, required_bool, options_dict),
      "CREATE INDEX foo ON table_name USING BTREE (field_name)",
      "INSERT INTO table_name (field_name) VALUES ('some value)"
    )

That way you can do crazy indexes and maybe add an admin user or something. I don't know if I Like the syntax, but it's the best I've come up with to allow things like creating statement indexes on the month and day of a timestamp index for example.

