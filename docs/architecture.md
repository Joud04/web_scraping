# Architecture

> Rubrique 4 du compte rendu. La notice prévient : « le schéma doit décrire le code
> livré, y compris s'il est regroupé dans deux fichiers » — pas l'architecture qu'on
> aurait aimé écrire. Chaque boîte ci-dessous pointe donc sur un fichier réel.

## Flux de données

```
        config.toml                    (aucun secret ; config.example.toml versionné)
             │
             ▼
   ┌───────────────────┐
   │  1. CONFIGURATION │  config.py      TOML + surcharges CLI, validées avant
   └─────────┬─────────┘                 la première requête
             │  Config
             ▼
   ┌───────────────────┐   robots.txt    délai garanti entre deux requêtes
   │  2. ACQUISITION   │◄───────────►    Crawl-delay > délai configuré
   │                   │   cible Web     429 → Retry-After ; 403/401 → ARRÊT
   └─────────┬─────────┘
             │  Reponse (html brut)
             ▼
   ┌───────────────────┐
   │  3. EXTRACTION    │  extraction.py  sélecteurs ; SEUL module qui connaît
   └─────────┬─────────┘                 la cible. Rend des chaînes brutes.
             │  dict[str, str]
             ▼
   ┌───────────────────┐
   │  4. NORMALISATION │  normalisation.py  règles métier : prix → Decimal,
   │     + VALIDATION  │  modele.py         texte → NFC, URL → absolue
   └────┬─────────┬────┘                    puis validation Pydantic stricte
        │         │
     valide    rejeté
        │         └──────────► data/rejets.jsonl  (motif + champ + brut)
        ▼
   ┌───────────────────┐
   │  5. EXPORT        │  export.py      JSONL incrémental, flush par objet
   └─────────┬─────────┘                 + samples/sample_output.json
             │
             ▼
      data/sortie.jsonl

   ┌───────────────────┐
   │  6. JOURNALISATION│  journal.py     traces horodatées + Compteurs
   └───────────────────┘                 (traverse les cinq étages)
```

## Responsabilités

| Composant | Fichier | Entrée | Sortie |
|---|---|---|---|
| Configuration | `src/collecteur/config.py` | `config.toml`, arguments CLI | `Config` (gelée) |
| Acquisition | `src/collecteur/acquisition.py` | `Config`, URL | `Reponse` ou exception |
| Extraction | `src/collecteur/extraction.py` | HTML, URL de base | `list[dict[str, str]]` |
| Normalisation | `src/collecteur/normalisation.py` | `dict[str, str]` | valeurs typées ou `None` |
| Modèle et validation | `src/collecteur/modele.py` | valeurs typées | `ObjetCollecte` ou `ValidationError` |
| Export | `src/collecteur/export.py` | `ObjetCollecte` | ligne JSONL |
| Journalisation | `src/collecteur/journal.py` | événements | `logs/collecte.log`, `Compteurs` |
| Orchestration | `src/collecteur/cli.py` | arguments | code de sortie |

## Deux décisions structurantes

### Décision 1 — parcours de proche en proche, plutôt que la recherche du site

- **Besoin observé.** Il faut découvrir 30 œuvres. La voie naturelle est la page de
  recherche — mais sa réponse HTTP contient **0 œuvre** : elle peuple ses résultats
  par `GET /api/…`, et `/api` est en `Disallow` dans le `robots.txt`
  (`tests/fixtures/robots.txt`, ligne 6). La voie naturelle est donc fermée, et
  aucun navigateur ne la rouvre : piloter Chrome rappellerait `/api` en coulisse.
  Ce serait un contournement, que l'énoncé rend non évaluable.
- **Retenu.** Un front de collecte en largeur : cinq graines déclarées dans
  `config.toml`, étendues par les œuvres voisines que chaque fiche publie dans
  `artworksForSeeAlso` (`extraction.extraire_liens_lies`, `cli._collecte`). Ces
  fiches sont servies **côté serveur** sous `/art/<accession>`, chemin autorisé.
- **Écarté.** L'appel direct à `/api`, qui donnerait la pagination, les filtres et
  le catalogue entier en une requête.
- **Ce à quoi je renonce.** La couverture. Le parcours n'atteint que la composante du
  catalogue reliée à mes graines, pas les dizaines de milliers d'œuvres du musée, et
  je perds tout filtrage par département ou par période. C'est le prix de la
  conformité, et il est assumé : la collecte reste défendable, ce que ne serait pas
  un échantillon plus large obtenu sur un chemin interdit.

> Point de vigilance pour l'oral : cet arbitrage est le cœur du sujet S32. La
> question « pourquoi ne pas simplement appeler l'API ? » tombera. La réponse tient
> en une phrase — **elle est interdite par le `robots.txt`, et un blocage explicite
> ne se contourne pas** — et elle se prouve à l'écran en une commande :
> `python -m collecteur diagnostic --url https://www.clevelandart.org/art/collection/search`.

### Décision 2 — schéma strict (`extra="forbid"`) plutôt que tolérant

- **Besoin.** Un champ inattendu remonté par l'extraction signale un décalage entre ce
  que la page contient et ce que le modèle attend. Avec un schéma tolérant, ce décalage
  passe en silence et se découvre en aval, dans les données.
- **Retenu.** `extra="forbid"` : l'objet est rejeté, le motif est écrit dans
  `data/rejets.jsonl`, le compteur `rejetes` monte, et l'écart est visible dans le
  tableau de la rubrique 7.
- **Écarté.** `extra="allow"`, qui aurait laissé passer les champs surnuméraires.
- **Ce à quoi je renonce.** Une collecte qui s'arrête plus souvent, notamment si le site
  ajoute un champ. C'est un choix assumé : sur ce volume, une collecte bruyante coûte
  quelques minutes, une donnée fausse coûte l'analyse qui s'appuiera dessus.

## Alternatives écartées à l'échelle du projet

Quatre outils **n'ont pas** été ajoutés. La grille pénalise l'accumulation :
« une solution volontairement simple, dont vous expliquez la sobriété, est mieux
notée qu'une pile de frameworks non justifiés ».

| Écarté | Ce qu'il aurait apporté | Pourquoi le besoin n'existe pas ici |
|---|---|---|
| **Playwright** | rendu du JavaScript | La donnée est **déjà** dans la réponse HTTP des fiches (`__NEXT_DATA__`). Un navigateur coûterait une dépendance système, ~1 s de rendu par page — et rappellerait `/api`, chemin interdit. Il résoudrait un problème que je n'ai pas, en en créant un que je n'ai pas le droit d'avoir. |
| **Scrapy** | ordonnanceur, file, middlewares, export | Scrapy est dimensionné pour des milliers d'URL en parallèle. Ici : 30 objets, **une** requête toutes les 10 s. Son ordonnanceur serait inactif 99,7 % du temps, et sa courbe d'apprentissage se paierait à l'oral sur du code que je n'aurais pas écrit. Une `deque` de 8 lignes fait le même travail (`cli._collecte`). |
| **Base de données** | déduplication persistante, requêtes | 30 objets tiennent dans un `set`. Une base ajouterait un schéma, une migration et un service à démarrer pour un gain nul à cette échelle. La limite est réelle et assumée — elle est citée en rubrique 9 plutôt que masquée. |
| **Orchestrateur** (Prefect, Airflow) | replanification, reprise, supervision | La collecte dure ~5 minutes et se relance à la main. Il n'y a ni tâche périodique, ni dépendance entre jobs, ni reprise partielle à gérer. |

Le compte final : **4 dépendances d'exécution** (`httpx`, `beautifulsoup4`, `lxml`,
`pydantic`), chacune reliée à un besoin nommé dans `requirements.txt`.
