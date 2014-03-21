#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from pymongo import DESCENDING, MongoClient
import glob
import os
import re
import xml.etree.ElementTree as etree


# ------------------------------------------------------------
#  Find filenames
# ------------------------------------------------------------

def find_germanet_xml_files(xml_path):
    xml_files = sorted(glob.glob(os.path.join(xml_path, '*.xml')))

    # sort out the lexical files
    lex_files = [xml_file for xml_file in xml_files if
                 re.match(r'(adj|nomen|verben)\.',
                          os.path.basename(xml_file).lower())]
    xml_files = sorted(set(xml_files) - set(lex_files))

    if not lex_files:
        print 'ERROR: cannot find lexical information files'

    # sort out the GermaNet relations file
    gn_rels_file = [xml_file for xml_file in xml_files if
                    os.path.basename(xml_file).lower() == 'gn_relations.xml']
    xml_files = sorted(set(xml_files) - set(gn_rels_file))

    if not gn_rels_file:
        print 'ERROR: cannot find relations file gn_relations.xml'
        gn_rels_file = None
    else:
        if 1 < len(gn_rels_file):
            print ('WARNING: more than one relations file gn_relations.xml, '
                   'taking first match')
        gn_rels_file = gn_rels_file[0]

    # sort out the wiktionary paraphrase files
    wiktionary_files =  [xml_file for xml_file in xml_files if
                         re.match(r'wiktionaryparaphrases-',
                                  os.path.basename(xml_file).lower())]
    xml_files = sorted(set(xml_files) - set(wiktionary_files))

    if not wiktionary_files:
        print 'WARNING: cannot find wiktionary paraphrase files'

    # sort out the interlingual index file
    ili_files = [xml_file for xml_file in xml_files if
                os.path.basename(xml_file).lower().startswith(
            'interlingualindex')]
    xml_files = sorted(set(xml_files) - set(ili_files))

    if not ili_files:
        print 'WARNING: cannot find interlingual index file'

    if xml_files:
        print 'WARNING: unrecognized xml files:', xml_files

    return lex_files, gn_rels_file, wiktionary_files, ili_files


# ------------------------------------------------------------
#  Read lexical files
# ------------------------------------------------------------

SYNSET_ATTRIBS   = ['category', 'id', 'class']
LEXUNIT_ATTRIBS  = ['styleMarking', 'namedEntity', 'artificial', 'source', 'sense', 'id']
MODIFIER_ATTRIBS = ['category', 'property']
HEAD_ATTRIBS     = ['property']

MAP_YESNO_TO_BOOL = {
    'yes': True,
    'no':  False,
    }

def read_lexical_file(filename):
    with open(filename, 'r') as input_file:
        doc = etree.parse(input_file)

    synsets = []
    assert doc.getroot().tag == 'synsets'
    for synset in doc.getroot():
        if synset.tag != 'synset':
            print 'unrecognised child of <synsets>', synset
            continue
        synset_dict = dict(synset.items())
        synloc = '{0} synset {1},'.format(filename, synset_dict.get('id', '???'))
        if set(SYNSET_ATTRIBS) - set(synset_dict):
            print synloc, 'missing synset properties', set(SYNSET_ATTRIBS) - set(synset_dict)
        if set(synset_dict) - set(SYNSET_ATTRIBS):
            print synloc, 'unrecognised synset properties', set(synset_dict) - set(SYNSET_ATTRIBS)
        synset_dict['lexunits'] = []
        synsets.append(synset_dict)

        for child in synset:
            if child.tag == 'lexUnit':
                lexunit      = child
                lexunit_dict = dict(lexunit.items())
                lexloc       = synloc + ' lexUnit {0},'.format(lexunit_dict.get('id', '???'))
                if set(LEXUNIT_ATTRIBS) - set(lexunit_dict):
                    print lexloc, 'missing lexunit properties', set(LEXUNIT_ATTRIBS) - set(lexunit_dict)
                if set(lexunit_dict) - set(LEXUNIT_ATTRIBS):
                    print lexloc, 'unrecognised lexunit properties', set(lexunit_dict) - set(LEXUNIT_ATTRIBS)
                # convert some properties to booleans
                for key in ['styleMarking', 'artificial', 'namedEntity']:
                    if key in lexunit_dict:
                        if lexunit_dict[key] not in MAP_YESNO_TO_BOOL:
                            print lexloc, 'lexunit property {0} has non-boolean value'.format(key), lexunit_dict[key]
                            continue
                        lexunit_dict[key] = MAP_YESNO_TO_BOOL[lexunit_dict[key]]
                # convert sense to integer number
                if 'sense' in lexunit_dict:
                    if lexunit_dict['sense'].isdigit():
                        lexunit_dict['sense'] = int(lexunit_dict['sense'], 10)
                    else:
                        print lexloc, 'lexunit property sense has non-numeric value', lexunit_dict['sense']
                synset_dict['lexunits'].append(lexunit_dict)
                lexunit_dict['examples'] = []
                lexunit_dict['frames']   = []
                for child in lexunit:
                    if child.tag in ['orthForm',
                                     'orthVar',
                                     'oldOrthForm',
                                     'oldOrthVar']:
                        if child.keys():
                            print lexloc, 'unrecognised {0} properties'.format(child.tag), child.keys()
                        if not child.text:
                            print lexloc, '{0} with no text'.format(child.tag)
                            continue
                        if child.tag in lexunit_dict:
                            print lexloc, 'more than one {0}'.format(child.tag)
                        lexunit_dict[child.tag] = unicode(child.text)
                    elif child.tag == 'example':
                        example = child
                        text = [child for child in example if child.tag == 'text']
                        if len(text) != 1 or not text[0].text:
                            print lexloc, '<example> tag without text'
                        example_dict = {'text': unicode(text[0].text)}
                        for child in example:
                            if child.tag == 'text':
                                continue
                            elif child.tag == 'exframe':
                                if 'exframe' in example_dict:
                                    print lexloc, 'more than one <exframe> for <example>'
                                if child.keys():
                                    print lexloc, 'unrecognised <exframe> properties', child.keys()
                                if not child.text:
                                    print lexloc, '<exframe> with no text'
                                    continue
                                example_dict['exframe'] = unicode(child.text)
                            else:
                                print lexloc, 'unrecognised child of <example>', child
                        lexunit_dict['examples'].append(example_dict)
                    elif child.tag == 'frame':
                        frame = child
                        if frame.keys():
                            print lexloc, 'unrecognized <frame> properties', frame.keys()
                        if 0 < len(frame):
                            print lexloc, 'unrecognized <frame> children', list(frame)
                        if not frame.text:
                            print lexloc, '<frame> without text'
                            continue
                        lexunit_dict['frames'].append(unicode(frame.text))
                    elif child.tag == 'compound':
                        compound = child
                        if compound.keys():
                            print lexloc, 'unrecognized <compound> properties', compound.keys()
                        compound_dict = {}
                        for child in compound:
                            if child.tag == 'modifier':
                                modifier_dict = dict(child.items())
                                if set(modifier_dict) - set(MODIFIER_ATTRIBS):
                                    print lexloc, 'unrecognised modifier properties', set(modifier_dict) - set(MODIFIER_ATTRIBS)
                                if not child.text:
                                    print lexloc, 'modifier without text'
                                    continue
                                modifier_dict['text'] = unicode(child.text)
                                if 'modifier' not in compound_dict:
                                    compound_dict['modifier'] = []
                                compound_dict['modifier'].append(modifier_dict)
                            elif child.tag == 'head':
                                head_dict = dict(child.items())
                                if set(head_dict) - set(HEAD_ATTRIBS):
                                    print lexloc, 'unrecognised <head> properties', set(head_dict) - set(HEAD_ATTRIBS)
                                if not child.text:
                                    print lexloc, '<head> without text'
                                    continue
                                head_dict['text'] = unicode(child.text)
                                if 'head' in compound_dict:
                                    print lexloc, 'more than one head in <compound>'
                                compound_dict['head'] = head_dict
                            else:
                                print lexloc, 'unrecognised child of <compound>', child
                                continue
                    else:
                        print lexloc, 'unrecognised child of <lexUnit>', child
                        continue
            elif child.tag == 'paraphrase':
                paraphrase = child
                if paraphrase.keys():
                    print synloc, 'unrecognised paraphrase properties', paraphrase.keys()
                paraphrase_text = unicode(paraphrase.text)
                if not paraphrase_text:
                    print synloc, 'WARNING: <paraphrase> tag with no text'
            else:
                print synloc, 'unrecognised child of <synset>', child
                continue

    return synsets


# ------------------------------------------------------------
#  Read relation file
# ------------------------------------------------------------

RELATION_ATTRIBS_REQD = set(['dir', 'from', 'name', 'to'])
RELATION_ATTRIBS_OPT  = set(['inv'])
RELATION_ATTRIBS      = RELATION_ATTRIBS_REQD | RELATION_ATTRIBS_OPT
LEX_REL_DIRS          = set(['both', 'one'])
CON_REL_DIRS          = set(['both', 'revert', 'one'])

def read_relation_file(filename):
    with open(filename, 'r') as input_file:
        doc = etree.parse(input_file)

    lex_rels = []
    con_rels = []
    assert doc.getroot().tag == 'relations'
    for child in doc.getroot():
        if child.tag == 'lex_rel':
            if 0 < len(child):
                print '<lex_rel> has unexpected child node'
            child_dict = dict(child.items())
            if set(child_dict) - RELATION_ATTRIBS:
                print '<lex_rel> has unexpected properties', set(child_dict) - RELATION_ATTRIBS
            if RELATION_ATTRIBS_REQD - set(child_dict):
                print '<lex_rel> has missing properties', RELATION_ATTRIBS_REQD - set(child_dict)
            if child_dict['dir'] not in LEX_REL_DIRS:
                print 'unrecognized <lex_rel> dir', child_dict['dir']
            if child_dict['dir'] == 'both' and 'inv' not in child_dict:
                print '<lex_rel> has dir=both but does not specify inv'
            lex_rels.append(child_dict)
        elif child.tag == 'con_rel':
            if 0 < len(child):
                print '<con_rel> has unexpected child node'
            child_dict = dict(child.items())
            if set(child_dict) - RELATION_ATTRIBS:
                print '<con_rel> has unexpected properties', set(child_dict) - RELATION_ATTRIBS
            if RELATION_ATTRIBS_REQD - set(child_dict):
                print '<con_rel> has missing properties', RELATION_ATTRIBS_REQD - set(child_dict)
            if child_dict['dir'] not in CON_REL_DIRS:
                print 'unrecognized <con_rel> dir', child_dict['dir']
            if child_dict['dir'] in ['both', 'revert'] and 'inv' not in child_dict:
                print '<con_rel> has dir={0} but does not specify inv'.format(child_dict['dir'])
            con_rels.append(child_dict)
        else:
            print 'unrecognised child of <relations>', synset
            continue

    return lex_rels, con_rels


# ------------------------------------------------------------
#  Mongo insertion
# ------------------------------------------------------------

# we need to change the names of some synset keys because they are
# Python keywords
SYNSET_KEY_REWRITES = {
    'class': 'gn_class',
    }

def insert_lexical_information(germanet_db, lex_files):
    # drop the database collections if they already exist
    germanet_db.lexunits.drop()
    germanet_db.synsets.drop()
    # inject data from XML files into the database
    for lex_file in lex_files:
        synsets = read_lexical_file(lex_file)
        for synset in synsets:
            synset = dict((SYNSET_KEY_REWRITES.get(key, key), value) for (key, value) in synset.iteritems())
            lexunits = synset['lexunits']
            synset['lexunits'] = germanet_db.lexunits.insert(lexunits)
            synset_id = germanet_db.synsets.insert(synset)
            for lexunit in lexunits:
                lexunit['synset']   = synset_id
                lexunit['category'] = synset['category']
                germanet_db.lexunits.save(lexunit)
    # index the two collections by id
    germanet_db.synsets.create_index('id')
    germanet_db.lexunits.create_index('id')
    # also index lexunits by lemma, lemma-pos, and lemma-pos-sensenum
    germanet_db.lexunits.create_index([('orthForm', DESCENDING)])
    germanet_db.lexunits.create_index([('orthForm', DESCENDING),
                                       ('category', DESCENDING)])
    germanet_db.lexunits.create_index([('orthForm', DESCENDING),
                                       ('category', DESCENDING),
                                       ('sense', DESCENDING)])
    print 'Inserted {0} synsets, {1} lexical units.'.format(
        germanet_db.synsets.count(),
        germanet_db.lexunits.count())

def insert_relation_information(germanet_db, gn_rels_file):
    lex_rels, con_rels = read_relation_file(gn_rels_file)

    # cache the lexunits while we work on them
    lexunits = {}
    for lex_rel in lex_rels:
        if lex_rel['from'] not in lexunits:
            lexunits[lex_rel['from']] = germanet_db.lexunits.find_one({'id': lex_rel['from']})
        from_lexunit = lexunits[lex_rel['from']]
        if lex_rel['to'] not in lexunits:
            lexunits[lex_rel['to']] = germanet_db.lexunits.find_one({'id': lex_rel['to']})
        to_lexunit = lexunits[lex_rel['to']]
        if 'rels' not in from_lexunit:
            from_lexunit['rels'] = set()
        from_lexunit['rels'].add((lex_rel['name'], to_lexunit['_id']))
        if lex_rel['dir'] == 'both':
            if 'rels' not in to_lexunit:
                to_lexunit['rels'] = set()
            to_lexunit['rels'].add((lex_rel['inv'], from_lexunit['_id']))
    for lexunit in lexunits.values():
        if 'rels' in lexunit:
            lexunit['rels'] = sorted(lexunit['rels'])
            germanet_db.lexunits.save(lexunit)

    # cache the synsets while we work on them
    synsets = {}
    for con_rel in con_rels:
        if con_rel['from'] not in synsets:
            synsets[con_rel['from']] = germanet_db.synsets.find_one({'id': con_rel['from']})
        from_synset = synsets[con_rel['from']]
        if con_rel['to'] not in synsets:
            synsets[con_rel['to']] = germanet_db.synsets.find_one({'id': con_rel['to']})
        to_synset = synsets[con_rel['to']]
        if 'rels' not in from_synset:
            from_synset['rels'] = set()
        from_synset['rels'].add((con_rel['name'], to_synset['_id']))
        if con_rel['dir'] in ['both', 'revert']:
            if 'rels' not in to_synset:
                to_synset['rels'] = set()
            to_synset['rels'].add((con_rel['inv'], from_synset['_id']))
    for synset in synsets.values():
        if 'rels' in synset:
            synset['rels'] = sorted(synset['rels'])
            germanet_db.synsets.save(synset)

    print 'Inserted {0} lexical relations, {1} synset relations.'.format(
        len(lex_rels), len(con_rels))


# ------------------------------------------------------------
#  Debug
# ------------------------------------------------------------

if 0:
    GN_XML_PATH = 'GN_V80_XML'

    client = MongoClient()
    germanet_db = client.germanet

    lex_files, gn_rels_file, wiktionary_files, ili_files = \
        find_germanet_xml_files(GN_XML_PATH)

    insert_lexical_information(germanet_db, lex_files)
    insert_relation_information(germanet_db, gn_rels_file)
