"""Collecteur Web explicable -- TP de groupe (3 eleves, 2 sites).

Les six responsabilites exigees par l'enonce sont portees par six modules,
un par responsabilite. Le schema de flux de docs/architecture.md pointe
directement sur ces noms.

    config          configuration        (lecture TOML + surcharge CLI)
    acquisition     acquisition          (requetes, delai, robots.txt, erreurs)
    extraction      extraction           (HTML/DOM/JSON -> dictionnaires bruts)
    normalisation   normalisation        (regles metier + validation Pydantic)
    export          export               (ecriture JSONL incrementale)
    journal         journalisation       (traces horodatees + compteurs)
"""

__version__ = "0.1.0"
