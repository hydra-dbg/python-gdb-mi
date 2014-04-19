The output of the GDB Machine Interface is compound of small elements
The most basic are the c-strings. As all the objects that can be found in
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
   >>> print s
   'fooo'

The *parse* method take two arguments, the full raw string and the offset where
to start read from it and parse it.
The result of this method is the updated offset.
After the correct parsing, the as_native method will return the simple python objects
representing the data parsed.

In the case of the c-string, the returned native object is, of course, a string.

Note that the c-string expect as a valid input a string like in C, starting with double
quote.

Any incorrect input will raise an exception

::
   
   >>> s.parse('xxx', 0)
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a double quote '"'.

   >>> s.parse('"f...', 0)
   Traceback (most recent call last):
   ParsingError: End of input found without close the c-string. Expecting a '"'.

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

With the c-string implemented, more complex objects can be built like lists or tuples (dicts)

::

   >>> l = List()
   >>> l.parse(r'[]', 0)
   2
   >>> l.as_native()
   []
   >>> print l
   []

   >>> l.parse(r'["a"]', 0)
   5
   >>> l.as_native()
   ['a']
   >>> print l
   ['a']

   >>> l.parse(r'["a","b"]', 0)
   9
   >>> l.as_native()
   ['a', 'b']
   >>> print l
   ['a', 'b']

::
   
   >>> t = Tuple()
   >>> t.parse(r'{}', 0)
   2
   >>> t.as_native()
   {}
   >>> print t
   {}

   >>> t.parse(r'{a="b"}', 0)
   7
   >>> t.as_native()
   {'a': 'b'}
   >>> print t
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
   >>> print t
   {'a': {'b': 'c'}}

   >>> t.parse(r'{a="b",c="d"}', 0)
   13
   >>> sorted(t.as_native().iteritems()) # we 'sort' the dictionary to make easy the testing
   [('a', 'b'), ('c', 'd')]
   >>> print t
   {'a': 'b', 'c': 'd'}


The ugly part of the tuples are the possibility of repeated keys.
In that case, the set of values with the same key are merged into a single entry 
in the dictionary and its value will be the list of the original values.

::
   >>> t = Tuple()
   >>> t.parse(r'{a="b",a="d"}', 0)
   13
   >>> t.as_native()
   {'a': ['b', 'd']}
   >>> print t
   {'a': ['b', 'd']}

Of course, wrong inputs are catched

::

   >>> l = List()

   >>> l.parse(r'["x"', 0)
   Traceback (most recent call last):
   ParsingError: End of input found without close the list. Expecting a ']'.

   >>> l.parse(r'"xxx"]', 0)
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a '['.
   
::
   >>> t = Tuple()

   >>> t.parse(r'{x', 0)
   Traceback (most recent call last):
   ParsingError: Token '=' not found.

   >>> t.parse(r'{x=', 0)
   Traceback (most recent call last):
   ParsingError: End of input.

   >>> t.parse(r'{x=}', 0)
   Traceback (most recent call last):
   UnexpectedToken: Unexpected token '}'.

   >>> t.parse(r'{=xx}', 0)
   Traceback (most recent call last):
   UnexpectedToken: Unexpected token 'x'.

   >>> t.parse(r'{xx}', 0)
   Traceback (most recent call last):
   ParsingError: Token '=' not found.

   >>> t.parse(r'xx}', 0)
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a '{'.

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
   >>> print record
   {'klass': 'foo', 'results': {}, 'token': None, 'type': 'Exec'}

   >>> r.parse('+bar,a="b"\n', 0)
   10
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('bar', 'Status', {'a': 'b'})
   >>> print record
   {'klass': 'bar', 'results': {'a': 'b'}, 'token': None, 'type': 'Status'}

   >>> r.parse('=baz,a=[],b={c="d"}\n', 0)
   19
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('baz', 'Notify', {'a': [], 'b': {'c': 'd'}})
   >>> print record                          #doctest: +NORMALIZE_WHITESPACE
   {'klass': 'baz', 
    'results': {'a': [], 'b': {'c': 'd'}}, 
    'token': None, 
    'type': 'Notify'}
   
::
   >>> r = ResultRecord()
   >>> r.parse('^bar,a="b"\n', 0)
   10
   >>> record = r.as_native()
   >>> record.klass, record.type, record.results
   ('bar', 'Sync', {'a': 'b'})
   >>> print record
   {'klass': 'bar', 'results': {'a': 'b'}, 'token': None, 'type': 'Sync'}

The other top level construction are the Stream. These are unstructured c-strings.

::
   >>> s = StreamRecord()
   >>> s.parse('~"foo"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Console', 'foo')
   >>> print stream
   {'stream': 'foo', 'type': 'Console'}

   >>> s.parse('@"bar"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Target', 'bar')
   >>> print stream
   {'stream': 'bar', 'type': 'Target'}

   >>> s.parse('&"baz"\n', 0)
   6
   >>> stream = s.as_native()
   >>> stream.type, stream.stream
   ('Log', 'baz')
   >>> print stream
   {'stream': 'baz', 'type': 'Log'}

Finally, the messages returned by GDB are a sequence (may be empty) of asynchronious 
messages and streams, followed by an optional result record. Then, the special token
'(gdb)' should be found, followed by a newline.

Instead of delivery these big messages one by one, the Output parser will deliver
each asynchronious message / stream / result separately.

::
   >>> o = Output()
   
   >>> text = '(gdb) \n'  #the extra space is not specified in GDB's docs but it's necessary
   >>> o.parse_line(text)
   '(gdb)'

   >>> text = '~"foo"\n'
   >>> stream = o.parse_line(text)
   >>> stream.type, stream.stream
   ('Console', 'foo')
   >>> print stream
   {'stream': 'foo', 'type': 'Console'}


For example, this is the message after setting a breakpoint

::
   >>> o = Output()

   >>> text = '^done,bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="0x08048564",func="main",file="myprog.c",fullname="/home/nickrob/myprog.c",line="68",thread-groups=["i1"],times="0"}\n'
   >>> record = o.parse_line(text)
   >>> record.klass, record.type
   ('done', 'Sync')
   >>> len(record.results)
   1
   >>> sorted(record.results['bkpt'].iteritems())
   [('addr', '0x08048564'), ('disp', 'keep'), ('enabled', 'y'), ('file', 'myprog.c'), ('fullname', '/home/nickrob/myprog.c'), ('func', 'main'), ('line', '68'), ('number', '1'), ('thread-groups', ['i1']), ('times', '0'), ('type', 'breakpoint')]
   >>> print record                       #doctest: +NORMALIZE_WHITESPACE
   {'klass': 'done',
    'results': {'bkpt': {'addr': '0x08048564',
                         'disp': 'keep',
                         'enabled': 'y',
                         'file': 'myprog.c',
                         'fullname': '/home/nickrob/myprog.c',
                         'func': 'main',
                         'line': '68',
                         'number': '1',
                         'thread-groups': ['i1'],
                         'times': '0',
                         'type': 'breakpoint'}},
    'token': None,
    'type': 'Sync'}


Or, when a execution is stopped

::
   >>> o = Output()

   >>> text = '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
   >>> record = o.parse_line(text)
   >>> record.klass, record.type
   ('stopped', 'Exec')
   >>> len(record.results)
   5
   >>> record.results['reason'], record.results['disp'], record.results['bkptno'], record.results['thread-id']
   ('breakpoint-hit', 'keep', '1', '0')
   >>> print record                       #doctest: +NORMALIZE_WHITESPACE
   {'klass': 'stopped',
   'results': {'bkptno': '1',
               'disp': 'keep',
               'frame': {'addr': '0x08048564',
                         'args': [{'name': 'argc', 'value': '1'},
                                  {'name': 'argv', 'value': '0xbfc4d4d4'}],
                         'file': 'myprog.c',
                         'fullname': '/home/nickrob/myprog.c',
                         'func': 'main',
                         'line': '68'},
               'reason': 'breakpoint-hit',
               'thread-id': '0'},
   'token': None,
   'type': 'Exec'}

   >>> frame = record.results['frame']
   >>> frame['addr'], frame['func'], frame['file'], frame['fullname'], frame['line']
   ('0x08048564', 'main', 'myprog.c', '/home/nickrob/myprog.c', '68')

   >>> main_args = frame['args']
   >>> main_args[0]['name'], main_args[0]['value']
   ('argc', '1')
   >>> main_args[1]['name'], main_args[1]['value']
   ('argv', '0xbfc4d4d4')

