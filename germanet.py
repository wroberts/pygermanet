#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
germanet.py
(c) Will Roberts  21 March, 2014

GermaNet interface.
'''

from pymongo import DESCENDING, MongoClient
import functools

LONG_POS_TO_SHORT = {
    'verben': 'v',
    'nomen':  'n',
    'adj':    'j',
    }

SHORT_POS_TO_LONG = dict((v, k) for (k, v) in LONG_POS_TO_SHORT.items())

class GermaNet(object):
    '''A class representing the GermaNet database.'''

    def __init__(self, mongo_db):
        '''
        Creates a new GermaNet object.

        Arguments:
        - `mongo_db`: a pymongo.database.Database object containing
          the GermaNet lexicon
        '''
        self._mongo_db = mongo_db

    def lemmas(self, lemma, pos = None):
        '''
        Looks up lemmas in the GermaNet database.

        Arguments:
        - `lemma`:
        - `pos`:
        '''
        if pos is not None:
            if pos not in SHORT_POS_TO_LONG:
                return None
            pos         = SHORT_POS_TO_LONG[pos]
            lemma_dicts = self._mongo_db.lexunits.find({'orthForm': lemma,
                                                        'category': pos})
        else:
            lemma_dicts = self._mongo_db.lexunits.find({'orthForm': lemma})
        return sorted([Lemma(self, lemma_dict) for lemma_dict in lemma_dicts])

    def synsets(self, lemma, pos = None):
        '''
        Looks up synsets in the GermaNet database.

        Arguments:
        - `lemma`:
        - `pos`:
        '''
        return sorted(set(lemma.synset for lemma in self.lemmas(lemma, pos)))

    def synset(self, synset_repr):
        '''
        Looks up a synset in GermaNet using its string representation.

        Arguments:
        - `synset_repr`: a unicode string containing the lemma, part
          of speech, and sense number of the first lemma of the synset

        >>> gn.synset(u'funktionieren.v.2')
        Synset(funktionieren.v.2)
        '''
        parts = synset_repr.split('.')
        if len(parts) != 3:
            return None
        lemma, pos, sensenum = parts
        if (not sensenum.isdigit() or pos not in SHORT_POS_TO_LONG):
            return None
        sensenum   = int(sensenum, 10)
        pos        = SHORT_POS_TO_LONG[pos]
        lemma_dict = self._mongo_db.lexunits.find_one({'orthForm': lemma,
                                                       'category': pos,
                                                       'sense':    sensenum})
        if lemma_dict:
            return Lemma(self, lemma_dict).synset

    def get_synset_by_id(self, mongo_id):
        synset_dict = self._mongo_db.synsets.find_one({'_id': mongo_id})
        if synset_dict is not None:
            return Synset(self, synset_dict)

    def get_lemma_by_id(self, mongo_id):
        lemma_dict = self._mongo_db.lexunits.find_one({'_id': mongo_id})
        if lemma_dict is not None:
            return Lemma(self, lemma_dict)

# rename some of the fields in the MongoDB dictionary
SYNSET_MEMBER_REWRITES = {
    'lexunits': '_lexunits',
    'rels':     '_rels',
    }

@functools.total_ordering
class Synset(object):
    '''A class representing a synset in GermaNet.'''

    def __init__(self, germanet, db_dict):
        '''
        Creates a new Synset object from a BSON dictionary retrieved
        from MongoDB.

        Arguments:
        - `germanet`: a GermaNet object
        - `db_dict`:
        '''
        self._germanet    = germanet
        self._id          = None
        self._rels        = []
        self.category     = None
        self.gn_class     = None
        self.id           = None
        self._lexunits    = None
        self.__dict__.update((SYNSET_MEMBER_REWRITES.get(k, k), v) for (k, v) in db_dict.iteritems())

    @property
    def lemmas(self):
        return [self._germanet.get_lemma_by_id(lemma) for lemma in self._lexunits]

    @property
    def pos(self):
        return LONG_POS_TO_SHORT[self.category]

    def rels(self, rel_name = None):
        if rel_name is not None:
            return [self._germanet.get_synset_by_id(mongo_id) for (name, mongo_id) in self._rels if name == rel_name]
        else:
            return [(name, self._germanet.get_synset_by_id(mongo_id)) for (name, mongo_id) in self._rels]

    @property
    def causes(self):             return self.rels('causes')
    @property
    def entails(self):            return self.rels('entails')
    @property
    def component_holonyms(self): return self.rels('has_component_holonym')
    @property
    def component_meronyms(self): return self.rels('has_component_meronym')
    @property
    def hypernyms(self):          return self.rels('has_hypernym')
    @property
    def hyponyms(self):           return self.rels('has_hyponym')
    @property
    def member_holonyms(self):    return self.rels('has_member_holonym')
    @property
    def member_meronyms(self):    return self.rels('has_member_meronym')
    @property
    def portion_holonyms(self):   return self.rels('has_portion_holonym')
    @property
    def portion_meronyms(self):   return self.rels('has_portion_meronym')
    @property
    def substance_holonyms(self): return self.rels('has_substance_holonym')
    @property
    def substance_meronyms(self): return self.rels('has_substance_meronym')
    @property
    def entailed_bys(self):       return self.rels('is_entailed_by')
    @property
    def related_tos(self):        return self.rels('is_related_to')

    @property
    def hypernym_paths(self):
        '''
        Returns a list of paths following hypernym links from this
        synset to the GermaNet root node.
        '''
        hypernyms = self.hypernyms
        if hypernyms:
            return reduce(list.__add__, [[path + [self] for path in hypernym.hypernym_paths] for hypernym in hypernyms], [])
        else:
            return [[self]]

    @property
    def root_hypernyms(self):
        '''
        Get the topmost hypernym(s) of this synset in GermaNet.
        Mostly GNROOT.n.1
        '''
        return sorted(set([path[0] for path in self.hypernym_paths]))

    @property
    def max_depth(self):
        '''
        The length of the longest hypernym path from this synset to
        the root.
        '''
        return max([len(path) for path in self.hypernym_paths])

    @property
    def min_depth(self):
        '''
        The length of the shortest hypernym path from this synset to
        the root.
        '''
        return min([len(path) for path in self.hypernym_paths])

    def __repr__(self):
        return u'Synset({0}.{1}.{2})'.format(
            self.lemmas[0].orthForm,
            self.pos,
            self.lemmas[0].sense).encode('utf-8')

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._id == other._id
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return ((self.lemmas[0].orthForm, self.pos, self.lemmas[0].sense) <
                    (other.lemmas[0].orthForm, other.pos, other.lemmas[0].sense))
        else:
            return False

# rename some of the fields in the MongoDB dictionary
LEMMA_MEMBER_REWRITES = {
    'synset': '_synset',
    'rels':   '_rels',
    }

@functools.total_ordering
class Lemma(object):
    '''A class representing a lexical unit in GermaNet.'''

    def __init__(self, germanet, db_dict):
        '''
        Creates a new Lemma object from a BSON dictionary retrieved
        from MongoDB.

        Arguments:
        - `germanet`: a GermaNet object
        - `db_dict`:
        '''
        self._germanet    = germanet
        self._id          = None
        self._rels        = []
        self.artificial   = None
        self.category     = None
        self.examples     = None
        self.frames       = None
        self.id           = None
        self.namedEntity  = None
        self.oldOrthForm  = None
        self.oldOrthVar   = None
        self.orthForm     = None
        self.orthVar      = None
        self.paraphrases  = []
        self.sense        = None
        self.source       = None
        self.styleMarking = None
        self._synset      = None
        self.__dict__.update((LEMMA_MEMBER_REWRITES.get(k, k), v) for (k, v) in db_dict.iteritems())

    @property
    def synset(self):
        return self._germanet.get_synset_by_id(self._synset)

    @property
    def pos(self):
        return LONG_POS_TO_SHORT[self.category]

    def rels(self, rel_name = None):
        if rel_name is not None:
            return [self._germanet.get_lemma_by_id(mongo_id) for (name, mongo_id) in self._rels if name == rel_name]
        else:
            return [(name, self._germanet.get_lemma_by_id(mongo_id)) for (name, mongo_id) in self._rels]

    @property
    def antonyms(self):    return self.rels('has_antonym')
    @property
    def participles(self): return self.rels('has_participle')
    @property
    def pertainyms(self):  return self.rels('has_pertainym')

    def __repr__(self):
        return u'Lemma({0}.{1}.{2}.{3})'.format(
            self.synset.lemmas[0].orthForm,
            self.synset.pos,
            self.synset.lemmas[0].sense,
            self.orthForm).encode('utf-8')

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._id == other._id
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return ((self.orthForm, self.pos, self.sense) <
                    (other.orthForm, other.pos, other.sense))
        else:
            return False

def load_germanet(host = None, port = None, database_name = 'germanet'):
    '''
    Loads a GermaNet instance connected to the given MongoDB instance.

    Arguments:
    - `host`: the hostname of the MongoDB instance
    - `port`: the port number of the MongoDB instance
    - `database_name`: the name of the GermaNet database on the
      MongoDB instance
    '''
    client      = MongoClient(host, port)
    germanet_db = client[database_name]
    return GermaNet(germanet_db)

gn     = load_germanet()
synset = Synset(gn, germanet_db.synsets.find_one({'category':'nomen'}))
lemma  = Lemma(gn, germanet_db.lexunits.find_one())

#import utils
#a = utils.reduce_sets_or(x.keys() for x in germanet_db.lexunits.find())

# zero hits
#[x for x in germanet_db.lexunits.find() if 'orthForm' not in x['forms']]
#[x for x in germanet_db.lexunits.find() if len(x['forms']['orthForm']) != 1]
#[x for x in germanet_db.lexunits.find() if 'orthVar' in x['forms'] and len(x['forms']['orthVar']) != 1]
#[x for x in germanet_db.lexunits.find() if 'oldOrthForm' in x['forms'] and len(x['forms']['oldOrthForm']) != 1]
#[x for x in germanet_db.lexunits.find() if 'oldOrthVar' in x['forms'] and len(x['forms']['oldOrthVar']) != 1]
#[x for x in germanet_db.lexunits.find() if 'styleMarking' in x and x['styleMarking'] not in MAP_YESNO_TO_BOOL]
#[x for x in germanet_db.lexunits.find() if 'artificial' in x and x['artificial'] not in MAP_YESNO_TO_BOOL]
#[x for x in germanet_db.lexunits.find() if 'namedEntity' in x and x['namedEntity'] not in MAP_YESNO_TO_BOOL]
#[x for x in germanet_db.lexunits.find() if 'sense' in x and not x['sense'].isdigit()]

#utils.reduce_sets_or([[y[0] for y in x['rels']] for x in germanet_db.lexunits.find() if 'rels' in x])
# set([u'has_participle', u'has_pertainym', u'has_antonym'])
#>>> utils.reduce_sets_or([[y[0] for y in x['rels']] for x in germanet_db.synsets.find() if 'rels' in x])
#set([u'is_related_to', u'is_entailed_by', u'has_component_holonym', u'has_hypernym', u'has_portion_meronym', u'has_portion_holonym', u'has_substance_holonym', u'has_hyponym', u'has_member_holonym', u'causes', u'has_member_meronym', u'has_component_meronym', u'entails', u'has_substance_meronym'])

#[x for x in germanet_db.synsets.find() if 'rels' in x and len([y for y in x['rels'] if y[0] == 'has_hypernym']) > 1]

#pprint(gn.synset('Husky.n.1').hypernym_paths)
