You can search GermaNet for synsets containing a particular word using
the =synsets= function::

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

Each =Synset= is represented by the orthographic form, part of speech,
and sense number of its first =Lemma=; this acts as a unique
identifier for synsets.  If you know this identifier, you can also
look up a synset in GermaNet::

    >>> funktionieren = gn.synset(u'funktionieren.v.2')
    >>> funktionieren
    Synset(funktionieren.v.2)

=Synset= objects have data members and methods::

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

Each =Synset= contains one or more =Lemma= objects::

    >>> funktionieren.lemmas
    [Lemma(funktionieren.v.2.funktionieren),
     Lemma(funktionieren.v.2.funzen),
     Lemma(funktionieren.v.2.gehen),
     Lemma(funktionieren.v.2.laufen),
     Lemma(funktionieren.v.2.arbeiten)]

A given orthographic form may be represented by multiple =Lemma=
objects belonging to different =Synset= objects::

    >>> gn.lemmas('brennen')
    [Lemma(brennen.v.1.brennen),
     Lemma(verbrennen.v.1.brennen),
     Lemma(brennen.v.3.brennen),
     Lemma(brennen.v.4.brennen),
     Lemma(brennen.v.5.brennen),
     Lemma(destillieren.v.1.brennen),
     Lemma(brennen.v.7.brennen),
     Lemma(brennen.v.8.brennen)]
