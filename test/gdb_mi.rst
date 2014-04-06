The output of the GDB Machine Interface is compound of small elements
The most basic are the c-string. As all the objects that can be found in
gdb_mi, the c-string objects support parse a raw string and transform it
into a python-native object.

::
   
   >>> from gdb.gdb_mi import *
   >>> 
   >>> s = CString()
   >>> s.parse('"fooo"', 0)
   6
   >>> s.as_native()
   'fooo'

The method *parse* take two arguments, the full raw string and the offset where
start to read from it and parse it.
The result of this method is the updated offset.
After the correct parsing, the method as_native will return the simple python objects
representing the data parsed.

In the case of the c-string, the returned native object is, of course, a string.

Note that the c-string expect as a valid input a string like in C, starting with double
quote.

Any incorrect input will raise an exception

::
   
   >>> s.parse('xxx', 0)
   >>> s.parse('"f...', 0)

The c-string support any valid string with the correct escape sequences

::
   
   >>> s.parse('""', 0)
   2
   >>> s.as_native()
   ''

   >>> s.parse(r'"\n"', 0)
   4
   >>> s.as_native()
   '\n'

   >>> s.parse(r'"\\\n"', 0)
   6
   >>> s.as_native()
   '\\\n'

   >>> s.parse(r'"\ \n"', 0)
   6
   >>> s.as_native()
   '\\ \n'

With the c-string implemented, more complex can be built like lists or tuples (dicts)

::

   >>> l = List()
   >>> l.parse(r'[]', 0)
   2
   >>> l.as_native()
   []

   >>> l.parse(r'["a"]', 0)
   5
   >>> l.as_native()
   ['a']

   >>> l.parse(r'["a","b"]', 0)
   9
   >>> l.as_native()
   ['a', 'b']

::
   
   >>> t = Tuple()
   >>> t.parse(r'{}', 0)
   2
   >>> t.as_native()
   {}

   >>> t.parse(r'{a="b"}', 0)
   7
   >>> t.as_native()
   {'a': 'b'}

   >>> t.parse(r'{a=[]}', 0)
   6
   >>> t.as_native()
   {'a': []}

   >>> t.parse(r'{a=["a","b"]}', 0)
   13
   >>> t.as_native()
   {'a': ['a', 'b']}

   >>> t.parse(r'{a={b="c"}}', 0)
   11
   >>> t.as_native()
   {'a': {'b': 'c'}}

   >>> t.parse(r'{a="b",c="d"}', 0)
   13
   >>> sorted(t.as_native().iteritems()) # we 'sort' the dictionary to make easy the testing
   [('a', 'b'), ('c', 'd')]


Of course, wrong inputs are catched

::

   >>> l = List()
   >>> l.parse(r'["x"', 0)
   >>> l.parse(r'"xxx"]', 0)
   
::
   >>> t = Tuple()
   >>> t.parse(r'{x', 0)
   >>> t.parse(r'{x=', 0)
   >>> t.parse(r'{x=}', 0)
   >>> t.parse(r'{=xx}', 0)
   >>> t.parse(r'{xx}', 0)
   >>> t.parse(r'xx}', 0)

At the top most of the construction, the structured messages returned by GDB are 
AsyncRecords and ResultRecord.
Both are a named list (possibly empty) of key-value pairs where each value 
can be a c-string, a list or a tuple, endig the list with a newline.

::

   >>> r = AsyncRecord()
   >>> r.parse('*foo\n', 0)
   4
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('foo', 'Exec', {})

   >>> r.parse('+bar,a="b"\n', 0)
   10
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('bar', 'Status', {'a': 'b'})

   >>> r.parse('=baz,a=[],b={c="d"}\n', 0)
   19
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('baz', 'Notify', {'a': [], 'b': {'c': 'd'}})
   
::
   >>> r = ResultRecord()
   >>> r.parse('^bar,a="b"\n', 0)
   10
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('bar', 'Sync', {'a': 'b'})

The other top level construction are the Stream. These are unstructured c-strings.

::
   >>> s = StreamRecord()
   >>> s.parse('~"foo"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Console', 'foo')

   >>> s.parse('@"bar"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Target', 'bar')

   >>> s.parse('&"baz"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Log', 'baz')

