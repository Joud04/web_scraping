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
   │  3. EXTRACTION    │  extraction.py      S32 -- SEULS modules qui
   │                   │  extraction_s19.py  S19    connaissent une cible.
   └─────────┬─────────┘                     Rendent des chaînes brutes.
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
| Extraction site 1 | `src/collecteur/extraction.py` | HTML, URL de base | `list[dict[str, str]]` |
| Extraction site 2 | `src/collecteur/extraction_s19.py` | HTML, URL de base | `list[dict[str, str]]` |
| Normalisation | `src/collecteur/normalisation.py` | `dict[str, str]` | valeurs typées ou `None` |
| Modèle et validation | `src/collecteur/modele.py` | valeurs typées | `ObjetCollecte` ou `ValidationError` |
| Export | `src/collecteur/export.py` | `ObjetCollecte` | ligne JSONL |
| Journalisation | `src/collecteur/journal.py` | événements | `logs/collecte.log`, `Compteurs` |
| Orchestration | `src/collecteur/cli.py` | arguments | code de sortie |

## Trois décisions structurantes

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

### Décision 3 — un socle commun aux deux cibles, plutôt qu'un projet par site

- **Besoin.** Le groupe couvre deux sites. La voie la plus rapide est que chacun
  écrive son collecteur dans son coin. Elle a d'abord été prise : la branche du
  site 2 contenait une seconde copie complète des six modules.
- **Ce qu'elle a coûté.** Les règles de politesse — `robots.txt`, délai garanti,
  `Retry-After`, arrêt sur refus explicite — sont la partie la plus difficile et
  la plus notée. Dupliquées, elles étaient à écrire deux fois, à tester deux fois,
  et sur le site 2 elles n'ont pas été écrites du tout : aucune lecture du
  `robots.txt`, aucun délai entre deux requêtes.
- **Retenu.** Un socle commun et **un module d'extraction par cible**. Les cinq
  modules génériques sont écrits et testés une seule fois ; brancher un site
  demande un module d'extraction et une classe métier.
- **Ce que ça prouve.** Les deux cibles ont des contraintes opposées : S32 impose
  un `Crawl-delay` de 10 s et interdit `/api` ; S19 ne publie aucun `robots.txt`.
  Le même code d'acquisition traite les deux, et chacune a ses tests de
  conformité (`test_robots_s32.py`, `test_robots_s19.py`).
- **Ce à quoi je renonce.** L'indépendance des deux sites : une modification du
  socle peut casser l'autre cible. C'est précisément ce que la suite de tests
  couvre, et c'est un compromis assumé.

## Alternatives écartées à l'échelle du projet

Six outils **n'ont pas** été retenus. La grille pénalise l'accumulation :
« une solution volontairement simple, dont vous expliquez la sobriété, est mieux
notée qu'une pile de frameworks non justifiés ».

| Écarté | Ce qu'il aurait apporté | Pourquoi le besoin n'existe pas ici |
|---|---|---|
| **Playwright** | rendu du JavaScript | La donnée est **déjà** dans la réponse HTTP des deux cibles : `__NEXT_DATA__` sur S32, les 34 produits en clair sur S19. Un navigateur coûterait une dépendance système, ~1 s de rendu par page — et sur S32 il rappellerait `/api`, chemin interdit. Il résoudrait un problème que je n'ai pas, en en créant un que je n'ai pas le droit d'avoir. |
| **crawl4ai** | acquisition pilotée par navigateur | Retenu un temps sur le site 2, puis retiré. Il embarque Playwright et Chromium pour une page servie côté serveur — vérifié : 34 produits dans la réponse HTTP brute. Il n'était de surcroît pas déclaré dans `requirements.txt` mais installé à part dans le `Dockerfile`, ce qui rendait le collecteur inexécutable hors conteneur. |
| **Docker** | environnement reproductible | Sa seule raison d'être ici était d'installer Chromium pour crawl4ai. Sans navigateur, un `venv` et un `requirements.txt` épinglé suffisent, et se démontrent à l'oral en une commande. |
| **Scrapy** | ordonnanceur, file, middlewares, export | Scrapy est dimensionné pour des milliers d'URL en parallèle. Ici : 30 objets, **une** requête toutes les 10 s. Son ordonnanceur serait inactif 99,7 % du temps, et sa courbe d'apprentissage se paierait à l'oral sur du code que je n'aurais pas écrit. Une `deque` de 8 lignes fait le même travail (`cli._collecte`). |
| **Base de données** | déduplication persistante, requêtes | 30 objets tiennent dans un `set`. Une base ajouterait un schéma, une migration et un service à démarrer pour un gain nul à cette échelle. La limite est réelle et assumée — elle est citée en rubrique 9 plutôt que masquée. |
| **Orchestrateur** (Prefect, Airflow) | replanification, reprise, supervision | La collecte dure ~5 minutes et se relance à la main. Il n'y a ni tâche périodique, ni dépendance entre jobs, ni reprise partielle à gérer. |

Le compte final reste **4 dépendances d'exécution** (`httpx`, `beautifulsoup4`, `lxml`,
`pydantic`), chacune reliée à un besoin nommé dans `requirements.txt`.
