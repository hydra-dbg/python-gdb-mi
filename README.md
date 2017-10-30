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

Three types of objects can be returned by `parse_line` and `parse`:

 - `Stream`    that represents an [output record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Stream-Records.html#GDB_002fMI-Stream-Records) from: the console, 
               the target and the log.
 - `Record`    that represents or a synchronous [result record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records) and
               or an out of band [asynchronous record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Async-Records.html#GDB_002fMI-Async-Records), 
               used to notify of changes that have happen.
 - `(gdb)`     a literal string that represents an empty prompt line.

Both, `Stream` and `Record` have a `as_native` method to transform them into a
composition of Python's dicts and lists.

### Streams

>>> from gdb_mi import Stream

>>> text = '~"GDB rocks!"\n'
>>> stream = out.parse_line(text)
>>> stream      # same as pprint.pprint(stream.as_native())
{'stream': 'GDB rocks!', 'type': 'Console'}

>>> isinstance(stream, Stream)
True

```

The `type` attribute is [one of the following](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax),
from the GDB MI's documentation:
 - `Console`: output that should be displayed as is in the console. 
              It is the textual response to a CLI command.
 - `Target`: output produced by the target program.
 - `Log`: output text coming from GDB’s internals, for instance messages that 
          should be displayed as part of an error log.

### Records

We have already seen an example of a `Record`, in that case it was a synchronous
`result record`:

```python
>>> from gdb_mi import Record

>>> isinstance(record, Record)
True

>>> record.klass, record.type
('done', 'Sync')

```

The `klass` attribute is [one of the following](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records): `done`, `running`, `connected`,
`error` or `exit`.

The `type` attribute is `Sync` for a `synchronous result record`.

Here are an example of an `asynchronous record`:

```python
>>> text = '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
>>> record = out.parse_line(text)
>>> record                                #doctest: +NORMALIZE_WHITESPACE
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

>>> isinstance(record, Record)
True

>>> record.klass, record.type
('stopped', 'Exec')

```

For an `asynchronous record`, the attribute `type` is [one of the following](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax) for `AsyncRecord`s:
`Exec`, `Status` or `Notify`.

From the GDB MI's documentation:
 - `Exec`: asynchronous state change on the target (stopped, started, disappeared).
 - `Status`: on-going status information about the progress of a slow operation. It can be discarded.
 - `Notify`: supplementary information that the client should handle (e.g., a new breakpoint information).


Both kind of records, synchronous and asynchronous, have two additional attributes:
 - `token`: used by GDB to match the request and the response.
 - `results`: the data contained in the message, it will depend of the GDB message.


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


