# Collecteur Web explicable — TP de groupe

> **État : site 1 (S32 — Cleveland Museum of Art) implémenté, collecté et vérifié.
> Site 2 en cours d'intégration.**
> Diagnostic, stratégie d'acquisition et preuves dans `docs/fiche_descriptive.md`.

Collecteur de données Web écrit pour le TP du module « Web Scraping moderne et
industrialisation » (Semifir, formateur Adrien Vossough).

## Groupe et périmètre

**Groupe de 3 élèves, 2 sites cibles.** Modalité officielle du TP : les groupes
de 2 ou 3 sont autorisés, et un groupe de 3 traite 2 sites au total.

| | |
|---|---|
| Membres | **Joud Atallah**, **Walid Hdilou**, et un troisième membre |
| Sites couverts | 2 |
| Dépôt | https://github.com/Joud04/web_scraping |

### Répartition et contribution

| Site | Cible | État | Contributions |
|---|---|---|---|
| 1 | **S32** — Cleveland Museum of Art | fusionné dans `main` | Walid Hdilou : diagnostic, extraction, modèle `Artwork`, parcours de collecte, fiche descriptive. Joud Atallah : audit technique complet, 12 tests de conformité `robots.txt` (`Crawl-delay` de 10 s relevé automatiquement, `/api` refusé avant toute requête), correctif de propagation d'URL dans les rejets, retrait de 90 lignes de code mort |
| 2 | à intégrer | en attente | intégration et vérification dès réception |

Le détail par auteur se lit dans l'historique : `git log --format='%an %s'`.

### Organisation du dépôt

`main` porte le **socle commun** et les sites au fur et à mesure de leur
intégration. Chaque site est développé sur sa branche puis fusionné.

C'est ce qui rend le travail à plusieurs praticable sans conflit : les cinq
modules génériques (configuration, acquisition, normalisation, modèle et export,
journalisation) sont communs aux deux sites, et **seul `extraction.py` connaît la
cible**. Un site se branche en écrivant un module d'extraction et une classe
métier, sans toucher au reste.

Le bénéfice est mesurable : la conformité au `robots.txt`, le délai garanti entre
deux requêtes, la gestion des 429 et l'arrêt sur refus explicite sont écrits et
testés **une seule fois**, et valent pour les deux sites.

## Site 1 — cible et périmètre

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

Les dates de création restent en **texte** (`date_text : "c. 1765"`) et ne sont pas
converties en date. Ce n'est pas un raccourci : le musée date ses œuvres en
« c. 1765 », « 1957 », « fin du XVIIIe siècle ». Forcer ces valeurs dans un type
`date` inventerait une précision que la source ne porte pas. La normalisation
appliquée est celle du **texte** — NFC et blancs Unicode — et de l'**URL**, qui
sont les deux endroits où deux écritures d'une même valeur casseraient la
déduplication.

Convention de valeur absente, tenue dans tout le projet :

| Valeur | Signification | Cas réel sur S32 |
|---|---|---|
| `null` | le champ n'existe pas sur la page | œuvre anonyme → `artist: null` |
| `""` | le champ existe et la page le laisse vide | — |
| `0` | le champ existe et vaut zéro | — |

Cette distinction porte ici tout son sens : `artist: null` signale une œuvre que
le musée **n'attribue à personne**, pas un sélecteur qui a échoué. Une chaîne vide
confondrait les deux.

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
4. **Déduplication non persistante.** Elle vit en mémoire
   (`normalisation.Deduplicateur`) et ne survit pas à la fin du processus : deux
   exécutions successives ne se dédoublonnent pas entre elles. Choix assumé sur un
   plafond de 30 objets — une base de données serait ici de la complexité gratuite,
   ce que la grille pénalise explicitement.

## Structure du dépôt

```
.
├── README.md
├── requirements.txt
├── pyproject.toml
├── config.example.toml          aucun secret ; graines du parcours S32
├── src/collecteur/              six responsabilités, un module chacune
├── tests/                       54 tests, aucun ne touche le réseau
│   ├── fixtures/
│   │   ├── page_detail.html     fiche 1915.534 enregistrée telle quelle (116 Ko)
│   │   └── robots.txt           robots.txt réel de la cible, enregistré
│   ├── test_extraction.py       contrôle 1 : champs extraits de la fiche enregistrée
│   ├── test_normalisation.py    contrôle 2 : normalisation texte et URL
│   ├── test_deduplication.py    contrôle 3 : déduplication et rejet d'incomplet
│   ├── test_robots_s32.py       conformité robots.txt : Crawl-delay 10 s, /api refusé
│   └── test_export.py           l'écrivain JSONL lui-même
├── samples/sample_output.json   échantillon de 10 objets
└── docs/
    ├── architecture.md
    ├── fiche_descriptive.md     diagnostic S32, preuves à l'appui
    ├── AI_USAGE.md
    ├── fiche_descriptive_template.md
    └── CHECKLIST_RENDU.md
```

Le rapport `ATALLAH_Joud_TP_Scraping.docx` vit à la racine mais **n'est pas
versionné** (`.gitignore`) : il porte des données personnelles et part au
formateur par courriel, pas sur un dépôt public.
