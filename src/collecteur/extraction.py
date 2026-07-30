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

import json
from typing import Any
from urllib.parse import urlsplit

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


def _bloc_next_data(html: str) -> dict[str, Any]:
    """Extrait et parse le bloc `__NEXT_DATA__` que Next.js injecte dans la page.

    La cible rend ses fiches d'oeuvre cote serveur : toute la donnee tient dans
    ce bloc JSON de la reponse HTTP, ce qui rend inutile le pilotage d'un
    navigateur. Le bloc est retrouve par le parseur, pas par une regex : une
    accolade a l'interieur d'une chaine JSON ne doit pas tromper la recherche.
    """
    balise = analyser(html).find("script", id="__NEXT_DATA__")
    if balise is None or not balise.string:
        raise ChampObligatoireAbsent("__NEXT_DATA__", "")
    return json.loads(balise.string)


def _origine(url: str) -> str:
    parties = urlsplit(url)
    return f"{parties.scheme}://{parties.netloc}"


def _url_oeuvre(accession: str, origine: str) -> str:
    return f"{origine}/art/{accession}"


def _attribution(creators: list[dict[str, Any]] | None) -> str | None:
    """Assemble la ligne d'auteur affichee, ou None si l'oeuvre est anonyme.

    Le musee attribue une oeuvre a zero, un ou plusieurs createurs. Le champ
    `description` porte la ligne complete telle qu'affichee (« John Singleton
    Copley (American, ...) ») ; `name` en est le repli quand elle manque.
    """
    if not creators:
        return None
    lignes = [c.get("description") or c.get("name") for c in creators]
    lignes = [ligne for ligne in lignes if ligne]
    return "; ".join(lignes) if lignes else None


def extraire_detail(html: str, url_base: str) -> dict[str, Any]:
    """Extrait les champs d'une fiche d'oeuvre. UN dictionnaire de chaines brutes.

    `title` et le numero d'accession sont obligatoires : leur absence n'est pas
    une oeuvre incomplete a exporter en silence, c'est le signe que la structure
    de la page a change. On leve alors `ChampObligatoireAbsent`, que le pipeline
    inscrira en rejet avec son motif.
    """
    props = _bloc_next_data(html).get("props", {}).get("pageProps", {})
    art = props.get("artworkData")
    if not art:
        raise ChampObligatoireAbsent("artworkData", url_base)

    accession = art.get("accession_number")
    if not accession:
        raise ChampObligatoireAbsent("accession_number", url_base)
    if not art.get("title"):
        raise ChampObligatoireAbsent("title", url_base)

    return {
        "item_id": str(accession),
        "title": art.get("title"),
        "artist": _attribution(art.get("creators")),
        "date_text": art.get("date_text") or art.get("creation_date"),
        "medium": art.get("technique") or art.get("medium_mapped"),
        "url": art.get("url") or _url_oeuvre(str(accession), _origine(url_base)),
    }


def extraire_liens_lies(html: str, url_base: str) -> list[str]:
    """Renvoie les URL des oeuvres liees, pour alimenter le front de collecte.

    La recherche du site passe par `/api`, chemin interdit par le robots.txt
    (voir docs/fiche_descriptive.md, section 2) : on ne peut donc pas parcourir
    une page de liste. Le catalogue reste neanmoins explorable de proche en
    proche -- chaque fiche declare ses oeuvres voisines dans `artworksForSeeAlso`.
    C'est ce lien, servi cote serveur et sur un chemin autorise, qui remplace la
    pagination classique.
    """
    props = _bloc_next_data(html).get("props", {}).get("pageProps", {})
    origine = _origine(url_base)
    liens, vus = [], set()
    for oeuvre in props.get("artworksForSeeAlso") or []:
        accession = oeuvre.get("accession_number")
        if accession and accession not in vus:
            vus.add(accession)
            liens.append(_url_oeuvre(str(accession), origine))
    return liens
