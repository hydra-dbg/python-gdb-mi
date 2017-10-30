Python GDB MI Parser: objects
=============================

The following doctests shows the different `Machine Inteface`_ objects that
GDB can write to its output in a line, text based way.

C-Strings
---------

The most basic elements are the `c-strings`_. As all the objects that can be found in
`python-gdb-mi`, the c-string objects support parse a raw string and transform it
into a python-native object::
 
   >>> import pprint
   >>> from gdb_mi import *
   >>> 
   >>> s = CString()
   >>> s.parse('"fooo"', 0)
   6
   >>> s.as_native()
   'fooo'
   >>> print(s)
   'fooo'

The `parse` method takes two arguments, the full raw string and the offset where
to start read from it and parse it and the result of this method is the updated 
offset.

After the correct parsing, the `as_native` method will return the simple python 
objects representing the data parsed using strings, numbers, lists and 
dictionaries which they are perfect for serialization as JSON or other text formats.

In the case of the c-string, the returned native object is, of course, a string.

Note that the c-string expect as a valid input a string like in C, starting with double
quote.

Any incorrect input will raise an exception::
   
   >>> s.parse('xxx', 0)                     #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a double quote '"'...
   
   >>> s.parse('"f...', 0)                   #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: End of input found without close the c-string. Expecting a '"'...

The c-string support any valid string with the correct escape sequences::
   
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

With the c-string implemented, more complex objects can be built like lists or 
tuples (python's dicts)

Lists
-----

Represent an ordered sequence of items or `list`_. In python they are represented as
naive lists::

   >>> l = List()
   >>> l.parse(r'[]', 0)
   2
   >>> l.as_native()
   []
   >>> print(l) # same as pprint.pprint(l.as_native())
   []

   >>> l.parse(r'["a"]', 0)
   5
   >>> l.as_native()
   ['a']
   >>> l        # same as print(l)
   ['a']

   >>> l.parse(r'["a","b"]', 0)
   9
   >>> l.as_native()
   ['a', 'b']
   >>> l
   ['a', 'b']
   
   >>> l.parse(r'["x"', 0)                   #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: End of input found without close the list. Expecting a ']'...

   >>> l.parse(r'"xxx"]', 0)                 #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a '['...

Tuples (aka Python's dicts)
---------------------------

A GDB's `tuple`_ is a key-value mapping. `python-gdb-mi` will take these
and it will transform them into native Python's dictionary::
   
   >>> t = Tuple()
   >>> t.parse(r'{}', 0)
   2
   >>> t.as_native()
   {}
   >>> t
   {}

   >>> t.parse(r'{a="b"}', 0)
   7
   >>> t  # same as pprint.pprint(t.as_native())
   {'a': 'b'}

   >>> t.parse(r'{a=[]}', 0)
   6
   >>> t
   {'a': []}

   >>> t.parse(r'{a=["a","b"]}', 0)
   13
   >>> t
   {'a': ['a', 'b']}

   >>> t.parse(r'{a={b="c"}}', 0)
   11
   >>> t
   {'a': {'b': 'c'}}

   >>> t.parse(r'{a="b",c="d"}', 0)
   13
   >>> t
   {'a': 'b', 'c': 'd'}


The ugly part of the tuples are the possibility of repeated keys.

In that case, the set of values with the same key are merged into a single entry
in the dictionary and its value will be the list of the original values::

   >>> t = Tuple()
   >>> t.parse(r'{a="b",a="d"}', 0)
   13
   >>> t
   {'a': ['b', 'd']}

Of course, wrong inputs are caught::

   >>> t.parse(r'{x', 0)                     #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: Token '=' not found...

   >>> t.parse(r'{x=', 0)                    #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: End of input...

   >>> t.parse(r'{x=}', 0)                   #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   UnexpectedToken: Unexpected token '}'...

   >>> t.parse(r'{=xx}', 0)                  #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   UnexpectedToken: Unexpected token 'x'...

   >>> t.parse(r'{xx}', 0)                   #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: Token '=' not found...

   >>> t.parse(r'xx}', 0)                    #doctest: +IGNORE_EXCEPTION_DETAIL
   Traceback (most recent call last):
   ParsingError: Wrong begin. Expected a '{'...


Asynchronous Records
--------------------

The `asynchronious records`_ are emitted by GDB to notify about changes that
happen like a breakpoint hit::

   >>> r = AsyncRecord()
   >>> r.parse('*foo\n', 0)
   4
   >>> r    # again, this is the same as pprint.pprint(r.as_native())
   {'klass': 'foo', 'results': {}, 'token': None, 'type': 'Exec'}

   >>> r.parse('+bar,a="b"\n', 0)
   10
   >>> r
   {'klass': 'bar', 'results': {'a': 'b'}, 'token': None, 'type': 'Status'}

   >>> r.parse('=baz,a=[],b={c="d"}\n', 0)
   19
   >>> r                                     #doctest: +NORMALIZE_WHITESPACE
   {'klass': 'baz', 
    'results': {'a': [], 'b': {'c': 'd'}}, 
    'token': None, 
    'type': 'Notify'}
   
Result Records (Sync)
---------------------

Synchronous `result records`_ of a GDB command::

   >>> r = ResultRecord()
   >>> r.parse('^bar,a="b"\n', 0)
   10
   >>> r
   {'klass': 'bar', 'results': {'a': 'b'}, 'token': None, 'type': 'Sync'}

Stream Records
--------------

The other top level construction are the Stream. These are unstructured c-strings
named `stream records`_::

::
   >>> s = StreamRecord()
   >>> s.parse('~"foo"\n', 0)
   6
   >>> s
   {'stream': 'foo', 'type': 'Console'}

   >>> s.parse('@"bar"\n', 0)
   6
   >>> s
   {'stream': 'bar', 'type': 'Target'}

   >>> s.parse('&"baz"\n', 0)
   6
   >>> s # again, this is a shortcut for pprint.pprint(s.as_native())
   {'stream': 'baz', 'type': 'Log'}

Output
------

Finally, the messages returned by GDB are a sequence (may be empty) of asynchronous 
messages and streams, followed by an optional result record. Then, the special token
'(gdb)' should be found, followed by a newline.

Instead of delivery these sequence of messages in one shot, the `Output` parser 
will deliver each asynchronous message / stream / result separately.

Call `parse_line` to parse a full GDB MI message to retrieve the parsed object::

   >>> o = Output()
   
   >>> text = '(gdb) \n'  #the extra space is not specified in GDB's docs but it's necessary
   >>> o.parse_line(text)
   '(gdb)'

   >>> text = '~"foo"\n'
   >>> stream = o.parse_line(text)
   >>> print(stream)
   {'stream': 'foo', 'type': 'Console'}

Call `parse` to feed the parser with a partial GDB MI message. If enough data is given,
it will return the parsed object like parse_line. If not, it will return None::

   >>> text = '~"bar"\n'
   >>> o.parse(text[:3])  # incomplete, return None

   >>> stream = o.parse(text[3:])  # feed the rest of the message, return the parsed object
   >>> print(stream)
   {'stream': 'bar', 'type': 'Console'}


As an example, this is the message when a execution is stopped::

   >>> o = Output()

   >>> text = '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
   >>> record = o.parse_line(text)
   >>> record.klass, record.type
   ('stopped', 'Exec')
   >>> len(record.results)
   5
   >>> record.results['reason'], record.results['disp'], record.results['bkptno'], record.results['thread-id']
   ('breakpoint-hit', 'keep', '1', '0')
   >>> print(record)                         #doctest: +NORMALIZE_WHITESPACE
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



.. _Machine Interface: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI.html
.. _c-strings: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Input-Syntax.html#GDB_002fMI-Input-Syntax
.. _list: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax
.. _tuple: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax
.. _stream records: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Stream-Records.html#GDB_002fMI-Stream-Records
.. _result records: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records
.. _asynchronious records: https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Async-Records.html#GDB_002fMI-Async-Records
