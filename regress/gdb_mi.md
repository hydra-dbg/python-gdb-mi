# Python GDB MI Parser: objects

The following doctests shows the different
[Machine Interface](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI.html)
objects that GDB can write to its output in a line, text based way.

## C-Strings

The most basic elements are the
[c-strings](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Input-Syntax.html#GDB_002fMI-Input-Syntax).
As all the objects that can be found in
``python-gdb-mi``, the c-string object supports parse a raw string and
transform it into a python-native object:

```python
>>> import pprint
>>> from gdb_mi import *

>>> s = CString()
>>> s.parse('"fooo"', 0)
6

>>> s.as_native()
'fooo'

>>> s
'fooo'

>>> isinstance(s.as_native(), bytes)
False
```

The ``parse`` method takes two arguments, the full raw string
and the offset where to start read from it and parse it and the result
of this method is the updated offset.

After the correct parsing, the ``as_native`` method will
return the simple python objects representing the data parsed using strings,
numbers, lists and dictionaries which they are perfect for serialization as
JSON or other text formats.

In the case of the c-string, the returned native object is, of course, a string
(``str`` object in Python 3.x parlance).

For Python 3.x that means that if you want to get bytes you need to do
the encoding yourself:

```python
>>> t = s.as_native().encode('ascii')
>>> isinstance(t, bytes)
True

>>> t
'fooo'
```

Note that the c-string expects as a valid input a string like in C,
starting with double quote.

Any incorrect input will raise an exception:

```python
>>> s.parse('xxx', 0)
Traceback (most recent call last):
<...>ParsingError: Wrong begin. Expected a double quote '"'<...>

>>> s.parse('"f...', 0)
Traceback (most recent call last):
<...>ParsingError: End of input found without close the c-string. Expecting a '"'<...>
```

The c-string supports any valid string with the correct escape sequences:

```python
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
```

With the c-string implemented, more complex objects can be built
like lists or tuples (python's dictionaries)

## Lists

Represent an ordered sequence of items or
[list](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax).

In python they are represented as naive lists:

```python
>>> l = List()
>>> l.parse(r'[]', 0)
2
>>> l.as_native()
[]
>>> print(l)
[]

>>> l.parse(r'["a"]', 0)
5
>>> l.as_native()
['a']
>>> l
['a']

>>> l.parse(r'["a","b"]', 0)
9
>>> l.as_native()
['a', 'b']
>>> l
['a', 'b']

>>> l.parse(r'["x"', 0)
Traceback (most recent call last):
<...>ParsingError: End of input found without close the list. Expecting a ']'<...>

>>> l.parse(r'"xxx"]', 0)
Traceback (most recent call last):
<...>ParsingError: Wrong begin. Expected a '['<...>
```

## Tuples (aka Python's dictionaries)

A GDB's
[tuple](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax)
is a key-value mapping. ``python-gdb-mi`` will take these
and it will transform them into native Python's dictionary:

```python
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
```

The **ugly part** of the tuples are the possibility of **repeated keys**.

In that case, the set of values with the same key are merged into a single entry
in the dictionary and its value will be the list of the original values:

```python
>>> t = Tuple()
>>> t.parse(r'{a="b",a="d"}', 0)
13
>>> t
{'a': ['b', 'd']}
```

Of course, wrong inputs are caught:


```python
>>> t.parse(r'{x', 0)
Traceback (most recent call last):
<...>ParsingError: Token '=' not found<...>

>>> t.parse(r'{x=', 0)
Traceback (most recent call last):
<...>ParsingError: End of input<...>

>>> t.parse(r'{x=}', 0)
Traceback (most recent call last):
<...>UnexpectedToken: Unexpected token '}'<...>

>>> t.parse(r'{=xx}', 0)
Traceback (most recent call last):
<...>UnexpectedToken: Unexpected token 'x'<...>

>>> t.parse(r'{xx}', 0)
Traceback (most recent call last):
<...>ParsingError: Token '=' not found<...>

>>> t.parse(r'xx}', 0)
Traceback (most recent call last):
<...>ParsingError: Wrong begin. Expected a '{'<...>
```

## Asynchronous Records

The [asynchronous records](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Async-Records.html#GDB_002fMI-Async-Records)
are emitted by GDB to notify about changes that happen like a breakpoint hit:

```python
>>> r = AsyncRecord()
>>> r.parse('*foo\n', 0)
4
>>> r    # again, this is the same as pprint.pprint(r.as_native())
{'class': 'foo', 'token': None, 'type': 'Exec'}

>>> r.is_async()
True
>>> r.is_async(of_type='Exec')
True
>>> r.is_async(of_type='Status')
False
>>> r.is_async(of_type=('Status', 'Exec'))
True

>>> r.parse('+bar,a="b"\n', 0)
10
>>> r
{'a': 'b', 'class': 'bar', 'token': None, 'type': 'Status'}

>>> r.parse('=baz,a=[],b={c="d"},type="z"\n', 0)
28
>>> r
{'_type': 'z',
 'a': [],
 'b': {'c': 'd'},
 'class': 'baz',
 'token': None,
 'type': 'Notify'}
```

## Result Records (Sync)

Synchronous [result records](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records)
of a GDB command:

```python
>>> r = ResultRecord()
>>> r.parse('^bar,a="b",token="32"\n', 0)
21
>>> r
{'_token': '32', 'a': 'b', 'class': 'bar', 'token': None, 'type': 'Sync'}

>>> r.is_result()
True
>>> r.is_result(of_class='bar')
True
>>> r.is_result(of_class='zaz')
False
>>> r.is_result(of_class=('zaz', 'bar'))
True
```

## Stream Records

The other top level construction are the ``Stream``. These are unstructured c-strings
named [stream records](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Stream-Records.html#GDB_002fMI-Stream-Records):


```python
>>> s = StreamRecord()
>>> s.parse('~"foo"\n', 0)
6
>>> s
{'type': 'Console', 'value': 'foo'}

>>> s.parse('@"bar"\n', 0)
6
>>> s
{'type': 'Target', 'value': 'bar'}

>>> s.parse('&"baz"\n', 0)
6
>>> s # again, this is a shortcut for pprint.pprint(s.as_native())
{'type': 'Log', 'value': 'baz'}

>>> s.is_stream()
True
>>> s.is_stream(of_type='Log')
True
>>> s.is_stream(of_type='Console')
False
>>> s.is_stream(of_type=('Console', 'Log'))
True
```

## Output

Finally, the messages returned by GDB are a sequence (may be empty) of asynchronous 
messages and streams, followed by an optional result record. Then, the special token
'(gdb)' should be found, followed by a newline.

Instead of delivery these sequence of messages in one shot, the ``Output`` parser
will deliver each asynchronous message / stream / result separately.

Call ``parse_line`` to parse a full GDB MI message to retrieve the parsed object:

```python
>>> o = Output()

>>> text = '(gdb) \n'  #the extra space is not specified in GDB's docs but it's necessary
>>> o.parse_line(text)
'(gdb)'

>>> text = '~"foo"\n'
>>> stream = o.parse_line(text)
>>> stream
{'type': 'Console', 'value': 'foo'}
```

Call ``parse`` to feed the parser with a partial GDB MI message.
If enough data is given, it will return the parsed object like
``parse_line``. If not, it will return ``None``:


```python
>>> text = '~"bar"\n'
>>> o.parse(text[:3])  # incomplete, return None

>>> stream = o.parse(text[3:])  # feed the rest of the message, return the parsed object
>>> stream
{'type': 'Console', 'value': 'bar'}
```


As an example, this is the message when a execution is stopped:

```python
>>> o = Output()

>>> text = '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
>>> record = o.parse_line(text)
>>> record.async_class, record.type
('stopped', 'Exec')
>>> results = record.as_native()
>>> len(results)
8
>>> results['reason'], results['disp'], results['bkptno'], results['thread-id']
('breakpoint-hit', 'keep', '1', '0')
>>> record             # byexample: +norm-ws
{'bkptno': '1',
 'class': 'stopped',
 'disp': 'keep',
 'frame': {'addr': '0x08048564',
           'args': [{'name': 'argc', 'value': '1'},
                    {'name': 'argv', 'value': '0xbfc4d4d4'}],
           'file': 'myprog.c',
           'fullname': '/home/nickrob/myprog.c',
           'func': 'main',
           'line': '68'},
 'reason': 'breakpoint-hit',
 'thread-id': '0',
 'token': None,
 'type': 'Exec'}

>>> frame = record.as_native()['frame']
>>> frame['addr'], frame['func'], frame['file'], frame['fullname'], frame['line']
('0x08048564', 'main', 'myprog.c', '/home/nickrob/myprog.c', '68')

>>> main_args = frame['args']
>>> main_args[0]['name'], main_args[0]['value']
('argc', '1')
>>> main_args[1]['name'], main_args[1]['value']
('argv', '0xbfc4d4d4')
```
