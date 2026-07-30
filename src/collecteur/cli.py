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
from pathlib import Path

from . import __version__
from . import config as module_config
from .acquisition import ClientHTTP, CollecteRefusee, ReessayerPlusTard
from .export import EcrivainJSONL, ecrire_echantillon_json
from .journal import Compteurs, configurer

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


def _collecte(config: module_config.Config) -> int:
    compteurs = Compteurs()
    with (
        ClientHTTP(config) as client,
        EcrivainJSONL(config.sortie.fichier_jsonl) as sortie,
        EcrivainJSONL(config.sortie.fichier_rejets) as rejets,
    ):
        # ------------------------------------------------------------------
        # A implementer apres l'attribution de la cible.
        #
        #   1. parcourir les pages de liste avec extraction.extraire_liste,
        #      en s'arretant sur max_pages ou sur l'absence de page suivante ;
        #   2. pour chaque objet vu : compteurs.vus += 1 ;
        #   3. suivre la page de detail si config.collecte.suivre_detail ;
        #   4. normaliser, puis valider par le modele Pydantic ;
        #   5. deduplicateur.est_nouveau(objet.cle_dedup) ;
        #   6. sortie.ecrire(objet) et compteurs.exportes += 1 ;
        #   7. sur echec de validation : rejets.ecrire(Rejet(...)) et
        #      compteurs.rejeter(motif, champ).
        #
        # Le plafond config.collecte.max_objets doit etre verifie A CHAQUE
        # objet, pas seulement en fin de page : c'est un plafond, pas un
        # objectif, et le depasser de onze objets parce que la page en
        # contenait douze est un depassement quand meme.
        # ------------------------------------------------------------------
        del client, sortie, rejets
        raise NotImplementedError(
            "Cible non attribuee : extraction.py n'est pas implemente.\n"
            "Lancer `python -m collecteur diagnostic --url <URL>` en attendant."
        )

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
