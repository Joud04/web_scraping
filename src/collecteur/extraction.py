"""Extraction -- HTML ou DOM vers dictionnaires bruts.

    ===================================================================
    MODULE VOLONTAIREMENT VIDE TANT QUE LA CIBLE N'EST PAS ATTRIBUEE.
    ===================================================================

C'est ici, et seulement ici, que vivent les selecteurs. Ecrire un selecteur
avant d'avoir regarde la page reviendrait a decider de l'acquisition avant le
diagnostic, ce que la notice du formateur sanctionne explicitement :

    « Ma decision d'acquisition decoule-t-elle de ces observations, ou
      l'avais-je prise avant de regarder ? »

Ordre de travail, une fois la cible connue :

  1. enregistrer une page de liste et une page de detail dans
     tests/fixtures/ -- c'est ce qui rendra la verification rejouable sans
     reseau, exigence de la rubrique 6 ;
  2. comparer la reponse HTTP brute et le DOM rendu, chiffres a l'appui,
     et consigner l'ecart dans docs/fiche_descriptive.md ;
  3. choisir l'ancrage des DEUX champs les plus importants, et noter tout de
     suite l'alternative ecartee -- c'est la rubrique 5 du rapport, et elle se
     redige mal a posteriori ;
  4. seulement alors, ecrire les fonctions ci-dessous.

Contrat de ce module : il retourne des dictionnaires de chaines BRUTES, telles
que la page les affiche. Il ne convertit rien. La conversion appartient a
`normalisation`, ce qui permet de tester les regles metier sans HTML.

Regle d'ancrage, valable quelle que soit la cible, par ordre de preference :

    1. donnee structuree du site   JSON-LD, microdonnees, reponse JSON interne
    2. attribut de donnee          data-testid, data-sku, itemprop
    3. role ou libelle accessible  role="listitem", aria-label
    4. structure du document       "le second <td> de la ligne"
    5. classe CSS utilitaire       a eviter : change a chaque refonte du theme

Un champ obligatoire introuvable doit produire un signal visible -- une
exception `ChampObligatoireAbsent` remontee au pipeline, qui l'inscrira en
rejet avec son motif. Jamais un enregistrement silencieusement incomplet :
c'est ecrit noir sur blanc dans l'enonce.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


class ChampObligatoireAbsent(ValueError):
    """Un ancrage a disparu. Bruyant par construction, jamais silencieux."""

    def __init__(self, champ: str, url: str) -> None:
        super().__init__(f"Champ obligatoire '{champ}' introuvable sur {url}")
        self.champ = champ
        self.url = url


def analyser(html: str) -> BeautifulSoup:
    """Point d'entree unique du parsing, pour n'avoir qu'un endroit a changer.

    `lxml` est retenu pour sa tolerance aux documents mal fermes, frequents sur
    les sites editoriaux. Passer a `html.parser` (sans dependance) ou a
    `selectolax` (plus rapide) ne demanderait de modifier que cette ligne.
    """
    return BeautifulSoup(html, "lxml")


def extraire_liste(html: str, url_base: str) -> list[dict[str, Any]]:
    """Extrait les objets d'une page de liste. UN dictionnaire par objet vu.

    A implementer apres le diagnostic de la cible.
    """
    raise NotImplementedError("Cible non attribuee. Voir l'ordre de travail en tete de ce module.")


def extraire_detail(html: str, url_base: str) -> dict[str, Any]:
    """Extrait les champs supplementaires d'une page de detail.

    A implementer apres le diagnostic de la cible. A supprimer si la cible n'a
    pas de page de detail (S14, S18, S61) -- une fonction morte dans un depot
    rendu est un point perdu au critere « architecture ».
    """
    raise NotImplementedError("Cible non attribuee. Voir l'ordre de travail en tete de ce module.")


def url_page_suivante(html: str, url_base: str) -> str | None:
    """Renvoie l'URL de la page suivante, ou None si c'est la derniere.

    Preferer un signal declare par la page (`<a rel="next">`) a un compteur
    incremente jusqu'au 404 : le premier s'arrete tout seul, le second demande
    une requete inutile pour decouvrir qu'il n'y avait plus rien.

    A implementer apres le diagnostic. A supprimer si la cible n'a pas de
    pagination.
    """
    raise NotImplementedError("Cible non attribuee. Voir l'ordre de travail en tete de ce module.")
