"""Interface en ligne de commande -- orchestration des six responsabilites.

Deux sous-commandes :

    diagnostic   n'ecrit aucune donnee. Interroge l'URL de depart et rapporte de
                 quoi remplir la rubrique 2 du compte rendu : statut, taille de
                 la reponse, regles du robots.txt, indices de rendu client.
                 Utilisable des l'attribution de la cible.

    collecte     la collecte complete, avec export JSONL automatique.
                 Necessite que `extraction` soit implemente.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import deque
from pathlib import Path

from pydantic import ValidationError

from . import __version__, extraction, extraction_s19
from . import config as module_config
from .acquisition import ClientHTTP, CollecteRefusee, ReessayerPlusTard
from .export import EcrivainJSONL, ecrire_echantillon_json
from .extraction import ChampObligatoireAbsent
from .journal import LOGGER, Compteurs, configurer
from .modele import Artwork, Product, Rejet
from .normalisation import Deduplicateur

# Marqueurs d'un rendu cote client dans une reponse HTTP brute.
_MOTIF_SCRIPT = re.compile(r"<script\b", re.IGNORECASE)
_MOTIF_JSONLD = re.compile(r'type=["\']application/ld\+json["\']', re.IGNORECASE)
_MOTIF_BALISE = re.compile(r"<[^>]+>")
_RACINES_SPA = ('id="root"', 'id="app"', 'id="__next"', "ng-app", "data-reactroot")


def _analyser_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(
        prog="collecteur",
        description="Collecteur Web explicable -- TP de groupe (3 eleves, 2 sites).",
    )
    analyseur.add_argument("--version", action="version", version=f"collecteur {__version__}")
    analyseur.add_argument("--config", type=Path, default=None, help="Chemin du fichier TOML.")
    analyseur.add_argument("--url", default=None, help="URL de depart (gagne sur le TOML).")
    analyseur.add_argument("--max-objets", type=int, default=None, help="Plafond d'objets.")
    analyseur.add_argument("--max-pages", type=int, default=None, help="Plafond de pages de liste.")
    analyseur.add_argument("--delai", type=float, default=None, help="Delai entre requetes (s).")
    analyseur.add_argument("--sortie", type=Path, default=None, help="Fichier JSONL de sortie.")
    analyseur.add_argument("--niveau", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    analyseur.add_argument(
        "commande",
        nargs="?",
        default="collecte",
        choices=["collecte", "diagnostic"],
    )
    return analyseur.parse_args(argv)


def _diagnostic(config: module_config.Config) -> int:
    """Rapporte ce qu'un simple GET renvoie. Aucune donnee n'est ecrite.

    La notice est explicite : le navigateur montre le DOM apres execution du
    JavaScript, il ne dit rien de la reponse HTTP. Cette commande mesure la
    reponse HTTP brute ; la comparaison avec le DOM rendu se fait ensuite dans
    les outils de developpement, et l'ecart chiffre est le diagnostic.
    """
    with ClientHTTP(config) as client:
        robots = client.robots
        print("\n=== robots.txt ===")
        print(f"  URL          : {robots.url if robots else '-'}")
        if robots and robots.contenu:
            print(f"  Crawl-delay  : {robots.crawl_delay if robots.crawl_delay else 'non declare'}")
            print(f"  URL autorisee: {robots.autorise(config.cible.url_depart)}")
            print("  --- contenu ---")
            for ligne in robots.contenu.splitlines()[:40]:
                print(f"  | {ligne}")
        else:
            print("  absent ou illisible -- aucun chemin interdit")

        reponse = client.get(config.cible.url_depart)

    texte_seul = _MOTIF_BALISE.sub(" ", reponse.texte)
    texte_seul = re.sub(r"\s+", " ", texte_seul).strip()
    racines = [marqueur for marqueur in _RACINES_SPA if marqueur in reponse.texte]

    print("\n=== Reponse HTTP brute ===")
    print(f"  URL finale        : {reponse.url}")
    print(f"  Statut            : {reponse.statut}")
    print(f"  Content-Type      : {reponse.content_type}")
    print(f"  Taille HTML       : {len(reponse.texte)} caracteres")
    print(f"  Texte hors balises: {len(texte_seul)} caracteres")
    print(f"  Balises <script>  : {len(_MOTIF_SCRIPT.findall(reponse.texte))}")
    print(f"  Blocs JSON-LD     : {len(_MOTIF_JSONLD.findall(reponse.texte))}")
    print(f"  Racines SPA       : {', '.join(racines) if racines else 'aucune'}")
    print(
        "\n  A faire maintenant : ouvrir la meme URL dans le navigateur, compter les objets\n"
        "  visibles dans le DOM, et comparer a ce que contient la reponse ci-dessus.\n"
        "  L'ecart chiffre entre les deux EST le diagnostic de la rubrique 2.2.\n"
    )
    return 0


def _urls_graines(config: module_config.Config) -> list[str]:
    """Construit les URL de depart a partir des numeros d'accession de la config.

    L'origine est celle de l'URL de depart declaree : la construction du chemin
    d'une fiche (`/art/<accession>`) reste ainsi au meme endroit que le reste de
    la connaissance de la cible, dans le module d'extraction.
    """
    origine = extraction._origine(config.cible.url_depart)
    return [extraction._url_oeuvre(accession, origine) for accession in config.collecte.graines]


def _collecte(config: module_config.Config) -> int:
    """Aiguille vers le parcours de la cible configuree.

    Les deux sites du groupe n'ont pas la meme topologie -- S32 n'a pas de page
    de liste utilisable et se parcourt de proche en proche, S19 en a et se
    parcourt par categories et par marques -- mais ils partagent tout le reste :
    client HTTP, delai, deduplication, validation, export, compteurs.
    """
    if config.cible.id.upper().lstrip("O") == "S19":
        return _collecte_s19(config)
    return _collecte_s32(config)


def _collecte_s32(config: module_config.Config) -> int:
    compteurs = Compteurs()
    deduplicateur = Deduplicateur()
    with (
        ClientHTTP(config) as client,
        EcrivainJSONL(config.sortie.fichier_jsonl) as sortie,
        EcrivainJSONL(config.sortie.fichier_rejets) as rejets,
    ):
        # Front de collecte en largeur. La recherche du site passant par un
        # chemin interdit (voir la fiche descriptive), on n'a pas de page de
        # liste : on part des graines et on suit les oeuvres liees de chaque
        # fiche, sur des chemins autorises. `deja_vu` evite de redemander une
        # fiche -- une requete inutile coute ici dix secondes.
        a_visiter: deque[str] = deque(_urls_graines(config))
        deja_vu: set[str] = set(a_visiter)

        while a_visiter and compteurs.exportes < config.collecte.max_objets:
            if compteurs.pages >= config.collecte.max_pages:
                LOGGER.warning(
                    "Plafond de %d fiches atteint : arret du parcours.", config.collecte.max_pages
                )
                break
            url = a_visiter.popleft()

            try:
                reponse = client.get(url)
            except ReessayerPlusTard as erreur:
                # Une fiche injoignable ne condamne pas le parcours entier : on
                # la note et on continue. Un refus explicite (CollecteRefusee),
                # lui, n'est pas rattrape ici et arrete tout, conformement a
                # l'enonce.
                LOGGER.warning("Fiche ignoree (%s) : %s", url, erreur)
                compteurs.erreurs_reseau += 1
                continue
            compteurs.pages += 1
            compteurs.requetes += 1

            compteurs.vus += 1
            try:
                brut = extraction.extraire_detail(reponse.texte, url)
                oeuvre = Artwork.depuis_brut(brut, reponse.url)
            except ChampObligatoireAbsent as erreur:
                rejets.ecrire(Rejet(source_url=url, motif=str(erreur), champ=erreur.champ))
                compteurs.rejeter("champ obligatoire absent", erreur.champ)
                continue
            except ValidationError as erreur:
                rejets.ecrire(Rejet(source_url=url, motif=str(erreur)))
                compteurs.rejeter("validation du modele")
                continue

            if not deduplicateur.est_nouveau(oeuvre.cle_dedup):
                compteurs.doublons += 1
                continue

            sortie.ecrire(oeuvre)
            compteurs.exportes += 1

            # Etendre le front avec les oeuvres liees encore inconnues.
            for lien in extraction.extraire_liens_lies(reponse.texte, url):
                if lien not in deja_vu:
                    deja_vu.add(lien)
                    a_visiter.append(lien)

    print("\n=== Rubrique 7 -- resultats ===")
    print(compteurs.resume())
    return 0


def _collecte_s19(config: module_config.Config) -> int:
    """Parcours de la cible S19 : pages de liste, puis fiche detail par produit.

    Deux etages, imposes par la cible et non par gout :

      - la page de liste donne le nom, le prix et l'URL, mais NI la categorie NI
        la marque, qui sont deux des six champs minimaux exiges. Il faut donc
        ouvrir la fiche de chaque produit ;
      - les 34 produits de /products ne sont pas tout le catalogue. Le site le
        repartit en 7 categories et 8 marques, chacune sur sa page de liste.
        Les parcourir est la forme que prend la pagination sur cette cible.

    La deduplication se fait sur l'identifiant du produit AVANT de demander sa
    fiche : un produit atteint a la fois par sa categorie et par sa marque ne
    doit couter qu'une requete, pas deux.
    """
    compteurs = Compteurs()
    deduplicateur = Deduplicateur()
    with (
        ClientHTTP(config) as client,
        EcrivainJSONL(config.sortie.fichier_jsonl) as sortie,
        EcrivainJSONL(config.sortie.fichier_rejets) as rejets,
    ):
        listes: deque[str] = deque([config.cible.url_depart])
        listes_vues: set[str] = set(listes)

        while listes and compteurs.exportes < config.collecte.max_objets:
            if compteurs.pages >= config.collecte.max_pages:
                LOGGER.warning(
                    "Plafond de %d pages de liste atteint : arret du parcours.",
                    config.collecte.max_pages,
                )
                break
            url_liste = listes.popleft()

            try:
                reponse_liste = client.get(url_liste)
            except ReessayerPlusTard as erreur:
                LOGGER.warning("Page de liste ignoree (%s) : %s", url_liste, erreur)
                compteurs.erreurs_reseau += 1
                continue
            compteurs.pages += 1
            compteurs.requetes += 1

            for apercu in extraction_s19.extraire_liste(reponse_liste.texte, reponse_liste.url):
                if compteurs.exportes >= config.collecte.max_objets:
                    break

                # `vus` compte tout objet RENCONTRE, y compris les redites :
                # c'est ce qui tient l'invariant du rapport
                # vus = exportes + rejetes + doublons. L'incrementer apres la
                # deduplication ferait etat de 34 objets vus pour 68 doublons,
                # et le tableau de la rubrique 7 ne s'additionnerait plus.
                compteurs.vus += 1

                # Dedupliquer AVANT la requete de detail, pas apres : c'est ce
                # qui rend gratuit le fait d'atteindre un produit deux fois.
                if not deduplicateur.est_nouveau(apercu["item_id"]):
                    compteurs.doublons += 1
                    continue

                url_produit = apercu["url"]
                brut = apercu

                if config.collecte.suivre_detail:
                    try:
                        reponse_detail = client.get(url_produit)
                    except ReessayerPlusTard as erreur:
                        LOGGER.warning("Fiche ignoree (%s) : %s", url_produit, erreur)
                        compteurs.erreurs_reseau += 1
                        continue
                    compteurs.requetes += 1
                    try:
                        brut = extraction_s19.extraire_detail(
                            reponse_detail.texte, reponse_detail.url
                        )
                    except ChampObligatoireAbsent as erreur:
                        rejets.ecrire(
                            Rejet(source_url=url_produit, motif=str(erreur), champ=erreur.champ)
                        )
                        compteurs.rejeter("champ obligatoire absent", erreur.champ)
                        continue
                    url_produit = reponse_detail.url

                try:
                    produit = Product.depuis_brut(brut, url_produit)
                except ChampObligatoireAbsent as erreur:
                    rejets.ecrire(
                        Rejet(source_url=url_produit, motif=str(erreur), champ=erreur.champ)
                    )
                    compteurs.rejeter("champ obligatoire absent", erreur.champ)
                    continue
                except ValidationError as erreur:
                    rejets.ecrire(Rejet(source_url=url_produit, motif=str(erreur)))
                    compteurs.rejeter("validation du modele")
                    continue

                sortie.ecrire(produit)
                compteurs.exportes += 1

            # Etendre le front avec les pages de categorie et de marque.
            for lien in extraction_s19.extraire_liens_listes(
                reponse_liste.texte, reponse_liste.url
            ):
                if lien not in listes_vues:
                    listes_vues.add(lien)
                    listes.append(lien)

    print("\n=== Rubrique 7 -- resultats ===")
    print(compteurs.resume())
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = _analyser_arguments(argv)
    config = module_config.charger(
        arguments.config,
        cible_url_depart=arguments.url,
        collecte_max_objets=arguments.max_objets,
        collecte_max_pages=arguments.max_pages,
        collecte_delai_secondes=arguments.delai,
        sortie_fichier_jsonl=arguments.sortie,
        journal_niveau=arguments.niveau,
    )
    configurer(config.journal.niveau, config.journal.fichier)

    try:
        config.valider()
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2

    try:
        if arguments.commande == "diagnostic":
            return _diagnostic(config)
        code = _collecte(config)
    except CollecteRefusee as refus:
        # Chemin volontairement distinct : un refus n'est pas un bug du
        # collecteur, c'est un resultat a documenter dans le rapport.
        print(f"\nCOLLECTE ARRETEE -- refus de la cible :\n  {refus}\n", file=sys.stderr)
        return 3
    except ReessayerPlusTard as erreur:
        print(
            f"\nCOLLECTE ARRETEE -- erreur temporaire persistante :\n  {erreur}\n", file=sys.stderr
        )
        return 4

    if config.sortie.fichier_jsonl.exists():
        from .export import lire_jsonl

        ecrire_echantillon_json(
            config.sortie.fichier_echantillon.with_suffix(".json"),
            lire_jsonl(config.sortie.fichier_jsonl),
            limite=config.sortie.taille_echantillon,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
