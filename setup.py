"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='python-gdb-mi',
    version='1.0.1',

    description='A parser for GDB Machine Interface (MI) events.',
    long_description=long_description,

    url='https://github.com/hydra-dbg/python-gdb-mi',

    # Author details
    author='Di Paola Martin, Di Tomaso Nicolas',
    author_email='no-email@example.com',
    
    license='GNU LGPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Debuggers',

        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],

    python_requires='>=2.6',

    keywords='debugger gdb',

    py_modules=['gdb_mi'],

)

