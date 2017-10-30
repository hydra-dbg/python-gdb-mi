[![Build Status](https://travis-ci.org/hydra-dbg/python-gdb-mi.svg?branch=master)](https://travis-ci.org/hydra-dbg/python-gdb-mi)

# Python GDB MI Parser

[MI](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI.html) or 
Machine Interface is the new interface to interact with GDB, the GNU Debugger,
from another program.

The output of the GDB Machine Interface is line oriented, text based.
It is compound of small elements that range from strings to dictionaries

`python-gdb-mi` is simple and quite robust parser for Python 2.x/3.x that can 
take those lines and transform them into python objects ready to be serialized
if need to JSON.

## Overview

A GDB MI text can be like this:

```python
>>> text = '^done,bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="0x08048564",func="main",file="myprog.c",fullname="/home/nickrob/myprog.c",line="68",thread-groups=["i1"],times="0"}\n'

```

This is the kind of message that GDB will print when a breakpoint is set.

To parse it, we need to send this line to our `Output` parser using the 
`parse_line` method:

```python
>>> from gdb_mi import Output

>>> out = Output()

>>> record = out.parse_line(text)
>>> record                                #doctest: +NORMALIZE_WHITESPACE
{'klass': 'done',
 'results': {'bkpts': [{'addr': '0x08048564',
                        'disp': 'keep',
                        'enabled': 'y',
                        'file': 'myprog.c',
                        'fullname': '/home/nickrob/myprog.c',
                        'func': 'main',
                        'line': '68',
                        'number': '1',
                        'thread-groups': ['i1'],
                        'times': '0',
                        'type': 'breakpoint'}]},
 'token': None,
 'type': 'Sync'}

```

If the output from GDB is not a complete line, `Output` can handle it anyways
doing some buffering. Use `parse` instead of `parse_line` to feed `Output`:

```python
>>> out.parse(text[:10])     # incomplete line, None returned

>>> out.parse(text[10:])     # enough data, parse it! doctest: +NORMALIZE_WHITESPACE
{'klass': 'done',
 'results': {'bkpts': [{'addr': '0x08048564',
                        'disp': 'keep',
                        'enabled': 'y',
                        'file': 'myprog.c',
                        'fullname': '/home/nickrob/myprog.c',
                        'func': 'main',
                        'line': '68',
                        'number': '1',
                        'thread-groups': ['i1'],
                        'times': '0',
                        'type': 'breakpoint'}]},
 'token': None,
 'type': 'Sync'}

```

## Parsing Results

Four types of objects can be returned by `parse_line` and `parse`:

  `StreamRecord`    that represents an [output record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Stream-Records.html#GDB_002fMI-Stream-Records) from: the console, 
                    the target and the log.
  `ResultRecord`    that represents a synchronous response or [result record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records).
  `AsyncRecord`     that represents an out of band [asynchronous record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Async-Records.html#GDB_002fMI-Async-Records), 
                    used to notify of changes that have happen.
  `(gdb)`           a literal string that represents an empty prompt line.

We have already seen an example of a `ResultRecord`. Here are two more examples
of `StreamRecord` and `AsyncRecord`:

```python
>>> text = '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
>>> async = out.parse_line(text)
>>> async                                 #doctest: +NORMALIZE_WHITESPACE
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

>>> text = '~"GDB rocks!"\n'
>>> stream = out.parse_line(text)
>>> stream
{'stream': 'GDB rocks!', 'type': 'Console'}

```
   
Any object can be then transformed to a simple combination of dict and lists
with the `as_native` method. This makes easier the serialization to JSON or any
other text representation:

```python
>>> s = stream.as_native()
>>> isinstance(s, dict)
True

>>> s['stream'], s['type']
('GDB rocks!', 'Console')

```

## Install

Just run:

```
$ pip install python-gdb-mi

```

You will find the `python-gdb-mi` package at [PyPI](https://pypi.python.org/pypi/python-gdb-mi)

## Workarounds for GDB MI's issues

There are some issues in the output of GDB. `python-gdb-mi` tries to fix
them implementing some minor changes in the GDB's output as workarounds.

See the issues and the implemented fixes in the [workarounds doctest](regress/workarounds.rst)

## Hacking/Contributing

Go ahead! Clone the repository, do a small fix/enhancement, run `make test` to
ensure that everything is working as expected and then propose your Pull Request!


