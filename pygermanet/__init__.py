'''
__init__.py
(c) Will Roberts  23 March, 2014

__init__ file to allow pygermanet to be loaded as a module.
'''

from __future__ import absolute_import
from codecs import open
from os import path

# Version. For each new release, the version number should be updated
# in the file VERSION.
try:
    # If a VERSION file exists, use it!
    version_file = path.join(path.dirname(__file__), 'VERSION')
    with open(version_file, encoding='utf-8') as infile:
        __version__ = infile.read().strip()
except NameError:
    __version__ = 'unknown (running code interactively?)'
except IOError as ex:
    __version__ = "unknown (%s)" % ex

# top-level functionality
from .germanet import load_germanet, Synset, Lemma
