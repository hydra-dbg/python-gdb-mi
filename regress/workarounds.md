# Workarounds for GDB MI's issues

Workaround for
[inaccuracy while adding a multiple location breakpoint](https://sourceware.org/bugzilla/show_bug.cgi?id=14733)
bug.

This bug makes an incorrect output when multiple breakpoints are in the same
location: each breakpoint's data is glued together in a non-conforming MI syntax.

This issue affects the result (synchronous), the asynchronous records and it even
affects the results of a
[Breakpoint Table](https://sourceware.org/gdb/onlinedocs/gdb/GDB_002fMI-Breakpoint-Commands.html#GDB_002fMI-Breakpoint-Commands)

```
=breakpoint-modified,bkpt={...
^done,bkpt={...
BreakpointTable={...
```

The proposed solution is to replace that by a simple list.

Notice how we also changed the expected keyword ``bkpt`` by ``bkpts``:

```python
>>> text = '=breakpoint-modified,bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="1",original-location="roll"},{number="1.1",enabled="y",addr="0x08048563",func="roll",file="two_pthreads.c",fullname="/threads/two_pthreads.c",line="5",thread-groups=["i1"]},{number="1.2",enabled="y",addr="0x08048563",func="roll",file="two_pthreads.c",fullname="/threads/two_pthreads.c",line="5",thread-groups=["i2"]}\n'

>>> import pprint
>>> from gdb_mi import Output

>>> o = Output()

>>> record = o.parse_line(text)
>>> record.async_class, record.type
('breakpoints-modified', 'Notify')

>>> record
{'bkpts': [{'addr': '<MULTIPLE>',
            'disp': 'keep',
            'enabled': 'y',
            'number': '1',
            'original-location': 'roll',
            'times': '1',
            'type': 'breakpoint'},
           {'addr': '0x08048563',
            'enabled': 'y',
            'file': 'two_pthreads.c',
            'fullname': '/threads/two_pthreads.c',
            'func': 'roll',
            'line': '5',
            'number': '1.1',
            'thread-groups': ['i1']},
           {'addr': '0x08048563',
            'enabled': 'y',
            'file': 'two_pthreads.c',
            'fullname': '/threads/two_pthreads.c',
            'func': 'roll',
            'line': '5',
            'number': '1.2',
            'thread-groups': ['i2']}],
 'class': 'breakpoints-modified',
 'token': None,
 'type': 'Notify'}
```

To make this behavior uniform we apply the same change even if there is only
one breakpoint:

```python
>>> text = '^done,bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="0x08048564",func="main",file="myprog.c",fullname="/home/nickrob/myprog.c",line="68",thread-groups=["i1"],times="0"}\n'
>>> record = o.parse_line(text)
>>> record.result_class, record.type
('done', 'Result')

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
 'type': 'Result'}
```

Due the same bug, we need to modify the event ``BreakpointTable`` which lists
the breakpoints and if some of them are in the same address, this will
trigger the same bug.

Here is the fix:

```python
>>> text = '^done,BreakpointTable={nr_rows="3",nr_cols="6",hdr=[{width="7",alignment="-1",col_name="number",colhdr="Num"},{width="14",alignment="-1",col_name="type",colhdr="Type"},{width="4",alignment="-1",col_name="disp",colhdr="Disp"},{width="3",alignment="-1",col_name="enabled",colhdr="Enb"},{width="18",alignment="-1",col_name="addr",colhdr="Address"},{width="40",alignment="2",col_name="what",colhdr="What"}],body=[bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="roll"},{number="1.1",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i1"]},{number="1.2",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i2"]},bkpt={number="2",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="roll"},{number="2.1",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i1"]},{number="2.2",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i2"]},bkpt={number="3",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="roll"},{number="3.1",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i1"]},{number="3.2",enabled="y",addr="0x00000000004006a9",func="roll",file="three_pthreads.c",fullname="/threads/three_pthreads.c",line="5",thread-groups=["i2"]}]}\n'

>>> record = o.parse_line(text)
>>> record              # byexample: -tags
{'BreakpointTable': {'body': [{'addr': '<MULTIPLE>',
                               'disp': 'keep',
                               'enabled': 'y',
                               'number': '1',
                               'original-location': 'roll',
                               'times': '0',
                               'type': 'breakpoint'},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '1.1',
                               'thread-groups': ['i1']},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '1.2',
                               'thread-groups': ['i2']},
                              {'addr': '<MULTIPLE>',
                               'disp': 'keep',
                               'enabled': 'y',
                               'number': '2',
                               'original-location': 'roll',
                               'times': '0',
                               'type': 'breakpoint'},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '2.1',
                               'thread-groups': ['i1']},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '2.2',
                               'thread-groups': ['i2']},
                              {'addr': '<MULTIPLE>',
                               'disp': 'keep',
                               'enabled': 'y',
                               'number': '3',
                               'original-location': 'roll',
                               'times': '0',
                               'type': 'breakpoint'},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '3.1',
                               'thread-groups': ['i1']},
                              {'addr': '0x00000000004006a9',
                               'enabled': 'y',
                               'file': 'three_pthreads.c',
                               'fullname': '/threads/three_pthreads.c',
                               'func': 'roll',
                               'line': '5',
                               'number': '3.2',
                               'thread-groups': ['i2']}],
                     'hdr': [{'alignment': '-1',
                              'col_name': 'number',
                              'colhdr': 'Num',
                              'width': '7'},
                             {'alignment': '-1',
                              'col_name': 'type',
                              'colhdr': 'Type',
                              'width': '14'},
                             {'alignment': '-1',
                              'col_name': 'disp',
                              'colhdr': 'Disp',
                              'width': '4'},
                             {'alignment': '-1',
                              'col_name': 'enabled',
                              'colhdr': 'Enb',
                              'width': '3'},
                             {'alignment': '-1',
                              'col_name': 'addr',
                              'colhdr': 'Address',
                              'width': '18'},
                             {'alignment': '2',
                              'col_name': 'what',
                              'colhdr': 'What',
                              'width': '40'}],
                     'nr_cols': '6',
                     'nr_rows': '3'},
 'class': 'done',
 'token': None,
 'type': 'Result'}
```
