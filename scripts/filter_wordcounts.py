#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
filter_wordcounts.py
(c) Will Roberts  30 March, 2014

Filters a list of word counts found in the SdeWaC corpus to include
only those listed in GermaNet.
'''

import mongodb

WORD_COUNT_FILE = ('/Users/wroberts/Documents/Berlin/hu_page/org/'
                   'files/sdewac-wcount-totals-thresh.tsv.xz')
