import logging
from decimal import Decimal, InvalidOperation
import re

logger = logging.getLogger(__name__)

class Normalisateur:
    """Règles métier pour transformer les données brutes en données propres."""

    @staticmethod
    def normaliser_prix(valeur: any) -> Decimal | None:
        """Convertit une chaîne de prix (ex: 'Rs. 500') en Decimal.

        Règle : On extrait le premier nombre décimal trouvé.
        """
        if valeur is None or (isinstance(valeur, str) and not valeur.strip()):
            return None

        s = str(valeur).replace(",", ".")
        match = re.search(r"(\d+[\.,]?\d*)", s)
        if not match:
            return None

        try:
            return Decimal(match.group(1))
        except InvalidOperation:
            return None

    @staticmethod
    def extraire_devise(valeur: any) -> str | None:
        """Extrait le symbole de devise d'une chaîne de prix."""
        if not valeur or not isinstance(valeur, str):
            return None

        # On cherche tout ce qui n'est pas un chiffre, point, virgule ou espace
        # (Ex: 'Rs. 500' -> 'Rs.')
        match = re.search(r"([^\d\s\.,]+)", valeur)
        return match.group(1) if match else None

    @staticmethod
    def nettoyer_texte(texte: any) -> str | None:
        """Supprime les espaces superflus et normalise le texte."""
        if texte is None:
            return None
        return " ".join(str(texte).split())
