# Collecteur Web explicable — TP individuel

> **État : structure initialisée, cible non encore attribuée.**
> Les zones marquées `<…>` sont à compléter dès que le formateur a communiqué
> l'identifiant de cible. Voir `docs/CHECKLIST_RENDU.md` pour l'ordre de travail.

Collecteur de données Web écrit pour le TP individuel du module « Web Scraping
moderne et industrialisation » (Semifir, formateur Adrien Vossough).

## Auteur

| | |
|---|---|
| Nom et prénom | **Joud Atallah** |
| Format | TP **strictement individuel** |
| Dépôt | https://github.com/Joud04/web_scraping |

## Organisation du travail

Groupe de travail déclaré : **Joud Atallah, Walid Hdilou, et un troisième
membre**, sur **deux sites cibles** au total.

| Site | Cible | Ma participation |
|---|---|---|
| 1 | **S32** — Cleveland Museum of Art (branche `s32-cleveland`) | audit technique complet, 12 tests de conformité `robots.txt`, correctif de propagation d'URL, retrait de 90 lignes de code mort |
| 2 | en attente du push de la branche | intégration et vérification dès réception |

> **Point à faire confirmer par le formateur avant l'envoi.** Les documents remis
> avec le sujet décrivent un **TP individuel** : *« Format : strictement
> individuel »* (`ENONCE_TP`), *« votre cible vous est attribuée »* au singulier
> (`MATRICE_CIBLES_ELEVES`), et la déclaration de la trame porte *« ma production
> individuelle »*. Aucun des cinq fichiers ne mentionne de binôme, de trinôme ni
> de règle « 3 étudiants = 2 cibles ». L'organisation en groupe décrite ci-dessus
> repose donc sur une consigne orale : **elle doit être confirmée par écrit avant
> la remise**, faute de quoi ce dépôt ne correspondrait pas au format attendu.

### Ce que contient la branche `main`

Uniquement du code que j'ai écrit et que je peux modifier sous les yeux du
formateur : l'ossature du collecteur (configuration, acquisition, normalisation,
modèle, export, journalisation), ses tests et sa documentation.

La branche `s32-cleveland` — le collecteur S32 de Walid Hdilou — n'est **pas**
fusionnée dans `main`. Ma contribution sur ce site est une contribution de
relecture et de correction, tracée dans l'historique Git par mes quatre commits
sur cette branche, et non une reprise de son code dans mon rendu.

## Cible et périmètre

| | |
|---|---|
| Identifiant de cible | `S__` |
| Site | `<nom>` |
| URL de départ | `<URL>` |
| Objet collecté | `<Product / Destination / Artwork / …>` |
| Volume plafond | `<n>` objets — **plafond de la fiche de cible, jamais un objectif** |
| Champs minimaux | `<liste>` |
| Rendu observé | `<HTML servi côté serveur / contenu absent sans JavaScript>` |

Le diagnostic complet, preuves à l'appui, est dans `docs/fiche_descriptive.md`.

## Prérequis

- Python **3.11 ou supérieur** (le module `tomllib` de la bibliothèque standard
  est utilisé pour lire la configuration)
- Aucun compte, aucune clé d'API, aucune variable d'environnement
- `<Playwright et son navigateur — uniquement si le diagnostic conclut à une cible SPA>`

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

`<à compléter — au moins trois limites réelles et mesurables, rubrique 9 du rapport>`

Une limite déjà identifiable, indépendante de la cible : la déduplication vit en
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

Le rapport `ATALLAH_Joud_TP_Scraping.docx` vit à la racine mais **n'est pas
versionné** (`.gitignore`) : il porte des données personnelles et part au
formateur par courriel, pas sur un dépôt public.
