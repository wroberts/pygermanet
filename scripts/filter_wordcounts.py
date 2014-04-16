#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
filter_wordcounts.py
(c) Will Roberts  30 March, 2014

Filters a list of word counts found in the SdeWaC corpus to include
only those listed in GermaNet.
'''

from collections import Counter
import gzip
import pymongo
import re

# strip the counts off
# xzcat sdewac-wcount-pos-totals-thresh.tsv.xz | cut -d $'\t' -f2-3 > sdewac-wcount-pos-totals-thresh-nocounts.tsv
# run the treetagger
# ~/Documents/Berlin/dissertation/code/tiger/TreeTagger_DE.sh sdewac-wcount-pos-totals-thresh-nocounts.tsv sdewac-wcount-pos-totals-thresh-nocounts.tsv.tt
# put the counts back on
# xzcat sdewac-wcount-pos-totals-thresh.tsv.xz | cut -d $'\t' -f1 - | paste - sdewac-wcount-pos-totals-thresh-nocounts.tsv.tt | gzip > ~/Documents/Berlin/dissertation/code/pygermanet/scripts/sdewac-treetagger.tsv.gz
WORD_COUNT_FILE = 'sdewac-treetagger.tsv.gz'

OUTPUT_FILE = 'sdewac-gn-words.tsv.gz'

STTS_GERMANET_MAPPING = {'$('      : ' ',
                         '$,'      : ' ',
                         '$.'      : ' ',
                         'ADJ'     : 'j',
                         'ADJA'    : 'j',
                         'ADJD'    : 'j',
                         'ADV'     : 'j',
                         'APPO'    : ' ',
                         'APPR'    : ' ',
                         'APPRART' : ' ',
                         'APZR'    : ' ',
                         'ART'     : ' ',
                         'CARD'    : 'j',
                         'FM'      : 'n',
                         'ITJ'     : ' ',
                         'KOKOM'   : ' ',
                         'KON'     : ' ',
                         'KOUI'    : ' ',
                         'KOUS'    : ' ',
                         'NE'      : 'n',
                         'NN'      : 'n',
                         'PAV'     : ' ',
                         'PROAV'   : ' ',
                         'PDAT'    : ' ',
                         'PDS'     : ' ',
                         'PIAT'    : 'j',
                         'PIS'     : 'j',
                         'PPER'    : ' ',
                         'PPOSAT'  : ' ',
                         'PPOSS'   : ' ',
                         'PRELAT'  : ' ',
                         'PRELS'   : ' ',
                         'PRF'     : ' ',
                         'PTKA'    : ' ',
                         'PTKANT'  : ' ',
                         'PTKNEG'  : ' ',
                         'PTKVZ'   : ' ',
                         'PTKZU'   : ' ',
                         'PWAT'    : ' ',
                         'PWAV'    : ' ',
                         'PWS'     : ' ',
                         'TRUNC'   : ' ',
                         'VAFIN'   : 'v',
                         'VAIMP'   : 'v',
                         'VAINF'   : 'v',
                         'VAPP'    : 'v',
                         'VMFIN'   : 'v',
                         'VMINF'   : 'v',
                         'VMPP'    : 'v',
                         'VVFIN'   : 'v',
                         'VVIMP'   : 'v',
                         'VVINF'   : 'v',
                         'VVIZU'   : 'v',
                         'VVPP'    : 'v',
                         'XY'      : 'n',
}


# need

# 1. a list of all lemmas in GermaNet
#    - these must not have any spaces in them

client = pymongo.MongoClient()
germanet = client.germanet
gn_words = set(x['orthForm'] for x in germanet.lexunits.find())

gn_rewrites = {}
for x in germanet.lexunits.find():
    if 'orthVar' in x:
        gn_rewrites[x['orthVar']] = x['orthForm']
    if 'oldOrthForm' in x:
        gn_rewrites[x['oldOrthForm']] = x['orthForm']
    if 'oldOrthVar' in x:
        gn_rewrites[x['oldOrthVar']] = x['orthForm']


# now read in the word count list line by line and keep those lines
# which are listed in all_words
input_file = gzip.open(WORD_COUNT_FILE)

recounts = Counter()

for line in input_file:
    line = line.decode('utf-8').strip().split('\t')
    if len(line) != 4:
        continue
    count, word, pos, lemma = line
    # map POS tags to GermaNet categories
    pos = STTS_GERMANET_MAPPING.get(pos, ' ')
    if not pos in list('nvj'):
        continue
    # rewrite orthographic forms if needed to canonical GermaNet forms
    lemma = gn_rewrites.get(lemma, lemma)
    # skip words not included in GermaNet
    if not lemma in gn_words:
        continue
    recounts[pos, lemma] += int(count)

input_file.close()

output_file = gzip.open(OUTPUT_FILE, 'w')

for ((pos, lemma), count) in recounts.most_common():
    line = u'\t'.join((str(count), pos, lemma)).encode('utf-8') + '\n'
    output_file.write(line)

output_file.close()

# gzcat sdewac-gn-words.tsv.gz | awk '{ sum+=$1} END {print sum}'

# this keeps 68013 lines representing 333175924 tokens
#
# the total number of words in SDEWAC is 884,838,511
