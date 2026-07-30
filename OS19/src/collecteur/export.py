import json
from pathlib import Path
from typing import Any
from .modele import ObjetCollecte, Rejet

class ExportateurJSONL:
    """Écrit les objets validés de façon incrémentale dans un fichier JSONL."""

    def __init__(self, fichier_sortie: str, fichier_rejets: str):
        self.fichier_sortie = Path(fichier_sortie)
        self.fichier_rejets = Path(fichier_rejets)

        # Assure que le dossier existe
        self.fichier_sortie.parent.mkdir(parents=True, exist_ok=True)
        self.fichier_rejets.parent.mkdir(parents=True, exist_ok=True)

    def ecrire_objet(self, objet: ObjetCollecte):
        """Ajoute un objet validé au fichier de sortie."""
        with open(self.fichier_sortie, "a", encoding="utf-8") as f:
            # On utilise model_dump(mode="json") pour gérer Decimal et datetime
            f.write(json.dumps(objet.model_dump(mode="json"), sort_keys=True) + "\n")

    def ecrire_rejet(self, rejet: Rejet):
        """Ajoute un objet rejeté au fichier de rejets."""
        with open(self.fichier_rejets, "a", encoding="utf-8") as f:
            f.write(json.dumps(rejet.model_dump(mode="json"), sort_keys=True) + "\n")

    def generer_echantillon(self, source: str, destination: str, limite: int):
        """Crée un fichier échantillon pour le dépôt GitHub."""
        with open(source, "r", encoding="utf-8") as in_f:
            lignes = in_f.readlines()[:limite]

        with open(destination, "w", encoding="utf-8") as out_f:
            out_f.writelines(lignes)
