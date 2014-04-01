============
 pygermanet
============

GermaNet API for Python.

Copyright (c) 23 March, 2014 Will Roberts <wildwilhelm@gmail.com>.

GermaNet_ is the German WordNet_, a machine-readable lexical semantic
resource which lists nouns, verbs and adjectives in German, along with
lexical relations which connect these words together into a semantic
network.  This library gives a Python interface to this resource.

.. _GermaNet: http://www.sfs.uni-tuebingen.de/GermaNet/
.. _WordNet: http://wordnet.princeton.edu/


Introduction
------------

Start GermaNet by connecting to the MongoDB_ database which contains
the lexical information.  On the local machine using the default port,
this is as simple as::

    >>> from pygermanet.germanet import load_germanet
    >>> gn = load_germanet()

You can search GermaNet for synsets containing a particular lemmatised
word form using the ``synsets`` function::

    >>> gn.synsets('gehen')
    [Synset(auseinandergehen.v.3),
     Synset(funktionieren.v.1),
     Synset(funktionieren.v.2),
     Synset(gehen.v.1),
     Synset(gehen.v.4),
     Synset(gehen.v.5),
     Synset(gehen.v.6),
     Synset(gehen.v.7),
     Synset(gehen.v.9),
     Synset(gehen.v.10),
     Synset(gehen.v.11),
     Synset(gehen.v.12),
     Synset(gehen.v.13),
     Synset(gehen.v.14),
     Synset(handeln.v.1)]

To look up synsets, you must have the canonical form of the word as it
would appear in a dictionary (head word); this module calls this word
form the lemma.  The GermaNet instance can perform lemmatisation of
words using data derived from the `Projekt deutscher Wortschatz`_::

    >>> gn.lemmatise(u'ginge')
    [u'gehen']

.. _Projekt deutscher Wortschatz: http://wortschatz.uni-leipzig.de/

Each ``Synset`` is represented by the orthographic form, part of speech,
and sense number of its first ``Lemma``; this acts as a unique
identifier for synsets.  If you know this identifier, you can also
look up a synset in GermaNet::

    >>> funktionieren = gn.synset(u'funktionieren.v.2')
    >>> funktionieren
    Synset(funktionieren.v.2)

``Synset`` objects have data members and methods::

    >>> funktionieren.hyponyms
    [Synset(vorgehen.v.1), Synset(leerlaufen.v.2)]
    >>> gn.synset('Husky.n.1').hypernym_paths
    [[Synset(GNROOT.n.1),
      Synset(Entität.n.2),
      Synset(Objekt.n.4),
      Synset(Ding.n.2),
      Synset(Teil.n.2),
      Synset(Teilmenge.n.2),
      Synset(Gruppe.n.1),
      Synset(biologische Gruppe.n.1),
      Synset(Spezies.n.1),
      Synset(Rasse.n.1),
      Synset(Tierrasse.n.1),
      Synset(Hunderasse.n.1),
      Synset(Husky.n.1)],
     [Synset(GNROOT.n.1),
      Synset(Entität.n.2),
      Synset(kognitives Objekt.n.1),
      Synset(Kategorie.n.1),
      Synset(Art.n.1),
      Synset(Spezies.n.1),
      Synset(Rasse.n.1),
      Synset(Tierrasse.n.1),
      Synset(Hunderasse.n.1),
      Synset(Husky.n.1)],
     [Synset(GNROOT.n.1),
      Synset(Entität.n.2),
      Synset(Objekt.n.4),
      Synset(natürliches Objekt.n.1),
      Synset(Wesenheit.n.1),
      Synset(Organismus.n.1),
      Synset(höheres Lebewesen.n.1),
      Synset(Tier.n.1),
      Synset(Gewebetier.n.1),
      Synset(Chordatier.n.1),
      Synset(Wirbeltier.n.1),
      Synset(Säugetier.n.1),
      Synset(Plazentatier.n.1),
      Synset(Beutegreifer.n.1),
      Synset(Landraubtier.n.1),
      Synset(hundeartiges Landraubtier.n.1),
      Synset(Hund.n.2),
      Synset(Husky.n.1)],
     [Synset(GNROOT.n.1),
      Synset(Entität.n.2),
      Synset(Objekt.n.4),
      Synset(natürliches Objekt.n.1),
      Synset(Wesenheit.n.1),
      Synset(Organismus.n.1),
      Synset(höheres Lebewesen.n.1),
      Synset(Tier.n.1),
      Synset(Haustier.n.1),
      Synset(Hund.n.2),
      Synset(Husky.n.1)]]

Each ``Synset`` contains one or more ``Lemma`` objects::

    >>> funktionieren.lemmas
    [Lemma(funktionieren.v.2.funktionieren),
     Lemma(funktionieren.v.2.funzen),
     Lemma(funktionieren.v.2.gehen),
     Lemma(funktionieren.v.2.laufen),
     Lemma(funktionieren.v.2.arbeiten)]

A given orthographic form may be represented by multiple ``Lemma``
objects belonging to different ``Synset`` objects::

    >>> gn.lemmas('brennen')
    [Lemma(brennen.v.1.brennen),
     Lemma(verbrennen.v.1.brennen),
     Lemma(brennen.v.3.brennen),
     Lemma(brennen.v.4.brennen),
     Lemma(brennen.v.5.brennen),
     Lemma(destillieren.v.1.brennen),
     Lemma(brennen.v.7.brennen),
     Lemma(brennen.v.8.brennen)]

Requirements
------------

- The GermaNet_ resource (available from the University of Tübingen)
- Python 2.7
- MongoDB_
- pymongo_
- `repoze.lru`_ (optional)

.. _MongoDB:    https://www.mongodb.org/
.. _pymongo:    http://api.mongodb.org/python/current/
.. _repoze.lru: https://pypi.python.org/pypi/repoze.lru/

Example setup::

    sudpo apt-get install mongodb
    sudo pip install pymongo repoze.lru

Setup
-----

GermaNet is distributed as a set of XML files, or as a PostgreSQL
database dump, neither of which is a convenient format for handling
from inside Python.  This library delegates responsibility for
handling the data to a MongoDB database.  As such, setup happens in
two steps.

1. Start a MongoDB instance running.  For example, the
   ``start_mongo.sh`` script contains::

       mkdir -p ./mongodb
       mongod --dbpath ./mongodb

2. Import GermaNet into the MongoDB instance.  The ``mongo_import.py``
   script needs the path to the directory that contains the GermaNet
   XML files::

       ./mongo_import.py ~/corpora/germanet/GN_V80/GN_V80_XML/

   This step only needs to be performed once, before you use
   pygermanet for the first time.

3. pygermanet can now be used by connecting to the running MongoDB
   instance.  Using default settings and connecting to a database on
   the local machine, this is accomplished with::

       >>> from pygermanet.germanet import load_germanet
       >>> gn = load_germanet()

License
-------

This README file and the source code in this library are licensed
under the MIT License (see source file LICENSE.txt for details).

The file ``baseforms_by_projekt_deutscher_wortschatz.txt.gz`` contains
data derived from the `Projekt deutscher Wortschatz`_; this database
is free for educational und researching purposes but not for
commercial use. For more information visit:
http://wortschatz.uni-leipzig.de/.


History
-------

The NLTK_ project had an API once upon a time for interacting with
GermaNet, but this has now been removed from the current NLTK
distribution.  This API was called GermaNLTK_ and was described in
some detail in `NLTK Issue 604`_.  pygermanet shamelessly imitates the
interface of this older NLTK code.

.. _NLTK:           http://www.nltk.org/
.. _GermaNLTK:      https://docs.google.com/document/d/1rdn0hOnJNcOBWEZgipdDfSyjJdnv_sinuAUSDSpiQns/edit?hl=en
.. _NLTK Issue 604: https://code.google.com/p/nltk/issues/detail?id=604

The GermaNLTK project had a script to push the content of the XML
files into a sqlite database; I haven't tested this code myself, and
the GermaNet database has changed over the years since GermaNLTK was
written.  This ``mongo_import.py`` script included in this library does much the
same thing, and could easily be adapted to use sqlite as a backend
instead of MongoDB.
