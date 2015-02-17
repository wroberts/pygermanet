#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
germanet.py
(c) Will Roberts  21 March, 2014

GermaNet interface.
'''

from __future__ import division
from builtins import dict, int
from functools import reduce
from pymongo import MongoClient
import functools
import math
import sys
try:
    import repoze.lru
except ImportError:
    pass

LONG_POS_TO_SHORT = {
    'verben': 'v',
    'nomen':  'n',
    'adj':    'j',
    }

SHORT_POS_TO_LONG  = dict((v, k) for (k, v) in LONG_POS_TO_SHORT.items())

DEFAULT_CACHE_SIZE = 100

GERMANET_METAINFO_IGNORE_KEYS = set(['_id'])

class GermaNet(object):
    '''A class representing the GermaNet database.'''

    def __init__(self, mongo_db, cache_size = DEFAULT_CACHE_SIZE):
        '''
        Creates a new GermaNet object.

        Arguments:
        - `mongo_db`: a pymongo.database.Database object containing
          the GermaNet lexicon
        '''
        self._mongo_db      = mongo_db
        self._lemma_cache   = None
        self._synset_cache  = None
        self.max_min_depths = {}
        try:
            self.__dict__.update((k, v) for (k, v)
                                 in self._mongo_db.metainfo.find_one().items()
                                 if k not in GERMANET_METAINFO_IGNORE_KEYS)
        except AttributeError:
            # ignore error generated if metainfo is not included in
            # the mongo DB
            pass
        try:
            self._lemma_cache  = repoze.lru.LRUCache(cache_size)
            self._synset_cache = repoze.lru.LRUCache(cache_size)
        except NameError:
            pass

    @property
    def cache_size(self):
        '''
        Return the current cache size used to reduce the number of
        database access operations.
        '''
        if self._lemma_cache is not None:
            return self._lemma_cache.size
        return 0

    @cache_size.setter
    def cache_size(self, new_value):
        '''
        Set the cache size used to reduce the number of database
        access operations.
        '''
        if type(new_value) == int and 0 < new_value:
            if self._lemma_cache is not None:
                self._lemma_cache  = repoze.lru.LRUCache(new_value)
                self._synset_cache = repoze.lru.LRUCache(new_value)

    def all_lemmas(self):
        '''
        A generator over all the lemmas in the GermaNet database.
        '''
        for lemma_dict in self._mongo_db.lexunits.find():
            yield Lemma(self, lemma_dict)

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

    def all_synsets(self):
        '''
        A generator over all the synsets in the GermaNet database.
        '''
        for synset_dict in self._mongo_db.synsets.find():
            yield Synset(self, synset_dict)

    def synsets(self, lemma, pos = None):
        '''
        Looks up synsets in the GermaNet database.

        Arguments:
        - `lemma`:
        - `pos`:
        '''
        return sorted(set(lemma_obj.synset
                          for lemma_obj in self.lemmas(lemma, pos)))

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
        if not sensenum.isdigit() or pos not in SHORT_POS_TO_LONG:
            return None
        sensenum   = int(sensenum, 10)
        pos        = SHORT_POS_TO_LONG[pos]
        lemma_dict = self._mongo_db.lexunits.find_one({'orthForm': lemma,
                                                       'category': pos,
                                                       'sense':    sensenum})
        if lemma_dict:
            return Lemma(self, lemma_dict).synset

    def get_synset_by_id(self, mongo_id):
        '''
        Builds a Synset object from the database entry with the given
        ObjectId.

        Arguments:
        - `mongo_id`: a bson.objectid.ObjectId object
        '''
        cache_hit = None
        if self._synset_cache is not None:
            cache_hit = self._synset_cache.get(mongo_id)
        if cache_hit is not None:
            return cache_hit
        synset_dict = self._mongo_db.synsets.find_one({'_id': mongo_id})
        if synset_dict is not None:
            synset = Synset(self, synset_dict)
            if self._synset_cache is not None:
                self._synset_cache.put(mongo_id, synset)
            return synset

    def get_lemma_by_id(self, mongo_id):
        '''
        Builds a Lemma object from the database entry with the given
        ObjectId.

        Arguments:
        - `mongo_id`: a bson.objectid.ObjectId object
        '''
        cache_hit = None
        if self._lemma_cache is not None:
            cache_hit = self._lemma_cache.get(mongo_id)
        if cache_hit is not None:
            return cache_hit
        lemma_dict = self._mongo_db.lexunits.find_one({'_id': mongo_id})
        if lemma_dict is not None:
            lemma = Lemma(self, lemma_dict)
            if self._lemma_cache is not None:
                self._lemma_cache.put(mongo_id, lemma)
            return lemma

    def lemmatise(self, word):
        '''
        Tries to find the base form (lemma) of the given word, using
        the data provided by the Projekt deutscher Wortschatz.  This
        method returns a list of potential lemmas.

        >>> gn.lemmatise(u'Männer')
        [u'Mann']
        >>> gn.lemmatise(u'XYZ123')
        [u'XYZ123']
        '''
        lemmas = list(self._mongo_db.lemmatiser.find({'word': word}))
        if lemmas:
            return [lemma['lemma'] for lemma in lemmas]
        else:
            return [word]

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
        self.infocont     = 0.
        self._lexunits    = None
        self.__dict__.update((SYNSET_MEMBER_REWRITES.get(k, k), v)
                             for (k, v) in db_dict.items())

    @property
    def lemmas(self):
        '''
        Returns the list of Lemma objects contained in this Synset.
        '''
        return [self._germanet.get_lemma_by_id(lemma)
                for lemma in self._lexunits]

    @property
    def pos(self):
        '''
        Returns the part of speech of this Synset as a single
        character.  Nouns are represented by 'n', verbs by 'v', and
        adjectives by 'j'.
        '''
        return LONG_POS_TO_SHORT[self.category]

    def rels(self, rel_name = None):
        '''
        Returns a list of lexical relations in this Synset.  If
        `rel_name` is specified, returns a list of Synsets which are
        reachable from this one by relations with the given name.  If
        `rel_name` is not specified, returns a list of all the lexical
        relations of this Synset, as tuples of (rel_name, synset).

        Arguments:
        - `rel_name`:
        '''
        if rel_name is not None:
            return [self._germanet.get_synset_by_id(mongo_id)
                    for (name, mongo_id) in self._rels if name == rel_name]
        else:
            return [(name, self._germanet.get_synset_by_id(mongo_id))
                    for (name, mongo_id) in self._rels]

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
            return reduce(list.__add__, [[path + [self]
                                          for path in hypernym.hypernym_paths]
                                         for hypernym in hypernyms], [])
        else:
            return [[self]]

    @property
    def hypernym_distances(self):
        '''
        Returns a list of synsets on the path from this synset to the root
        node, counting the distance of each node on the way.
        '''
        retval = dict()
        for (synset, dist) in reduce(
                set.union,
                [[(synset, idx) for (idx, synset) in enumerate(reversed(path))]
                 for path in self.hypernym_paths],
                set()):
            if synset not in retval or dist < retval[synset]:
                retval[synset] = dist
        return set(retval.items())

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
        reprstr = u'Synset({0}.{1}.{2})'.format(
            self.lemmas[0].orthForm,
            self.pos,
            self.lemmas[0].sense)
        if sys.version_info.major < 3:
            return reprstr.encode('utf-8')
        return reprstr

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
                    (other.lemmas[0].orthForm, other.pos,
                     other.lemmas[0].sense))
        else:
            return False

    def _common_hypernyms(self, other):
        '''Helper method for common_hypernyms.'''
        if not isinstance(other, Synset):
            return dict()
        self_dists  = dict(self.hypernym_distances)
        other_dists = dict(other.hypernym_distances)
        common      = dict((synset, 0) for synset in (set(self_dists) &
                                                      set(other_dists)))
        # update the distance values
        for synset in common:
            common[synset] = self_dists[synset] + other_dists[synset]
        return common

    def common_hypernyms(self, other):
        '''
        Finds the set of hypernyms common to both this synset and
        ``other``.

        Arguments:
        - `other`: another synset
        '''
        return set(synset for (synset, dist) in
                   self._common_hypernyms(other).items())

    def lowest_common_hypernyms(self, other):
        '''
        Finds the set of hypernyms common to both this synset and
        ``other`` which are lowest in the GermaNet hierarchy (furthest
        away from GNROOT).

        Arguments:
        - `other`: another synset
        '''
        if not isinstance(other, Synset):
            return set()
        self_hypers   = set(synset for path in self.hypernym_paths
                            for synset in path)
        other_hypers  = set(synset for path in other.hypernym_paths
                            for synset in path)
        common_hypers = self_hypers & other_hypers
        common_hypers = [(synset.min_depth, synset)
                         for synset in common_hypers]
        if not common_hypers:
            return set()
        max_depth     = max(x[0] for x in common_hypers)
        return set(synset for (depth, synset) in common_hypers
                   if depth == max_depth)

    def nearest_common_hypernyms(self, other):
        '''
        Finds the set of hypernyms common to both this synset and
        ``other`` which are closest to the two synsets (the hypernyms
        which the minimum path length joining the two synsets passes
        through).

        Arguments:
        - `other`: another synset
        '''
        common_hypers = [(dist, synset) for (synset, dist) in
                         list(self._common_hypernyms(other).items())]
        if not common_hypers:
            return set()
        min_dist = min(x[0] for x in common_hypers)
        return set(synset for (dist, synset) in common_hypers
                   if dist == min_dist)

    def shortest_path_length(self, other):
        '''
        Returns the length of the shortest path linking this synset with
        ``other`` via a common hypernym.  If no path exists, the
        method returns None.

        Arguments:
        - `other`:
        '''
        if self == other:
            return 0
        common_hypers = self._common_hypernyms(other)
        if not common_hypers:
            return None
        return min(common_hypers.values())

    # --------------------------------------------------
    #  Semantic similarity
    # --------------------------------------------------

    def sim_lch(self, other):
        '''
        Computes the Leacock-Chodorow similarity score between this synset
        and the synset ``other``.

        Arguments:
        - `other`:
        '''
        if not isinstance(other, Synset):
            return 0.
        if self.category != other.category:
            return 0.
        path_length = self.shortest_path_length(other)
        if path_length is None:
            return 0.
        return -math.log(
            (path_length + 1) /
            (2. * self._germanet.max_min_depths[self.category]))

    def sim_res(self, other):
        '''
        Computes the Resnik similarity score between this synset and the
        synset ``other``.

        Arguments:
        - `other`:
        '''
        if not isinstance(other, Synset):
            return 0.
        # find the lowest concept which subsumes both this synset and
        # ``other``;
        #common_hypers = self.lowest_common_hypernyms(other)
        # specifically, we choose the hypernym "closest" to this
        # synset and ``other``, not the hypernym which is furthest
        # away from GNROOT (as is done by lowest_common_hypernyms)
        common_hypers = self.nearest_common_hypernyms(other)
        if not common_hypers:
            return 0.
        # infocont is actually the probability
        infoconts = [synset.infocont for synset in common_hypers]
        # filter out zero counts
        infoconts = [x for x in infoconts if x != 0]
        if not infoconts:
            return 0.
        # we take the lowest probability subsumer
        least_prob = min(infoconts)
        # information content is the negative log
        return -math.log(least_prob)

    def dist_jcn(self, other):
        '''
        Computes the Jiang-Conrath semantic distance between this synset
        and the synset ``other``.

        Arguments:
        - `other`:
        '''
        ic1 = self.infocont
        ic2 = other.infocont
        if ic1 == 0 or ic2 == 0:
            return 0.
        ic1 = -math.log(ic1)
        ic2 = -math.log(ic2)
        ic_lcs = self.sim_res(other)
        return ic1 + ic2 - 2. * ic_lcs

    def sim_lin(self, other):
        '''
        Computes the Lin similarity score between this synset and the
        synset ``other``.

        Arguments:
        - `other`:
        '''
        ic1 = self.infocont
        ic2 = other.infocont
        if ic1 == 0 or ic2 == 0:
            return 0.
        ic1 = -math.log(ic1)
        ic2 = -math.log(ic2)
        ic_lcs = self.sim_res(other)
        return 2. * ic_lcs / (ic1 + ic2)

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
        self.__dict__.update((LEMMA_MEMBER_REWRITES.get(k, k), v)
                             for (k, v) in db_dict.items())

    @property
    def synset(self):
        '''Returns the Synset that this Lemma is contained in.'''
        return self._germanet.get_synset_by_id(self._synset)

    @property
    def pos(self):
        '''
        Returns the part of speech of this Lemma as a single
        character.  Nouns are represented by 'n', verbs by 'v', and
        adjectives by 'j'.
        '''
        return LONG_POS_TO_SHORT[self.category]

    def rels(self, rel_name = None):
        '''
        Returns a list of lexical relations in this Lemma.  If
        `rel_name` is specified, returns a list of Lemmas which are
        reachable from this one by relations with the given name.  If
        `rel_name` is not specified, returns a list of all the lexical
        relations of this Lemma, as tuples of (rel_name, lemma).

        Arguments:
        - `rel_name`:
        '''
        if rel_name is not None:
            return [self._germanet.get_lemma_by_id(mongo_id)
                    for (name, mongo_id) in self._rels if name == rel_name]
        else:
            return [(name, self._germanet.get_lemma_by_id(mongo_id))
                    for (name, mongo_id) in self._rels]

    @property
    def antonyms(self):    return self.rels('has_antonym')
    @property
    def participles(self): return self.rels('has_participle')
    @property
    def pertainyms(self):  return self.rels('has_pertainym')

    def __repr__(self):
        reprstr = u'Lemma({0}.{1}.{2}.{3})'.format(
            self.synset.lemmas[0].orthForm,
            self.synset.pos,
            self.synset.lemmas[0].sense,
            self.orthForm)
        if sys.version_info.major < 3:
            return reprstr.encode('utf-8')
        return reprstr

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
