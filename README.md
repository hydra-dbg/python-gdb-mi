[![Build Status](https://travis-ci.org/hydra-dbg/python-gdb-mi.svg?branch=master)](https://travis-ci.org/hydra-dbg/python-gdb-mi)

# Python GDB MI Parser

[MI](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI.html) or
Machine Interface is the new interface to interact with GDB, the GNU Debugger,
from another program.

The output of the GDB Machine Interface is line oriented, text based.
It is compound of small elements that range from strings to dictionaries

`python-gdb-mi` is simple and quite robust parser for Python 3.x that can
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
>>> record
{'bkpts': [{'addr': '0x08048564',
            'disp': 'keep',
            'enabled': 'y',
            'file': 'myprog.c',
            'fullname': '/home/nickrob/myprog.c',
            'func': 'main',
            'line': '68',
            'number': '1',
            'thread-groups': ['i1'],
            'times': '0',
            'type': 'breakpoint'}],
 'class': 'done',
 'token': None,
 'type': 'Sync'}
```

If the output from GDB is not a complete line, `Output` can handle it anyways
doing some buffering. Use `parse` instead of `parse_line` to feed `Output`:

```python
>>> out.parse(text[:10])     # incomplete line, None returned

>>> out.parse(text[10:])     # enough data, parse it!
{'bkpts': [{'addr': '0x08048564',
            'disp': 'keep',
            'enabled': 'y',
            'file': 'myprog.c',
            'fullname': '/home/nickrob/myprog.c',
            'func': 'main',
            'line': '68',
            'number': '1',
            'thread-groups': ['i1'],
            'times': '0',
            'type': 'breakpoint'}],
 'class': 'done',
 'token': None,
 'type': 'Sync'}
```

## Parsing Results

Four types of objects can be returned by `parse_line` and `parse`:

 - `StreamRecord`    that represents an [output record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Stream-Records.html#GDB_002fMI-Stream-Records) from: the console, 
                     the target and the log.
 - `ResultRecord`    that represents or a synchronous [result record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records)
 - `AsyncRecord`     an out of band [asynchronous record](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Async-Records.html#GDB_002fMI-Async-Records), 
                     used to notify of changes that have happen.
 - `(gdb)`           the literal string that represents an empty prompt line.

All except the literal `(gdb)` have a `as_native` method to transform them into a
composition of Python's dictionaries and lists.

### Streams

```python
>>> from gdb_mi import StreamRecord

>>> text = '~"GDB rocks!"\n'
>>> stream = out.parse_line(text)
>>> stream      # same as pprint.pprint(stream.as_native())
{'type': 'Console', 'value': 'GDB rocks!'}

>>> isinstance(stream, StreamRecord)
True

>>> stream.is_stream()
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
>>> from gdb_mi import ResultRecord

>>> isinstance(record, ResultRecord)
True

>>> record.result_class, record.type
('done', 'Sync')
```

The `result_class` attribute is [one of the following](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Result-Records.html#GDB_002fMI-Result-Records):
`done`, `running`, `connected`, `error` or `exit`.

The `type` attribute is `Sync` for a `synchronous result record`.

Here are an example of an `asynchronous record`:

```python
>>> from gdb_mi import AsyncRecord

>>> text = '42*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",thread-id="0",frame={addr="0x08048564",func="main",args=[{name="argc",value="1"},{name="argv",value="0xbfc4d4d4"}],file="myprog.c",fullname="/home/nickrob/myprog.c",line="68"}\n'
>>> record = out.parse_line(text)

>>> record
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
 'token': 42,
 'type': 'Exec'}

>>> isinstance(record, AsyncRecord)
True

>>> record.async_class, record.type
('stopped', 'Exec')
```

For an `asynchronous record`, the attribute `type` is [one of the following](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Output-Syntax.html#GDB_002fMI-Output-Syntax) for `AsyncRecord`s:
`Exec`, `Status` or `Notify`.

From the GDB MI's documentation:
 - `Exec`: asynchronous state change on the target (stopped, started, disappeared).
 - `Status`: on-going status information about the progress of a slow operation. It can be discarded.
 - `Notify`: supplementary information that the client should handle (e.g., a new breakpoint information).


Both kind of records, synchronous and asynchronous, have one additional attribute:
 - `token`: used by GDB to match the request and the response.

### Interference from Target

If you do not redirect the target's output nor send it to a new console running
the GDB `set new-console on` command, the output of the target will interfere an
confuse the parser.

Unfortunately there is nothing that we can do. Even if we ignore the message
we cannot be sure when a message is safe to be discarded.

For example, the following C code generates an ambiguous output:

```c
printf("~looks like a GDB stream but it isn't\n");
```

Even if you think that it is improbable, here is a quite common problem:

```c
printf("normal output 42"); /* no newline at the end */
fflush(stdout); /* but we flush to the console anyway */
```

Now imagine that GDB hits a breakpoint after the `fflush` instruction, what we will
see is:

```python
>>> text = 'normal output 4242*stopped,reason="breakpoint-hit",<and so on...>\n'
```

The problem is that all those strings are glued together which can lead to
**nasty bugs**. We could try to use some regexps but it would be
too fragile (is the `token` 42 or 4242?).

Instead we try to warn you if you try to parse something like that:

```python
>>> out.parse_line(text)
Traceback (most recent call last):
<...>ParsingError: Invalid input. Maybe the target's output is interfering with the GDB MI's messages. Try to redirect the target's output to elsewhere or run GDB's 'set new-console on' command. Found at 0 position.
Original message:
  normal output 4242*stopped,reason="breakpoint-hit",<...>
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


