# Fiche descriptive de cible

```
Cible ................. S32 — Cleveland Museum of Art
URL de départ ......... https://www.clevelandart.org/art/collection/search
Date d'analyse ........ 2026-07-30
Objet collecté ........ Artwork
Volume plafond ........ 30 objets (source : fiche de cible — plafond, pas objectif)
Champs minimaux ....... title, artist, date_text, medium, url
Exigence complémentaire robots.txt impose Crawl-delay: 10 ; le respect du délai est évalué
```

---

## 1. Source

| Élément | Valeur | Preuve (commande + sortie) |
|---|---|---|
| Famille de site | SPA (Next.js) adossée à une API interne | `id="__NEXT_DATA__"` et `id="__next"` présents, 1 occurrence chacun |
| Statut HTTP de l'URL de départ | 200 | `curl -s -o /dev/null -w "%{http_code}"` → `200` |
| `Content-Type` | `text/html; charset=utf-8` | idem, `%{content_type}` |
| Taille de la réponse | 108 882 octets | `curl -s -o /dev/null -w "%{size_download}"` → `108882` |
| `robots.txt` publié | oui | `curl -s https://www.clevelandart.org/robots.txt` (ci-dessous) |
| `sitemap.xml` publié | oui, mais sans œuvres | index → `?page=1` : 2000 `<loc>`, **0** vers `/art/` |

### Lecture du `robots.txt`

```
User-agent: *
Crawl-delay: 10
Disallow: /membership
Disallow: /orders
Disallow: /api
Disallow: /errors
Disallow: /404
Disallow: /500
Host: https://www.clevelandart.org
Sitemap: https://www.clevelandart.org/sitemap.xml
```

- **Mon chemin de collecte est-il autorisé ?** Oui. Je collecte des fiches d'œuvre
  servies sous `/art/<accession>` : aucune règle `Disallow` ne couvre ce chemin.
- **Ce qui est interdit et me concerne :** `Disallow: /api`. C'est précisément le
  chemin qu'appelle la page de recherche pour peupler ses résultats. Je ne le
  demande donc **jamais** — ni en direct, ni via un navigateur. Cette contrainte
  commande toute la stratégie (section 4).
- `Crawl-delay` déclaré : **10 s**.
- Délai réellement appliqué : **10 s** (le collecteur relève automatiquement le
  délai configuré au `Crawl-delay` du robots.txt — `acquisition.ClientHTTP.__enter__`).

### Conditions d'utilisation

- Les données du Cleveland Museum of Art sont publiées en **Open Access (CC0)**.
- Conclusion : collecte poursuivie, volume plafonné à 30, délai de 10 s respecté.

---

## 2. Surface porteuse de la donnée

| Élément | Observation | Preuve |
|---|---|---|
| HTML initial — marqueur cherché | `"accession_number"` d'une œuvre de résultat | occurrences dans la réponse brute de `/search` : **0** |
| HTML initial (`/search`) — objets présents | **0 / 30** | `__NEXT_DATA__` ne porte que les filtres (`artFilters`, `galleryLocations`), aucune œuvre |
| Requête identique avec `?search=cat` | même réponse, **108 882 octets** à l'octet près | la requête ne change rien au HTML : le filtrage est 100 % client |
| Requête réseau porteuse | `GET /api/...` (XHR) | onglet Réseau ; **chemin interdit par robots.txt** |
| **Écart HTML brut ↔ DOM** | 0 œuvre dans la réponse HTTP, N vignettes dans le DOM après appel à `/api` | ← c'est le diagnostic |
| Fiche détail `/art/1915.534` | **rendue côté serveur** : toute la donnée dans `__NEXT_DATA__` | `curl` → 200, 116 368 octets ; `props.pageProps.artworkData` complet |
| Pagination / filtres | derrière `/api` (interdit) ; remplacés par le lien `artworksForSeeAlso` de chaque fiche | `artworkData` et `artworksForSeeAlso` présents dans la réponse détail |
| Condition d'arrêt | plafond `max_objets` atteint, ou front de collecte vide | vérifiée par le compteur `exportes` |

**Conformité à la fiche de cible :** ☑ conforme — « contenu absent sans
JavaScript » est vérifié pour la **page de recherche**, mais les **fiches détail
sont servies côté serveur**, ce qui permet une collecte sans navigateur.

La requête réseau qui porte les résultats (`/api`) est publique et réellement
utilisée par la page, mais elle est **interdite par le robots.txt** : on ne
l'utilise pas. On se rabat sur les fiches détail, sur un chemin autorisé.

---

## 3. Champs disponibles et couverture du contrat

| Champ du modèle | Source exacte (`artworkData.…`) | Obligatoire ? | Règle si absent |
|---|---|---|---|
| `item_id` | `accession_number` | oui | `ChampObligatoireAbsent` → rejet |
| `title` | `title` | oui | `ChampObligatoireAbsent` → rejet |
| `artist` | `creators[].description` (repli `name`) | non | `None` (œuvre anonyme) |
| `date_text` | `date_text` (repli `creation_date`) | non | `None` |
| `medium` | `technique` (repli `medium_mapped`) | non | `None` |
| `url` | `url` | oui | `ChampObligatoireAbsent` → rejet |

Champs minimaux non trouvés sur la cible : **aucun**. Les trois champs facultatifs
sont réellement absents sur certaines œuvres (anonymes, sans date), ce qui est une
information à conserver (`None`), pas un ancrage manqué.

---

## 4. Technique d'acquisition retenue

| Niveau | Statut | Justification |
|---|---|---|
| 1 — jeu de données publié | écarté | un dump complet CC0 existe hors périmètre ; la cible attribuée est le site |
| 2 — API documentée et autorisée | écarté | l'API Open Access est documentée mais son hôte diffère du site attribué |
| 3 — endpoint JSON interne | **interdit** | `/api` est en `Disallow` dans le robots.txt |
| 4 — HTTP + parser | **retenu** | les fiches détail sont servies côté serveur ; un `GET` nu suffit |
| 5 — navigateur | inutile | la donnée est déjà dans la réponse HTTP ; un navigateur appellerait `/api` |
| 6 — extraction LLM | inutile | la donnée est structurée (JSON), aucune ambiguïté à lever |

**Niveau retenu : 4 — pourquoi pas le 3 :** le niveau 3 (endpoint `/api`) est le
plus direct, mais il est explicitement interdit par le robots.txt ; l'utiliser
serait un contournement, sanctionné par l'énoncé. **Pourquoi pas le 5 :** un
navigateur n'apporte rien puisque `props.pageProps.artworkData` est déjà présent
dans la réponse HTTP brute d'une fiche détail — et il rappellerait `/api` en
coulisse.

**En-têtes nécessaires :** aucun. Un `GET` avec un simple `User-Agent`
identifiant renvoie 200 et la donnée complète (preuve : `curl` sur
`/art/1915.534`).

---

## 5. Ancrage des sélecteurs (les deux champs les plus importants)

| Champ | Ancrage retenu | Alternative écartée | Pourquoi elle est plus fragile ici | Si l'ancrage disparaît demain |
|---|---|---|---|---|
| `title` | `__NEXT_DATA__ → props.pageProps.artworkData.title` (donnée structurée) | balise `<h1>` du DOM ou `og:title` | le `<h1>` dépend du thème CSS et mélange titre + auteur ; l'`og:title` est tronqué | `ChampObligatoireAbsent` (erreur bruyante) |
| `artist` | `artworkData.creators[].description` | texte de la ligne d'auteur dans le DOM | la mise en forme de la ligne change ; le champ structuré distingue auteur, rôle et dates | `None` (œuvre traitée comme anonyme) |

Ordre de préférence appliqué : **donnée structurée** (JSON interne servi par la
page) > attribut de données > rôle/libellé > structure > classe CSS.

**Hypothèse vérifiée ?** ☑ oui — `tests/test_extraction.py` retire le champ de la
charge `__NEXT_DATA__` et vérifie que `extraire_detail` lève bien
`ChampObligatoireAbsent`.

---

## 6. Risques et contraintes

**Techniques**
- Le site peut cesser de servir `artworkData` côté serveur (bascule vers un rendu
  100 % client). Détection : le test d'extraction échouerait sur la fixture mise à
  jour ; repli = niveau 5 (navigateur), au prix d'une dépendance.
- Le nom du bloc `__NEXT_DATA__` est une convention Next.js ; une montée de version
  du framework pourrait le renommer.

**Juridiques**
- `robots.txt` : chemin `/art/` **autorisé** ; `/api` **interdit** et non demandé.
- CGU : données en Open Access CC0.
- RGPD : aucune donnée personnelle dans le périmètre (œuvres d'art).
- Part de la base collectée : 30 œuvres sur plusieurs dizaines de milliers — négligeable.

**Charge**
- concurrence max : 1 connexion.
- délai min : **10 s** — source : `Crawl-delay` du robots.txt.
- conduite sur 429/503 : respect de `Retry-After`, sinon repli exponentiel plafonné.
- conduite sur 403/401/CAPTCHA : **arrêt** (`CollecteRefusee`), preuve conservée.

---

## 7. Point de rupture et repli

- **Ce qui casserait le collecteur :** la disparition du bloc `__NEXT_DATA__` ou du
  sous-objet `artworkData` sur les fiches détail (`extraction._bloc_next_data`).
- **Détection :** `pytest tests/test_extraction.py` — rejoué sans réseau sur la
  fixture enregistrée.
- **Repli 1 :** rendre la fiche avec un navigateur (niveau 5), coût = dépendance
  Playwright + ~1 s de rendu par page.
- **Repli 2 :** si le front `artworksForSeeAlso` se tarit, élargir la liste de
  graines dans `config.toml` (coût nul).
- **Repli écarté :** appeler directement `/api` — il résoudrait la découverte
  d'œuvres, mais il est interdit par le robots.txt : ce n'est pas un repli, c'est
  une infraction.
