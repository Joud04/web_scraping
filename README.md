# Collecteur Web explicable — TP individuel

> **État : cible S32 (Cleveland Museum of Art) implémentée et vérifiée.**
> Diagnostic, stratégie d'acquisition et preuves dans `docs/fiche_descriptive.md`.

Collecteur de données Web écrit pour le TP individuel du module « Web Scraping
moderne et industrialisation » (Semifir, formateur Adrien Vossough).

## Auteur

| | |
|---|---|
| Nom et prénom | Walid Hdilou |
| Cible traitée | S32 — Cleveland Museum of Art |
| Groupe | `<binôme 2 à compléter>`, `<binôme 3 à compléter>` |

## Cible et périmètre

| | |
|---|---|
| Identifiant de cible | S32 |
| Site | Cleveland Museum of Art |
| URL de départ | https://www.clevelandart.org/art/collection/search |
| Objet collecté | Artwork |
| Volume plafond | 30 objets — **plafond de la fiche de cible, jamais un objectif** |
| Champs minimaux | `title`, `artist`, `date_text`, `medium`, `url` |
| Rendu observé | recherche : contenu absent sans JavaScript ; **fiches détail : servies côté serveur** |

Le diagnostic complet, preuves à l'appui, est dans `docs/fiche_descriptive.md`.

## Prérequis

- Python **3.11 ou supérieur** (le module `tomllib` de la bibliothèque standard
  est utilisé pour lire la configuration)
- Aucun compte, aucune clé d'API, aucune variable d'environnement
- **Aucun navigateur** : le diagnostic conclut que les fiches détail sont servies
  côté serveur, la donnée est donc dans la réponse HTTP (voir `docs/fiche_descriptive.md`, section 4)

## Installation

```bash
git clone <URL_DU_DEPOT>
cd <dossier>

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .

cp config.example.toml config.toml   # puis renseigner [cible]
```

## Lancement

### Diagnostic de la cible — n'écrit aucune donnée

```bash
python -m collecteur diagnostic --url <URL_DE_DEPART>
```

Interroge l'URL de départ et rapporte : statut HTTP, taille de la réponse brute,
volume de texte hors balises, nombre de `<script>`, présence de JSON-LD, racines
de SPA détectées, et le contenu du `robots.txt` avec son `Crawl-delay`.

Ces chiffres sont la moitié gauche du tableau de la rubrique 2.2 du compte rendu.
L'autre moitié se relève dans les outils de développement du navigateur, sur le
DOM rendu. **L'écart chiffré entre les deux est le diagnostic** — le navigateur
seul ne dit rien de ce que contenait la réponse HTTP.

### Collecte limitée

```bash
python -m collecteur collecte --max-objets 10 --delai 1.0
```

Toutes les options : `--url`, `--max-objets`, `--max-pages`, `--delai`,
`--sortie`, `--config`, `--niveau {DEBUG,INFO,WARNING,ERROR}`.
Un argument de ligne de commande gagne sur `config.toml`, qui gagne sur les
valeurs par défaut du code.

### Vérification — s'exécute **sans réseau**

```bash
pytest
```

## Architecture

Six responsabilités, un module par responsabilité, sous `src/collecteur/` :

| Module | Responsabilité |
|---|---|
| `config.py` | configuration (TOML + surcharges CLI, validées avant la première requête) |
| `acquisition.py` | requêtes HTTP, délai garanti, `robots.txt`, gestion des refus |
| `extraction.py` | sélecteurs — **seul module qui connaît la cible** |
| `normalisation.py` | règles métier, déduplication |
| `modele.py` | schéma et validation Pydantic |
| `export.py` | écriture JSONL incrémentale |
| `journal.py` | traces horodatées et compteurs d'exécution |

Le schéma de flux et les décisions de conception sont dans `docs/architecture.md`.

## Format de sortie

**JSONL** (JSON Lines) : un objet JSON par ligne, UTF-8 sans échappement, clés
triées, fins de ligne `\n` quel que soit le système.

L'export est **automatique** : chaque objet validé est écrit dès qu'il est produit,
avec vidage du tampon à chaque ligne. Une collecte interrompue en cours de route
laisse un fichier exploitable — argument vérifié par
`tests/test_export.py::test_ecriture_incrementale_survit_a_une_interruption`,
et non pas seulement affirmé ici.

| Fichier | Contenu | Versionné ? |
|---|---|---|
| `data/sortie.jsonl` | tous les objets validés | non (`.gitignore`) |
| `data/rejets.jsonl` | objets écartés, avec motif et champ fautif | non |
| `samples/sample_output.json` | échantillon de 10 objets, relisible sur GitHub | **oui** |
| `logs/collecte.log` | traces horodatées | non |

Le prix est sérialisé en **chaîne** et manipulé en `Decimal`, jamais en `float` :
`129.90` n'a pas de représentation binaire exacte, et un prix qui dérive au
centième dans un fichier de sortie est un défaut de donnée, pas d'affichage.

Convention de valeur absente, tenue dans tout le projet :

| Valeur | Signification |
|---|---|
| `null` | le champ n'existe pas sur la page |
| `""` | le champ existe et la page le laisse vide |
| `0` | le champ existe et vaut zéro |

## Usage responsable — règles effectivement appliquées

- **Aucun contournement.** Un statut 401, 403, 407 ou 451 lève `CollecteRefusee`,
  qui n'est **pas** rattrapée par la boucle de réessai : la collecte s'arrête et le
  refus est documenté. Le chemin de code est volontairement distinct de celui des
  erreurs temporaires pour qu'aucune logique de reprise ne puisse l'attraper par
  accident (`src/collecteur/acquisition.py`).
- **`robots.txt` lu avant toute autre requête**, et un chemin interdit n'est jamais
  demandé. Si le fichier déclare un `Crawl-delay` supérieur au délai configuré,
  **c'est le `Crawl-delay` qui gagne** — le délai est relevé, jamais abaissé.
- **Une requête à la fois**, avec un délai minimal garanti entre deux, mesuré sur
  une horloge monotone.
- **`Retry-After` respecté** sur 429 et 503, plafonné pour qu'un serveur renvoyant
  `Retry-After: 3600` n'immobilise pas la collecte une heure. À défaut d'en-tête,
  repli exponentiel borné et nombre de tentatives fini.
- **User-Agent identifiant.** Le collecteur ne se fait pas passer pour un navigateur.
- **Aucune donnée personnelle** dans le périmètre, aucune page derrière un compte,
  **aucune action irréversible** — pas d'achat, pas de réservation, pas d'envoi de
  formulaire réel.
- **Aucun secret versionné.** `config.toml`, `.env` et les états de session sont
  exclus par `.gitignore` ; seul `config.example.toml`, qui ne porte aucune valeur,
  est publié.

## Limites connues

1. **Découverte bornée par le voisinage.** Le parcours part de graines et suit les
   œuvres liées (`artworksForSeeAlso`). Il n'atteint donc que la composante du
   catalogue connexe aux graines, pas l'ensemble des dizaines de milliers d'œuvres.
   C'est un choix imposé : la recherche exhaustive passe par `/api`, interdit.
2. **Filtres et pagination non couverts.** Ils vivent derrière `/api` ; les
   démontrer exigerait de contourner le robots.txt. Le front de collecte
   (`artworksForSeeAlso`) en est l'équivalent conforme, mais il ne permet pas de
   filtrer par département ou par date.
3. **Dépendance au format `__NEXT_DATA__`.** L'extraction lit le JSON injecté par
   Next.js ; une refonte du site vers un rendu 100 % client casserait la collecte
   (détecté par `pytest`, repli documenté en fiche §7).

Une quatrième limite, indépendante de la cible : la déduplication vit en
mémoire (`normalisation.Deduplicateur`). Elle ne survit pas à la fin du processus,
donc deux exécutions successives ne se dédoublonnent pas entre elles. Choix assumé
sur un volume de 60 objets au plus — une base de données serait ici de la
complexité gratuite, ce que la grille pénalise.

## Structure du dépôt

```
.
├── README.md
├── requirements.txt
├── pyproject.toml
├── config.example.toml          aucun secret
├── src/collecteur/              six responsabilités, un module chacune
├── tests/
│   ├── fixtures/                pages enregistrées — vérification sans réseau
│   ├── test_extraction.py       contrôle 1 : nombre d'objets extraits
│   ├── test_normalisation.py    contrôle 2 : normalisation du prix
│   ├── test_deduplication.py    contrôle 3 : déduplication et rejet d'incomplet
│   └── test_export.py           l'écrivain JSONL lui-même
├── samples/sample_output.json   échantillon de 10 objets
└── docs/
    ├── architecture.md
    ├── AI_USAGE.md
    ├── fiche_descriptive_template.md
    └── CHECKLIST_RENDU.md
```
