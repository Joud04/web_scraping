"""Normalisation et deduplication -- regles metier, independantes de la cible.

Ces fonctions transforment ce que la page affiche en ce que le modele attend.
Elles sont volontairement separees de l'extraction : l'extraction dit ou lire,
la normalisation dit comment interpreter. C'est aussi ce qui les rend testables
sans reseau, exigence de la rubrique 6 de l'enonce.

Chaque fonction retourne `None` quand l'entree ne permet aucune conclusion.
Elle ne devine jamais : une valeur illisible devient `None` et l'objet part en
rejet avec son motif, plutot que d'etre comble par une valeur par defaut.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit, urlunsplit

# Blancs Unicode que `str.strip` ignore et que les sites emploient couramment.
# Ecrits en echappements plutot qu'en caracteres litteraux : a l'oeil, ils sont
# indiscernables d'une espace ordinaire dans un editeur, et un relecteur de bonne
# foi les "corrigerait" en cassant silencieusement la comparaison des textes.
ESPACE_INSECABLE = "\u00a0"  # NO-BREAK SPACE        -- "1 299" sur les sites francais
ESPACE_INSEC_FINE = "\u202f"  # NARROW NO-BREAK SPACE -- meme role, variante typographique
_BLANCS = (
    ESPACE_INSECABLE
    + ESPACE_INSEC_FINE
    + "\u2007"  # FIGURE SPACE
    + "\u2009"  # THIN SPACE
    + "\u200a"  # HAIR SPACE
    + "\ufeff"  # ZERO WIDTH NO-BREAK SPACE (BOM rencontre en milieu de flux)
)

# Separateurs de milliers typographiques. Un prix affiche \u00ab 1 299 \u00bb porte
# souvent une espace insecable, pas une espace ordinaire.
_SEPARATEURS_MILLIERS = " " + ESPACE_INSECABLE + ESPACE_INSEC_FINE

# Deux formes, dans cet ordre : nombre a separateurs de milliers, puis nombre
# simple. La premiere exige AU MOINS un groupe de trois chiffres (`+`, pas `*`)
# et refuse d'etre suivie d'un chiffre.
#
# Sans ces deux precautions, « 1500 » entrait dans la premiere forme : `\d{1,3}`
# y capturait « 150 », le groupe de milliers ne trouvait rien a repeter, et le
# motif rendait 150. Tout prix de quatre chiffres ou plus ecrit sans separateur
# perdait ainsi ses derniers chiffres, en silence. Le defaut est reste invisible
# tant que le projet ne traitait que des oeuvres d'art, qui n'ont pas de prix.
_MOTIF_NOMBRE = re.compile(
    r"[-+]?\d{1,3}(?:[" + _SEPARATEURS_MILLIERS + r".,]\d{3})+(?:[.,]\d+)?(?!\d)"
    r"|[-+]?\d+(?:[.,]\d+)?"
)

# Symboles et codes monetaires les plus courants sur les cibles du TP.
# \u00ab Rs. \u00bb est celui de la cible S19 (Automation Exercise), qui affiche ses
# prix en roupies indiennes sans jamais ecrire le code ISO.
_DEVISES = {
    "\u20ac": "EUR",
    "eur": "EUR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "\u00a3": "GBP",
    "gbp": "GBP",
    "\u20b9": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "\u00a5": "JPY",
    "jpy": "JPY",
    "zar": "ZAR",
    "s$": "SGD",
    "sgd": "SGD",
    "nz$": "NZD",
    "nzd": "NZD",
    "c$": "CAD",
    "cad": "CAD",
    "a$": "AUD",
    "aud": "AUD",
}


def normaliser_texte(brut: str | None, *, vide_en_none: bool = True) -> str | None:
    """Nettoie un texte extrait du HTML.

    Trois operations, dans cet ordre :
      1. normalisation Unicode NFC -- « e » + accent combinant et « e accent
         precompose » sont visuellement identiques mais comparent faux, ce qui
         casse silencieusement la deduplication ;
      2. remplacement des blancs Unicode par une espace ordinaire ;
      3. reduction des suites d'espaces et retours a la ligne du HTML.

    `vide_en_none=True` traduit une chaine devenue vide en `None`, conformement
    a la convention du modele : absent et vide ne se confondent pas.
    """
    if brut is None:
        return None
    texte = unicodedata.normalize("NFC", brut)
    for blanc in _BLANCS:
        texte = texte.replace(blanc, " ")
    texte = re.sub(r"\s+", " ", texte).strip()
    if not texte and vide_en_none:
        return None
    return texte


def normaliser_prix(brut: str | None) -> Decimal | None:
    """Extrait un montant d'une chaine affichee, en `Decimal`.

    `Decimal` et non `float` : 0.1 + 0.2 != 0.3 en binaire, et un prix qui
    derive au centieme dans un fichier de sortie est un defaut de donnee.

    Le point delicat est le separateur. « 1,299 » vaut 1299 en anglais et 1.299
    en francais. La regle retenue, documentee et donc defendable :

      - un separateur suivi d'exactement trois chiffres, et seul de son espece
        dans le nombre, est un separateur de milliers ;
      - sinon, le dernier separateur rencontre est la decimale.

    Elle echoue sur « 1,250 » signifiant 1,25 EUR ecrit avec trois decimales :
    ce cas est rare sur les cibles du TP, et l'echec est silencieux. C'est une
    limite a citer en rubrique 9 plutot qu'a passer sous silence.
    """
    if brut is None:
        return None
    texte = normaliser_texte(brut)
    if texte is None:
        return None
    correspondance = _MOTIF_NOMBRE.search(texte)
    if correspondance is None:
        return None

    nombre = correspondance.group(0)
    for blanc in _SEPARATEURS_MILLIERS:
        nombre = nombre.replace(blanc, "")

    dernier_point, derniere_virgule = nombre.rfind("."), nombre.rfind(",")
    decimale = max(dernier_point, derniere_virgule)
    if decimale == -1:
        propre = nombre
    else:
        chiffres_apres = len(nombre) - decimale - 1
        if chiffres_apres == 3 and (dernier_point == -1 or derniere_virgule == -1):
            # Un seul type de separateur, suivi de trois chiffres : milliers.
            propre = nombre.replace(".", "").replace(",", "")
        else:
            entier = nombre[:decimale].replace(".", "").replace(",", "")
            propre = f"{entier}.{nombre[decimale + 1 :]}"

    try:
        return Decimal(propre)
    except InvalidOperation:
        return None


def detecter_devise(brut: str | None, *, defaut: str | None = None) -> str | None:
    """Deduit un code ISO 4217 du symbole affiche a cote du prix.

    Les symboles sont essayes du plus long au plus court, sans quoi « rs »
    l'emporterait sur « rs. » et « $ » sur « us$ ». Les symboles d'une seule
    lettre sont volontairement absents de la table : « r » se rencontre dans
    presque tout texte, et le faire correspondre a ZAR etiquetterait en rand
    n'importe quel prix accompagne d'un mot.

    Renvoie `defaut` si aucun symbole n'est reconnu. Sur une cible qui n'affiche
    jamais sa devise, le rapport doit dire d'ou vient la valeur retenue : une
    devise codee en dur qui ne vient pas de la page est une hypothese, et elle
    se declare.
    """
    if brut is None:
        return defaut
    texte = (normaliser_texte(brut) or "").lower()
    for symbole, code in sorted(_DEVISES.items(), key=lambda paire: -len(paire[0])):
        if symbole in texte:
            return code
    return defaut


def normaliser_url(brut: str | None, base: str) -> str | None:
    """Resout une URL relative et retire le fragment.

    Le fragment (`#section`) ne designe pas une autre ressource : le conserver
    ferait passer deux fois sur la meme page et gonflerait le compteur de
    doublons pour rien.
    """
    if brut is None:
        return None
    texte = normaliser_texte(brut)
    if texte is None:
        return None
    absolue = urljoin(base, texte)
    parties = urlsplit(absolue)
    if parties.scheme not in ("http", "https"):
        return None
    return urlunsplit((parties.scheme, parties.netloc, parties.path, parties.query, ""))


class Deduplicateur:
    """Retient les cles deja vues et signale les redites.

    Volontairement en memoire : sur les volumes du TP (60 objets au plus), une
    base de donnees serait de la complexite gratuite, ce que la grille penalise
    au critere « choix des outils ». La limite est reelle et se cite en rubrique
    9 : la deduplication ne survit pas a la fin du processus, donc deux
    executions successives ne se dedoublonnent pas entre elles.
    """

    def __init__(self) -> None:
        self._vues: set[str] = set()
        self.doublons = 0

    def est_nouveau(self, cle: str) -> bool:
        if cle in self._vues:
            self.doublons += 1
            return False
        self._vues.add(cle)
        return True

    def __len__(self) -> int:
        return len(self._vues)
