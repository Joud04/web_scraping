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

### Décision 1 — `<à compléter après le diagnostic : client HTTP ou navigateur>`

La forme attendue, d'après la notice : **une décision est un cas où l'on a renoncé à
quelque chose.** Un choix sans contrepartie n'est pas une décision.

- Besoin observé :
- Retenu :
- Écarté :
- Ce à quoi je renonce en choisissant ainsi :

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

## Alternative écartée à l'échelle du projet

`<Scrapy / Playwright / base de données / orchestrateur — à compléter>`

> La grille pénalise explicitement l'accumulation d'outils : « une solution
> volontairement simple, dont vous expliquez la sobriété, est mieux notée qu'une pile
> de frameworks non justifiés ». Écrire ici ce qui **n'a pas** été ajouté, et pourquoi
> le besoin n'existait pas.
