#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
mongo_import.py
(c) Will Roberts  21 March, 2014

A script to import the GermaNet lexicon into a MongoDB database.
'''

from pymongo import DESCENDING, MongoClient
import glob
import optparse
import os
import re
import sys
import xml.etree.ElementTree as etree


# ------------------------------------------------------------
#  Find filenames
# ------------------------------------------------------------

def find_germanet_xml_files(xml_path):
    '''
    Globs the XML files contained in the given directory and sorts
    them into sections for import into the MongoDB database.

    Arguments:
    - `xml_path`: the path to the directory containing the GermaNet
      XML files
    '''
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

def warn_attribs(loc,
                 node,
                 recognised_attribs,
                 reqd_attribs = None):
    '''
    Error checking of XML input: check that the given node has certain
    required attributes, and does not have any unrecognised
    attributes.

    Arguments:
    - `loc`: a string with some information about the location of the
      error in the XML file
    - `node`: the node to check
    - `recognised_attribs`: a set of node attributes which we know how
      to handle
    - `reqd_attribs`: a set of node attributes which we require to be
      present; if this argument is None, it will take the same value
      as `recognised_attribs`
    '''
    if reqd_attribs is None:
        reqd_attribs = recognised_attribs
    found_attribs = set(node.keys())
    if reqd_attribs - found_attribs:
        print loc, 'missing <{0}> attributes'.format(node.tag), (
            reqd_attribs - found_attribs)
    if found_attribs - recognised_attribs:
        print loc, 'unrecognised <{0}> properties'.format(node.tag), (
            found_attribs - recognised_attribs)

SYNSET_ATTRIBS   = set(['category', 'id', 'class'])
LEXUNIT_ATTRIBS  = set(['styleMarking', 'namedEntity', 'artificial',
                        'source', 'sense', 'id'])
MODIFIER_ATTRIBS = set(['category', 'property'])
HEAD_ATTRIBS     = set(['property'])

MAP_YESNO_TO_BOOL = {
    'yes': True,
    'no':  False,
    }

def read_lexical_file(filename):
    '''
    Reads in a GermaNet lexical information file and returns its
    contents as a list of dictionary structures.

    Arguments:
    - `filename`: the name of the XML file to read
    '''
    with open(filename, 'r') as input_file:
        doc = etree.parse(input_file)

    synsets = []
    assert doc.getroot().tag == 'synsets'
    for synset in doc.getroot():
        if synset.tag != 'synset':
            print 'unrecognised child of <synsets>', synset
            continue
        synset_dict = dict(synset.items())
        synloc = '{0} synset {1},'.format(filename,
                                          synset_dict.get('id', '???'))
        warn_attribs(synloc, synset, SYNSET_ATTRIBS)
        synset_dict['lexunits'] = []
        synsets.append(synset_dict)

        for child in synset:
            if child.tag == 'lexUnit':
                lexunit      = child
                lexunit_dict = dict(lexunit.items())
                lexloc       = synloc + ' lexUnit {0},'.format(
                    lexunit_dict.get('id', '???'))
                warn_attribs(lexloc, lexunit, LEXUNIT_ATTRIBS)
                # convert some properties to booleans
                for key in ['styleMarking', 'artificial', 'namedEntity']:
                    if key in lexunit_dict:
                        if lexunit_dict[key] not in MAP_YESNO_TO_BOOL:
                            print lexloc, ('lexunit property {0} has '
                                           'non-boolean value').format(key), \
                                           lexunit_dict[key]
                            continue
                        lexunit_dict[key] = MAP_YESNO_TO_BOOL[lexunit_dict[key]]
                # convert sense to integer number
                if 'sense' in lexunit_dict:
                    if lexunit_dict['sense'].isdigit():
                        lexunit_dict['sense'] = int(lexunit_dict['sense'], 10)
                    else:
                        print lexloc, ('lexunit property sense has '
                                       'non-numeric value'), \
                                       lexunit_dict['sense']
                synset_dict['lexunits'].append(lexunit_dict)
                lexunit_dict['examples'] = []
                lexunit_dict['frames']   = []
                for child in lexunit:
                    if child.tag in ['orthForm',
                                     'orthVar',
                                     'oldOrthForm',
                                     'oldOrthVar']:
                        warn_attribs(lexloc, child, set())
                        if not child.text:
                            print lexloc, '{0} with no text'.format(child.tag)
                            continue
                        if child.tag in lexunit_dict:
                            print lexloc, 'more than one {0}'.format(child.tag)
                        lexunit_dict[child.tag] = unicode(child.text)
                    elif child.tag == 'example':
                        example = child
                        text = [child for child in example
                                if child.tag == 'text']
                        if len(text) != 1 or not text[0].text:
                            print lexloc, '<example> tag without text'
                        example_dict = {'text': unicode(text[0].text)}
                        for child in example:
                            if child.tag == 'text':
                                continue
                            elif child.tag == 'exframe':
                                if 'exframe' in example_dict:
                                    print lexloc, ('more than one <exframe> '
                                                   'for <example>')
                                warn_attribs(lexloc, child, set())
                                if not child.text:
                                    print lexloc, '<exframe> with no text'
                                    continue
                                example_dict['exframe'] = unicode(child.text)
                            else:
                                print lexloc, ('unrecognised child of '
                                               '<example>'), child
                        lexunit_dict['examples'].append(example_dict)
                    elif child.tag == 'frame':
                        frame = child
                        warn_attribs(lexloc, frame, set())
                        if 0 < len(frame):
                            print lexloc, 'unrecognized <frame> children', \
                                list(frame)
                        if not frame.text:
                            print lexloc, '<frame> without text'
                            continue
                        lexunit_dict['frames'].append(unicode(frame.text))
                    elif child.tag == 'compound':
                        compound = child
                        warn_attribs(lexloc, compound, set())
                        compound_dict = {}
                        for child in compound:
                            if child.tag == 'modifier':
                                modifier_dict = dict(child.items())
                                warn_attribs(lexloc, child,
                                             MODIFIER_ATTRIBS, set())
                                if not child.text:
                                    print lexloc, 'modifier without text'
                                    continue
                                modifier_dict['text'] = unicode(child.text)
                                if 'modifier' not in compound_dict:
                                    compound_dict['modifier'] = []
                                compound_dict['modifier'].append(modifier_dict)
                            elif child.tag == 'head':
                                head_dict = dict(child.items())
                                warn_attribs(lexloc, child, HEAD_ATTRIBS, set())
                                if not child.text:
                                    print lexloc, '<head> without text'
                                    continue
                                head_dict['text'] = unicode(child.text)
                                if 'head' in compound_dict:
                                    print lexloc, ('more than one head in '
                                                   '<compound>')
                                compound_dict['head'] = head_dict
                            else:
                                print lexloc, ('unrecognised child of '
                                               '<compound>'), child
                                continue
                    else:
                        print lexloc, 'unrecognised child of <lexUnit>', child
                        continue
            elif child.tag == 'paraphrase':
                paraphrase = child
                warn_attribs(synloc, paraphrase, set())
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
    '''
    Reads the GermaNet relation file ``gn_relations.xml`` which lists
    all the relations holding between lexical units and synsets.

    Arguments:
    - `filename`:
    '''
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
            warn_attribs('', child, RELATION_ATTRIBS, RELATION_ATTRIBS_REQD)
            if child_dict['dir'] not in LEX_REL_DIRS:
                print 'unrecognized <lex_rel> dir', child_dict['dir']
            if child_dict['dir'] == 'both' and 'inv' not in child_dict:
                print '<lex_rel> has dir=both but does not specify inv'
            lex_rels.append(child_dict)
        elif child.tag == 'con_rel':
            if 0 < len(child):
                print '<con_rel> has unexpected child node'
            child_dict = dict(child.items())
            warn_attribs('', child, RELATION_ATTRIBS, RELATION_ATTRIBS_REQD)
            if child_dict['dir'] not in CON_REL_DIRS:
                print 'unrecognized <con_rel> dir', child_dict['dir']
            if (child_dict['dir'] in ['both', 'revert'] and
                'inv' not in child_dict):
                print '<con_rel> has dir={0} but does not specify inv'.format(
                    child_dict['dir'])
            con_rels.append(child_dict)
        else:
            print 'unrecognised child of <relations>', child
            continue

    return lex_rels, con_rels


# ------------------------------------------------------------
#  Read wiktionary paraphrase file
# ------------------------------------------------------------

PARAPHRASE_ATTRIBS = set(['edited', 'lexUnitId', 'wiktionaryId',
                          'wiktionarySense', 'wiktionarySenseId'])

def read_paraphrase_file(filename):
    '''
    Reads in a GermaNet wiktionary paraphrase file and returns its
    contents as a list of dictionary structures.

    Arguments:
    - `filename`:
    '''
    with open(filename) as input_file:
        doc = etree.parse(input_file)

    assert doc.getroot().tag == 'wiktionaryParaphrases'
    paraphrases = []
    for child in doc.getroot():
        if child.tag == 'wiktionaryParaphrase':
            paraphrase = child
            warn_attribs('', paraphrase, PARAPHRASE_ATTRIBS)
            if 0 < len(paraphrase):
                print 'unrecognized child of <wiktionaryParaphrase>', \
                    list(paraphrase)
            paraphrase_dict = dict(paraphrase.items())
            if paraphrase_dict['edited'] not in MAP_YESNO_TO_BOOL:
                print '<paraphrase> attribute "edited" has unexpected value', \
                    paraphrase_dict['edited']
            else:
                paraphrase_dict['edited'] = MAP_YESNO_TO_BOOL[
                    paraphrase_dict['edited']]
            if not paraphrase_dict['wiktionarySenseId'].isdigit():
                print ('<paraphrase> attribute "wiktionarySenseId" has '
                       'non-integer value'), paraphrase_dict['edited']
            else:
                paraphrase_dict['wiktionarySenseId'] = \
                    int(paraphrase_dict['wiktionarySenseId'], 10)
            paraphrases.append(paraphrase_dict)
        else:
            print 'unknown child of <wiktionaryParaphrases>', child

    return paraphrases


# ------------------------------------------------------------
#  Mongo insertion
# ------------------------------------------------------------

# we need to change the names of some synset keys because they are
# Python keywords
SYNSET_KEY_REWRITES = {
    'class': 'gn_class',
    }

def insert_lexical_information(germanet_db, lex_files):
    '''
    Reads in the given lexical information files and inserts their
    contents into the given MongoDB database.

    Arguments:
    - `germanet_db`: a pymongo.database.Database object
    - `lex_files`: a list of paths to XML files containing lexial
      information
    '''
    # drop the database collections if they already exist
    germanet_db.lexunits.drop()
    germanet_db.synsets.drop()
    # inject data from XML files into the database
    for lex_file in lex_files:
        synsets = read_lexical_file(lex_file)
        for synset in synsets:
            synset = dict((SYNSET_KEY_REWRITES.get(key, key), value)
                          for (key, value) in synset.iteritems())
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
    '''
    Reads in the given GermaNet relation file and inserts its contents
    into the given MongoDB database.

    Arguments:
    - `germanet_db`: a pymongo.database.Database object
    - `gn_rels_file`:
    '''
    lex_rels, con_rels = read_relation_file(gn_rels_file)

    # cache the lexunits while we work on them
    lexunits = {}
    for lex_rel in lex_rels:
        if lex_rel['from'] not in lexunits:
            lexunits[lex_rel['from']] = germanet_db.lexunits.find_one(
                {'id': lex_rel['from']})
        from_lexunit = lexunits[lex_rel['from']]
        if lex_rel['to'] not in lexunits:
            lexunits[lex_rel['to']] = germanet_db.lexunits.find_one(
                {'id': lex_rel['to']})
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
            synsets[con_rel['from']] = germanet_db.synsets.find_one(
                {'id': con_rel['from']})
        from_synset = synsets[con_rel['from']]
        if con_rel['to'] not in synsets:
            synsets[con_rel['to']] = germanet_db.synsets.find_one(
                {'id': con_rel['to']})
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

def insert_paraphrase_information(germanet_db, wiktionary_files):
    '''
    Reads in the given GermaNet relation file and inserts its contents
    into the given MongoDB database.

    Arguments:
    - `germanet_db`: a pymongo.database.Database object
    - `wiktionary_files`:
    '''
    num_paraphrases = 0
    # cache the lexunits while we work on them
    lexunits = {}
    for filename in wiktionary_files:
        paraphrases = read_paraphrase_file(filename)
        num_paraphrases += len(paraphrases)
        for paraphrase in paraphrases:
            if paraphrase['lexUnitId'] not in lexunits:
                lexunits[paraphrase['lexUnitId']] = \
                    germanet_db.lexunits.find_one(
                    {'id': paraphrase['lexUnitId']})
            lexunit = lexunits[paraphrase['lexUnitId']]
            if 'paraphrases' not in lexunit:
                lexunit['paraphrases'] = []
            lexunit['paraphrases'].append(paraphrase)
    for lexunit in lexunits.values():
        germanet_db.lexunits.save(lexunit)

    print 'Inserted {0} wiktionary paraphrases.'.format(num_paraphrases)


# ------------------------------------------------------------
#  Main function
# ------------------------------------------------------------

def main():
    '''Main function.'''
    usage = ('\n\n  %prog [options] XML_PATH\n\nArguments:\n\n  '
             'XML_PATH              the directory containing the '
             'GermaNet .xml files')

    parser = optparse.OptionParser(usage = usage)
    parser.add_option('--host', default=None,
                      help='hostname or IP address of the MongoDB instance '
                      'where the GermaNet database will be inserted '
                      '(default: %default)')
    parser.add_option('--port', type='int', default=None,
                      help='port number of the MongoDB instance where the '
                      'GermaNet database will be inserted (default: %default)')
    parser.add_option('--database', dest='database_name', default='germanet',
                      help='the name of the database on the MongoDB instance '
                      'where GermaNet will be stored (default: %default)')
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("incorrect number of arguments")
        sys.exit(1)
    xml_path = args[0]

    client = MongoClient(options.host, options.port)
    germanet_db = client[options.database_name]

    lex_files, gn_rels_file, wiktionary_files, ili_files = \
        find_germanet_xml_files(xml_path)

    insert_lexical_information(germanet_db, lex_files)
    insert_relation_information(germanet_db, gn_rels_file)
    insert_paraphrase_information(germanet_db, wiktionary_files)

    client.close()

if __name__ == '__main__' and sys.argv != ['']:
    main()
