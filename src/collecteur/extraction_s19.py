"""Extraction -- fiches produit d'Automation Exercise (cible S19).

Second des deux modules qui connaissent une cible. Le reste du collecteur
l'ignore : acquisition, normalisation, modele, export et journalisation sont
communs aux deux sites.

Ancrage retenu, dans l'ordre de preference du projet :

    1. donnee structuree du site   absente ici (ni JSON-LD, ni bloc injecte)
    2. attribut de donnee          <- retenu : data-product-id, input#product_id
    3. role ou libelle accessible  absent
    4. structure du document       <- retenu en second : h2 = prix, p = nom
    5. classe CSS utilitaire       evite

Diagnostic de la cible, verifie et non suppose :

  - la reponse HTTP brute de /products contient les 34 produits. Aucun rendu
    JavaScript n'est necessaire, donc aucun navigateur : c'est ce qui exclut
    Playwright et crawl4ai du perimetre (voir docs/architecture.md) ;
  - le site ne publie pas de robots.txt : /robots.txt repond 302 vers la page
    d'accueil. Aucun chemin n'est donc interdit et aucun Crawl-delay n'est
    declare. L'absence de regle n'est pas une permission de marteler le
    serveur : le delai configure s'applique quand meme, entierement a notre
    charge ;
  - le site se declare lui-meme terrain d'entrainement a l'automatisation
    (« This is for automation practice »), ce qui rend la collecte legitime.

Piege de structure, verifie sur la page enregistree : chaque produit apparait
DEUX fois dans le HTML de la liste, une fois dans `.productinfo` et une fois
dans `.product-overlay` affiche au survol. Un selecteur pose sur `h2` ou sur
`[data-product-id]` compte donc 68 noeuds pour 34 produits. On itere sur les
blocs `.product-image-wrapper` et on ne lit que `.productinfo`.

Contrat de ce module : il retourne des dictionnaires de chaines BRUTES, telles
que la page les porte. Il ne convertit rien -- ni prix, ni devise. La
normalisation appartient a `normalisation`, ce qui permet de tester les regles
metier sans HTML.

Un champ obligatoire introuvable leve `ChampObligatoireAbsent`, que le pipeline
inscrit en rejet avec son motif. Jamais un enregistrement silencieusement
incomplet.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .extraction import ChampObligatoireAbsent, analyser

# « Category: Women > Tops » -- on ne garde que ce qui suit le libelle.
_MOTIF_CATEGORIE = re.compile(r"^\s*category\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL)


def _texte(noeud: Tag | None) -> str | None:
    """Texte d'un noeud, ou None si le noeud est absent.

    L'absence de noeud et le noeud vide restent distincts : le premier rend
    None (le champ n'existe pas sur la page), le second une chaine vide que la
    normalisation traduira a son tour.
    """
    return noeud.get_text(" ", strip=True) if noeud is not None else None


def _valeur_apres_libelle(bloc: Tag, libelle: str) -> str | None:
    """Lit « <p><b>Brand:</b> Polo</p> », c'est-a-dire la valeur suivant un <b>.

    La fiche detail range plusieurs champs sous cette meme forme (Availability,
    Condition, Brand). Les distinguer par leur libelle est plus stable que par
    leur rang : le site peut inserer une ligne sans casser la lecture.
    """
    attendu = libelle.rstrip(":").strip().lower()
    for gras in bloc.find_all("b"):
        if gras.get_text(strip=True).rstrip(":").strip().lower() == attendu:
            parent = gras.parent
            if parent is None:
                continue
            valeur = parent.get_text(" ", strip=True)
            # Retirer le libelle lui-meme, en tete du texte du <p>.
            sans_libelle = valeur[len(gras.get_text(" ", strip=True)) :].strip()
            return sans_libelle or None
    return None


def extraire_liste(html: str, url_base: str) -> list[dict[str, Any]]:
    """Extrait les produits d'une page de liste (accueil, categorie ou marque).

    Rend un dictionnaire par produit, avec l'identifiant, le nom, le prix
    affiche tel quel (« Rs. 500 ») et l'URL de la fiche. La categorie et la
    marque ne figurent PAS sur la page de liste : elles ne se lisent que sur la
    fiche detail, d'ou le second appel a `extraire_detail`.
    """
    soup = analyser(html)
    produits: list[dict[str, Any]] = []

    for bloc in soup.select(".product-image-wrapper"):
        # Un seul des deux exemplaires du produit : celui de `.productinfo`.
        info = bloc.select_one(".productinfo")
        if info is None:
            continue

        lien = bloc.select_one('a[href^="/product_details/"]')
        href = lien.get("href") if lien is not None else None
        if not href:
            # Sans URL de fiche, le produit n'est ni identifiable ni verifiable.
            continue

        marqueur = info.select_one("[data-product-id]")
        identifiant = marqueur.get("data-product-id") if marqueur is not None else None
        if not identifiant:
            # Repli sur le dernier segment de l'URL, qui porte le meme numero.
            identifiant = str(href).rstrip("/").rsplit("/", 1)[-1]

        produits.append(
            {
                "item_id": str(identifiant),
                "name": _texte(info.find("p")),
                "prix_affiche": _texte(info.find("h2")),
                "url": urljoin(url_base, str(href)),
            }
        )

    return produits


def extraire_detail(html: str, url_base: str) -> dict[str, Any]:
    """Extrait les champs d'une fiche produit. UN dictionnaire de chaines brutes.

    `name` et l'identifiant sont obligatoires : leur absence n'est pas un
    produit incomplet a exporter en silence, c'est le signe que la structure de
    la page a change. On leve alors `ChampObligatoireAbsent`, que le pipeline
    inscrira en rejet avec son motif.

    `category` et `brand` sont des champs minimaux de la fiche de cible et ne
    sont disponibles QUE sur cette page -- la page de liste ne les porte pas.
    """
    soup = analyser(html)
    bloc = soup.select_one(".product-information")
    if bloc is None:
        raise ChampObligatoireAbsent("product-information", url_base)

    nom = _texte(bloc.find("h2"))
    if not nom:
        raise ChampObligatoireAbsent("name", url_base)

    champ_id = soup.select_one("input#product_id")
    identifiant = champ_id.get("value") if champ_id is not None else None
    if not identifiant:
        identifiant = str(url_base).rstrip("/").rsplit("/", 1)[-1]
    if not identifiant:
        raise ChampObligatoireAbsent("item_id", url_base)

    # « Category: Women > Tops » : premier <p> qui porte ce libelle.
    categorie = None
    for paragraphe in bloc.find_all("p"):
        trouve = _MOTIF_CATEGORIE.match(paragraphe.get_text(" ", strip=True))
        if trouve:
            categorie = trouve.group(1)
            break

    return {
        "item_id": str(identifiant),
        "name": nom,
        "prix_affiche": _texte(bloc.select_one("span span")),
        "category": categorie,
        "brand": _valeur_apres_libelle(bloc, "Brand"),
        "url": url_base,
    }


def extraire_liens_listes(html: str, url_base: str) -> list[str]:
    """Renvoie les URL des pages de categorie et de marque.

    C'est l'equivalent de la pagination pour cette cible : la fiche de cible
    exige de couvrir « categories, marques, recherche, detail ». Le site ne
    pagine pas /products (les 34 produits tiennent sur une page) mais repartit
    son catalogue en 7 categories et 8 marques, chacune sur sa propre page de
    liste. Les parcourir est ce qui donne acces a plus de produits que la seule
    page d'accueil, et ce qui remplit le champ `category` cote source.
    """
    soup: BeautifulSoup = analyser(html)
    liens: list[str] = []
    vus: set[str] = set()

    for ancre in soup.select('a[href*="/category_products/"], a[href*="/brand_products/"]'):
        href = ancre.get("href")
        if not href:
            continue
        absolue = urljoin(url_base, str(href))
        if absolue not in vus:
            vus.add(absolue)
            liens.append(absolue)

    return liens
