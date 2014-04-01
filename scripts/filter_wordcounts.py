#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
filter_wordcounts.py
(c) Will Roberts  30 March, 2014

Filters a list of word counts found in the SdeWaC corpus to include
only those listed in GermaNet.
'''

import lzma
import pymongo
import re

WORD_COUNT_FILE = ('/Users/wroberts/Documents/Berlin/hu_page/org/'
                   'files/sdewac-wcount-totals-thresh.tsv.xz')

OUTPUT_FILE = 'sdewac-gn-words.tsv.xz'

# need

# 1. a list of all lemmas in GermaNet
#    - these must not have any spaces in them

client = pymongo.MongoClient()
germanet = client.germanet
gn_words = set(x['orthForm'] for x in germanet.lexunits.find())

# 2. a list of all the inflected forms listed by the Projekt deutscher
#    Wortschatz

infl_words = set(x['word'] for x in germanet.lemmatiser.find())

# put these lists together

all_words = set(x for x in (gn_words | infl_words) if not re.search(r'\s', x))

# now read in the word count list line by line and keep those lines
# which are listed in all_words
input_file = lzma.LZMAFile(WORD_COUNT_FILE)

output_file = lzma.LZMAFile(OUTPUT_FILE, 'w')

for line in input_file:
    word = line.strip().split('\t')[-1]
    if word in all_words:
        output_file.write(line)

input_file.close()
output_file.close()

# this keeps 330665 lines representing 331060882 tokens
#
# the total number of words in SDEWAC is 884,838,511
