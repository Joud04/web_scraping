# Démonstration orale — 5 minutes

> **Fenêtre visée : 4 min 30 – 5 min 30**, chronométrée au premier mot.
> L'énoncé applique une pénalité mécanique au dépassement : on ne finit pas la
> phrase, on s'arrête.
>
> Groupe : **Joud Atallah**, **Walid Hdilou**, **Amine Kaoutar** — 2 sites cibles.

---

## ⚠️ À LIRE AVANT TOUT — trois pièges qui coûtent des points

### Piège 1 — Ne PAS prouver le Crawl-delay avec l'écart entre horodatages

C'est le réflexe naturel, et c'est un piège. Dans `samples/sample_output.json`
(site 1), les écarts réels entre `scraped_at` consécutifs sont :

```
obj1 → obj2 : 10,04 s
obj2 → obj3 : 10,31 s
obj3 → obj4 :  9,72 s   ← INFÉRIEUR À 10
obj4 → obj5 : 10,01 s
```

Si le formateur fait défiler le fichier, il trouve **9,72 s** et pose la
question qui tue : « votre Crawl-delay de 10 s n'est pas respecté ». Vous
auriez tort de paniquer, mais vous auriez l'air d'avoir tort.

**Pourquoi 9,72 s ?** `scraped_at` est posé à la **construction de l'objet**,
après réception et parsing de la réponse. L'écart entre deux horodatages vaut
donc `délai + temps_de_réponse(n+1) − temps_de_réponse(n)` : il oscille autour
de 10 s au lieu de le minorer. Le délai garanti porte sur l'**émission** des
requêtes, mesurée sur une horloge monotone (`acquisition.py:153`, `_attendre`).

**Ce qu'on montre à la place — et qui est irréfutable :**

```bash
pytest tests/test_robots_s32.py -v
```

12 tests, hors réseau, dont `test_le_delai_est_releve_de_1s_a_10s` et
`test_le_delai_configure_plus_long_n_est_pas_abaisse`. C'est déterministe, ça
tourne en une seconde, et ça ne dépend pas de l'état du réseau ce jour-là.

**Si la question tombe quand même**, la réponse tient en deux phrases :
> « L'horodatage est posé à la construction de l'objet, pas à l'émission de la
> requête — il dérive du temps de réponse du serveur. Le délai garanti est
> mesuré sur horloge monotone à l'émission, et c'est ce que vérifient les douze
> tests de `test_robots_s32.py`. »

### Piège 2 — La démo live écrase l'échantillon versionné

Toute exécution de `collecte` régénère `samples/sample_output_s19.json` (ou
`sample_output.json`). Une démo à 3 objets remplace donc l'échantillon de 10
objets **versionné dans le dépôt**.

**Réflexe obligatoire après toute démo live :**

```bash
git checkout -- samples/
git status --short      # doit être vide
```

À faire **avant** de quitter la salle. Un échantillon à 3 objets commité par
accident après la soutenance, c'est un livrable dégradé.

### Piège 3 — Ne jamais lancer la collecte complète du site 1 en direct

30 œuvres × 10 s de Crawl-delay = **5 minutes**, soit tout le temps de parole.
Le site 1 se démontre sur des **fichiers déjà produits** ; seul le site 2 se
prête à une collecte en direct (8 s pour 3 objets).

---

## ⏱️ SCRIPT MINUTÉ

> Débit visé : ~140 mots/minute. Les scripts ci-dessous sont calibrés.
> Le texte en `>` est à dire ; le reste est une indication de manœuvre.

### 0:00 – 1:00 — Introduction et architecture unifiée — **JOUD**

*(Écran : `README.md`, section « Groupe et périmètre »)*

> « Bonjour. Nous sommes trois : Walid Hdilou, Amine Kaoutar et moi-même, Joud
> Atallah. Nous avons traité deux sites — le Cleveland Museum of Art, et
> Automation Exercise.
>
> La décision structurante n'est pas dans les sélecteurs, elle est dans
> l'architecture. Nous avons refusé d'écrire deux collecteurs. Il y a **un seul
> socle** : configuration, acquisition, normalisation, modèle, export,
> journalisation. **Seuls les modules d'extraction connaissent une cible.**
>
> L'intérêt se mesure : nos deux sites ont des contraintes **opposées**. Le
> premier impose un Crawl-delay de 10 secondes et interdit son API. Le second
> ne publie aucun `robots.txt`. Et c'est le même code d'acquisition qui traite
> les deux — donc les règles de politesse sont écrites **une fois**, et testées
> **une fois**.
>
> Côté outils : `httpx`, `BeautifulSoup`, `lxml`, `pydantic`. **Quatre
> dépendances.** Pas de Playwright, pas de Scrapy, pas de Docker, pas de base
> de données. Sur le site 2, un prototype embarquait crawl4ai, Playwright et
> Chromium ; nous l'avons retiré après avoir **mesuré** que la donnée était
> déjà dans la réponse HTTP. Je laisse Walid présenter le premier site. »

*(Écran : basculer sur `docs/architecture.md`, schéma de flux)*

---

### 1:00 – 2:30 — Site 1, S32 Cleveland Museum — **WALID**

*(Écran : `docs/fiche_descriptive.md`, section 2 — le `robots.txt` relevé)*

> « Le site 1, c'est le Cleveland Museum of Art. La difficulté y est
> immédiate : la page de recherche renvoie **zéro œuvre** dans sa réponse HTTP.
> Zéro. Elle peuple ses résultats par un appel à `/api`.
>
> Et `/api` est en **`Disallow`** dans le `robots.txt`. »

*(Écran : `tests/fixtures/robots.txt` — pointer les deux lignes)*

> « Donc la voie naturelle est fermée. Et aucun navigateur ne la rouvre :
> piloter Chrome rappellerait `/api` en coulisse. Ce serait un contournement,
> et l'énoncé le rend non évaluable.
>
> Notre solution ne contourne rien. Chaque fiche d'œuvre déclare ses œuvres
> voisines dans un champ `artworksForSeeAlso`, servi **côté serveur**, sur un
> chemin **autorisé**. On part de cinq graines et on parcourt le catalogue de
> proche en proche. »

*(Écran : `src/collecteur/extraction.py:134` — `extraire_liens_lies`)*

> « Deuxième point : le `robots.txt` déclare `Crawl-delay: 10`. Notre
> configuration proposait 1 seconde. Le collecteur **relève** le délai à 10
> secondes — il ne l'abaisse jamais. »

*(Écran : `pytest tests/test_robots_s32.py -v` — laisser tourner, 1 seconde)*

> « Douze tests le vérifient, hors réseau : le Crawl-delay est lu, le délai est
> relevé de 1 à 10 secondes, un délai plus long n'est pas abaissé, et `/api`
> est refusé **avant** toute requête réseau. Résultat : 30 œuvres, cinq champs
> minimaux, zéro rejet. Amine pour le site 2. »

---

### 2:30 – 3:45 — Site 2, S19 Automation Exercise — **AMINE**

*(Écran : `docs/fiche_descriptive_s19.md`, section 2.1)*

> « Le site 2 est l'inverse exact. Ici, `/robots.txt` répond **302** et redirige
> vers la page d'accueil. **Il n'y a pas de fichier de règles.** Aucun chemin
> interdit, aucun Crawl-delay.
>
> Deux conséquences. La première : rien ne nous impose de délai, donc nous en
> appliquons un quand même — une seconde, entièrement à notre charge. L'absence
> de règle n'est pas une autorisation d'aller vite.
>
> La seconde est plus subtile. Le serveur renvoie 52 000 octets de HTML sur
> `/robots.txt`. Si on le lit comme un fichier de règles, une ligne
> `Disallow:` présente par hasard dans la page interdirait le site entier. Notre
> collecteur refuse donc toute réponse qui n'est pas `text/plain`. »

*(Écran : `src/collecteur/acquisition.py:98`)*

> « Ensuite, la navigation. Le site **ne pagine pas** : les 34 produits tiennent
> sur une page. Ce sont les **7 catégories** et les **8 marques** qui
> structurent le catalogue — 16 pages de liste au total.
>
> Un piège nous a coûté du temps : chaque produit figure **deux fois** dans le
> HTML, une fois visible et une fois dans le calque affiché au survol. Un
> sélecteur naïf compte 68 produits au lieu de 34. »

*(Écran : `tests/test_extraction_s19.py:39` — `test_liste_compte_34_produits`)*

> « Enfin, la catégorie et la marque ne sont **pas** sur la page de liste, alors
> que ce sont deux des six champs exigés. Il faut ouvrir chaque fiche. On
> dédoublonne donc **avant** cette requête : 102 produits rencontrés, 68
> doublons écartés, **68 requêtes économisées**.
>
> Les prix sont convertis en `Decimal`, jamais en `float` — un prix qui dérive
> au centième est une donnée fausse. Résultat : 34 produits, six champs, **aucune
> valeur nulle**, zéro rejet. »

*(Écran optionnel si le temps le permet — `data/sortie_s19.jsonl`)*

---

### 3:45 – 5:00 — Qualité et conclusion — **JOUD**

*(Écran : terminal)*

```bash
pytest
```

> « 105 tests, **aucun ne touche le réseau**. Les deux cibles sont rejouées
> depuis des pages enregistrées, donc la vérification est reproductible même si
> les sites changent demain. »

*(Écran : `ruff check` puis `ruff format --check`)*

> « Zéro remarque du linter, 20 fichiers formatés.
>
> Un mot sur l'export, parce que c'est une exigence de l'énoncé : le JSONL est
> écrit **en temps réel**, un objet par ligne, avec vidage du tampon à chaque
> ligne. Une collecte interrompue au milieu laisse un fichier exploitable. Ce
> n'est pas une affirmation : c'est un test. »

*(Écran : `src/collecteur/export.py:126` — le `flush`)*

> « Ce que ce projet nous a appris tient en une phrase : **la contrainte n'est
> pas l'ennemi de la collecte, c'est ce qui la rend défendable.** Le site 1
> nous interdisait son API — nous avons trouvé un chemin autorisé plutôt qu'un
> contournement. Le site 2 ne nous interdisait rien — nous nous sommes imposé
> un délai quand même.
>
> Et s'il fallait retenir une seule limite, ce serait la déduplication : elle
> vit en mémoire et ne survit pas au processus. C'est la première chose que
> nous corrigerions, parce que c'est la seule qui produit de la donnée
> **fausse** plutôt que de la donnée manquante. Merci. »

---

## 🖥️ CHECKLIST DÉMO — À PRÉPARER AVANT D'ENTRER

### Avant la soutenance (la veille)

- [ ] `git status --short` → **vide**
- [ ] `pytest` → **105 passed**
- [ ] `ruff check` → All checks passed
- [ ] Terminal en **police 16 pt minimum**, thème clair (les vidéoprojecteurs
      écrasent les contrastes sombres)
- [ ] `config.toml` **et** `config.s19.toml` présents (ils sont hors dépôt —
      `cp config.example.toml config.toml` et
      `cp config.s19.example.toml config.s19.toml`)
- [ ] `data/sortie_s19.jsonl` et `samples/` déjà peuplés — **la démo ne doit
      pas dépendre du réseau de la salle**
- [ ] Onglets déjà ouverts dans l'éditeur (voir tableau ci-dessous)

### Commandes exactes, dans l'ordre

| # | Commande | Durée | Quand |
|---|---|---|---|
| 1 | `pytest tests/test_robots_s32.py -v` | ~1 s | 2:10, Walid |
| 2 | `pytest` | ~2 s | 3:45, Joud |
| 3 | `ruff check && ruff format --check` | ~1 s | 4:05, Joud |
| 4 | *(optionnel)* `python -m collecteur collecte --config config.s19.toml --max-objets 3 --sortie data/demo.jsonl` | **8 s** | seulement si l'on est en avance |

> **Après la commande 4, impérativement :** `git checkout -- samples/`

### Fichiers à ouvrir, avec les lignes exactes

| Fichier | Ligne | Ce qu'on montre |
|---|---|---|
| `README.md` | § Groupe et périmètre | 3 membres, 2 sites |
| `docs/architecture.md` | schéma de flux | socle commun, 2 modules d'extraction |
| `tests/fixtures/robots.txt` | 3 et 6 | `Crawl-delay: 10`, `Disallow: /api` |
| `src/collecteur/extraction.py` | **134** | `extraire_liens_lies` — `artworksForSeeAlso` |
| `src/collecteur/acquisition.py` | **98** | garde `text/plain` sur le `robots.txt` |
| `src/collecteur/acquisition.py` | **153** | `_attendre` — horloge monotone |
| `src/collecteur/acquisition.py` | **31** | `REFUS_EXPLICITES` — 401/403/407/451 |
| `tests/test_robots_s32.py` | **94** | `test_le_delai_est_releve_de_1s_a_10s` |
| `tests/test_extraction_s19.py` | **39** | `test_liste_compte_34_produits` (34, pas 68) |
| `src/collecteur/modele.py` | **161** | `price: Decimal \| None` |
| `src/collecteur/export.py` | **126** | `flush()` par objet |
| `samples/sample_output_s19.json` | 1–12 | 6 champs, aucune valeur nulle |

### Plan B si la démo échoue

Réseau coupé, projecteur capricieux, terminal qui ne répond pas — **on ne
répare pas en direct**. On bascule sur :

1. `samples/sample_output.json` et `samples/sample_output_s19.json` — déjà
   produits, lisibles, versionnés ;
2. la sortie de `pytest` (elle ne dépend d'aucun réseau) ;
3. `docs/fiche_descriptive.md` et `docs/fiche_descriptive_s19.md`, où tous les
   chiffres sont écrits.

Phrase de bascule, à dire calmement :
> « La démonstration en direct dépend du réseau, je passe sur les résultats déjà
> produits — ils sont dans le dépôt. »

---

## 🎯 LES 5 QUESTIONS QUI TOMBENT — ET LES RÉPONSES

### Q1 — « Pourquoi pas Playwright ou Selenium ? »

> « Parce que nous avons **mesuré** avant de choisir. Sur le site 2, la réponse
> HTTP brute de `/products` contient déjà les 34 produits : l'écart avec le DOM
> rendu est **nul**. Sur le site 1, la donnée des fiches est dans le bloc
> `__NEXT_DATA__`, servi côté serveur. Dans les deux cas, un navigateur aurait
> coûté une dépendance système et environ une seconde de rendu par page pour
> produire **exactement la même donnée**.
>
> Sur le site 1, il aurait même été nuisible : Chrome aurait rappelé `/api` en
> coulisse, or `/api` est interdit par le `robots.txt`. Le navigateur nous
> aurait fait franchir une limite que nous respectons volontairement.
>
> Un prototype du site 2 embarquait crawl4ai, Playwright, Chromium et Docker.
> Nous l'avons retiré — et au passage, `crawl4ai` n'était même pas déclaré dans
> `requirements.txt`, il était installé à part dans le `Dockerfile` : le
> collecteur était inexécutable hors conteneur. »

**Si on insiste — « et si le site passait en 100 % client demain ? »**
> « On ajouterait la dépendance ce jour-là, quand la mesure la justifie. Pas
> avant. C'est exactement la démarche que nous venons de décrire. »

---

### Q2 — « Comment prouvez-vous que vous avez respecté le serveur ? »

> « Par des tests, pas par des affirmations. Et les deux sites posaient des
> problèmes différents.
>
> **Site 1** : le `robots.txt` déclare `Crawl-delay: 10`. Notre configuration
> proposait 1 seconde ; le collecteur **relève** à 10. Douze tests dans
> `test_robots_s32.py` le vérifient hors réseau — le délai relevé de 1 à 10, un
> délai plus long **non abaissé**, et `/api` refusé **avant** toute requête.
>
> **Site 2** : il n'y a **pas** de `robots.txt`. Rien ne nous impose de délai —
> nous en appliquons un quand même. Six tests dans `test_robots_s19.py`
> verrouillent ça, dont un qui vérifie qu'une page HTML contenant `Disallow: /`
> n'est **pas** appliquée comme une règle.
>
> Et le délai porte sur l'**émission** des requêtes, mesurée sur horloge
> monotone. Mesuré à l'émission : 1,000 seconde, six fois de suite. »

**Si on montre un écart de 9,72 s dans le JSONL :**
> « C'est l'horodatage de **construction de l'objet**, pas d'émission de la
> requête — il dérive du temps de réponse du serveur, donc il oscille autour de
> 10 secondes. Le délai garanti est en amont, sur horloge monotone. »

**Et sur les refus :**
> « Un 401, 403, 407 ou 451 lève `CollecteRefusee`, qui n'est
> **volontairement pas** une sous-classe de l'erreur temporaire : aucune boucle
> de réessai ne peut la rattraper par accident. La collecte s'arrête et le refus
> est documenté. Il n'est jamais contourné. »

---

### Q3 — « Comment gérez-vous les doublons et la qualité des données ? »

> « Trois niveaux.
>
> **La clé de déduplication vient de la page, pas de l'URL.** Sur le site 2,
> c'est `data-product-id` sur la liste et `input#product_id` sur la fiche — la
> même valeur des deux côtés. Sur le site 1, c'est le numéro d'accession, gravé
> dans l'objet physique. Dans les deux cas, la clé survit à une réorganisation
> des URL, ce que ne ferait pas l'URL elle-même.
>
> **La déduplication intervient au bon moment.** Sur le site 2, un produit est
> atteignable par sa catégorie **et** par sa marque. On dédoublonne **avant** la
> requête de détail : 102 produits rencontrés, 68 doublons, donc 68 requêtes
> économisées.
>
> **Le schéma est strict.** `extra="forbid"` en Pydantic : un champ inattendu
> fait rejeter l'objet avec son motif dans `data/rejets.jsonl`, au lieu de
> passer en silence. Et nous distinguons **trois états** — `None`, la chaîne
> vide, et zéro. Sur un catalogue produit ça compte : `price = None` signifie
> "pas de prix affiché", `price = 0` signifie "gratuit". Les confondre
> fausserait toute moyenne. Un prix illisible devient donc `None`, jamais 0. »

**Preuve chiffrée à avoir en tête :**
> « Sur les 34 produits du site 2 : **aucune valeur nulle**, sur aucun des six
> champs. 7 catégories, 8 marques, prix de 278 à 5 000 roupies. »

---

### Q4 — « Pourquoi parcourir les catégories au lieu de la pagination ? »

> « Parce qu'il n'y a **pas** de pagination. Les 34 produits du catalogue
> tiennent sur une seule page — il n'existe pas de "page 2" à suivre.
>
> Ce qui structure ce catalogue, ce sont **7 catégories** et **8 marques**,
> chacune sur sa propre page de liste. Les parcourir, c'est la forme que prend
> l'exigence "catégories, marques" de notre fiche de cible : 16 pages de liste
> au total.
>
> Et ça sert un second objectif. La catégorie et la marque sont deux des six
> champs exigés, et elles ne figurent **pas** sur la page de liste — seule la
> fiche détail les porte. Le parcours par catégories nous fait donc traverser
> tout le catalogue, et la requête de détail remplit les deux champs manquants. »

**Sur la recherche, si on la mentionne :**
> « Elle passe par un `POST /search_product`. Nous ne l'avons pas couverte, et
> c'est un choix, pas un oubli : les catégories et les marques donnent déjà
> accès à l'intégralité du catalogue, la recherche n'apporterait aucun produit
> supplémentaire. C'est écrit dans nos limites. »

---

### Q5 — « Comment vos tests sont-ils structurés ? »

> « 105 tests, et le principe directeur est qu'**aucun ne touche le réseau**.

| Fichier | Tests | Ce qu'il verrouille |
|---|---|---|
| `test_normalisation_prix.py` | 32 | prix en `Decimal`, devise ISO |
| `test_export.py` | 13 | l'écrivain JSONL lui-même |
| `test_extraction_s19.py` | 13 | site 2 : liste, détail, catégorie, marque |
| `test_robots_s32.py` | 12 | site 1 : Crawl-delay 10 s, `/api` refusé |
| `test_deduplication.py` | 11 | clés et rejet d'incomplet |
| `test_normalisation.py` | 11 | texte NFC, URL |
| `test_extraction.py` | 7 | site 1 : champs de la fiche |
| `test_robots_s19.py` | 6 | site 2 : `robots.txt` absent |

> Les deux cibles sont rejouées depuis des **pages enregistrées** —
> `tests/fixtures/`. C'est ce qui rend la vérification reproductible : si le
> Cleveland Museum refond son site demain, nos tests tournent toujours, et ils
> nous **disent** que l'extraction a cassé au lieu de nous laisser produire des
> lignes vides.
>
> Trois exemples de ce qu'un test attrape et qu'une relecture ne voit pas :
> - `test_liste_compte_34_produits` : le site affiche chaque produit **deux
>   fois** dans le HTML ; sans ce test on collectait 68 doublons ;
> - un test de régression sur `normaliser_prix` : le motif tronquait
>   « Rs. 1500 » en **150**. Silencieusement. Il est resté invisible tant que le
>   projet n'a traité que des œuvres d'art, qui n'ont pas de prix ;
> - `test_une_page_html_contenant_disallow_n_est_pas_appliquee` : une page HTML
>   renvoyée par `/robots.txt` ne doit pas devenir une règle. »

---

## 👥 RÉPARTITION DES RÔLES

| Temps | Durée | Qui | Sujet |
|---|---|---|---|
| 0:00 – 1:00 | **1:00** | **Joud** | Groupe, architecture unifiée, sobriété des outils |
| 1:00 – 2:30 | **1:30** | **Walid** | Site 1 — `/api` interdit, `artworksForSeeAlso`, Crawl-delay |
| 2:30 – 3:45 | **1:15** | **Amine** | Site 2 — `robots.txt` absent, catégories/marques, `Decimal` |
| 3:45 – 5:00 | **1:15** | **Joud** | 105 tests, `ruff`, export temps réel, conclusion |

**Total de parole :** Joud 2:15 — Walid 1:30 — Amine 1:15.

Le déséquilibre est assumé et se justifie : Joud ouvre et ferme parce que
l'architecture commune et la qualité transverse sont sa contribution ; Walid et
Amine défendent chacun **leur** site, celui qu'ils ont diagnostiqué. Chacun
parle donc de ce qu'il a réellement fait — c'est exactement ce que le formateur
cherche à vérifier.

> **Si vous préférez équilibrer** : Joud cède les 30 dernières secondes
> (`ruff` + export temps réel) à Amine, et garde la conclusion. On arrive à
> 1:45 / 1:30 / 1:45.

### Règles de passage de parole

- **Une phrase de relais, pas un silence.** « Je laisse Walid présenter le
  premier site. » — la transition est préparée, pas improvisée.
- **Celui qui parle tient le clavier.** On ne dicte pas à quelqu'un d'autre quoi
  taper : ça coûte dix secondes à chaque fois.
- **Les deux autres ne coupent jamais**, même pour compléter. Si un point est
  oublié, il ressortira aux questions.
- **Chacun connaît le script des deux autres.** Si l'un est bloqué, le suivant
  enchaîne.

### Répétition — le seul entraînement qui compte

Chronométrer **trois fois**, à voix haute, avec l'écran. Pas dans sa tête : on
lit trois fois plus vite qu'on ne parle, et c'est ainsi qu'on se retrouve à
7 minutes le jour J.

Si le premier passage dépasse 5:30, **couper du contenu, pas accélérer le
débit**. Les deux coupes les moins coûteuses, dans l'ordre :

1. la démo live du site 2 (commande 4) — elle est optionnelle ;
2. le détail du piège des 68 doublons — il se garde pour les questions.

---

## 📌 CARTE MÉMOIRE — les chiffres, si tout le reste s'efface

| | |
|---|---|
| Tests | **105**, 0 échec, 0 ignoré, **0 réseau** |
| Linter | `ruff check` ✅ — `ruff format` ✅ 20 fichiers |
| Dépendances d'exécution | **4** — `httpx`, `beautifulsoup4`, `lxml`, `pydantic` |
| Site 1 — délai | **10 s**, imposé par le `Crawl-delay`, relevé automatiquement |
| Site 1 — parcours | graines + `artworksForSeeAlso`, `/api` jamais demandé |
| Site 2 — `robots.txt` | **absent** (302), délai de 1 s **à notre charge** |
| Site 2 — parcours | 16 pages : 1 liste + 7 catégories + 8 marques |
| Site 2 — collecte | 102 vus → **34 exportés**, 0 rejet, 68 doublons, 0 erreur |
| Site 2 — qualité | 6 champs, **aucune valeur nulle**, prix en `Decimal` |
| Export | JSONL, une ligne par objet, `flush` à chaque ligne |

**La phrase à ne pas oublier, si on n'en retient qu'une :**

> « La contrainte n'est pas l'ennemi de la collecte, c'est ce qui la rend
> défendable. »
