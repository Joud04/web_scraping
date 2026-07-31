# Fiche descriptive — Site 2, cible S19 (Automation Exercise)

> Diagnostic du second site du groupe. Le site 1 (S32, Cleveland Museum of Art)
> a sa propre fiche dans `fiche_descriptive.md`.
>
> Chaque affirmation ci-dessous a été vérifiée sur le site réel, à la date
> indiquée. Les chiffres sont reproductibles avec la commande donnée.

## 1. Identité de la cible

| | |
|---|---|
| Identifiant | **S19** |
| Site | Automation Exercise |
| URL de départ | https://automationexercise.com/products |
| Zone | International, hébergement États-Unis |
| Objet collecté | `Product` |
| Volume plafond | **60 objets** — plafond de la fiche de cible, jamais un objectif |
| Champs minimaux | `name`, `price`, `currency`, `category`, `brand`, `url` |
| Éléments spécifiques exigés | catégories, marques, recherche, détail et panier de test |
| Date du diagnostic | 31 juillet 2026 |

## 2. Conditions d'accès

### 2.1 robots.txt — le fichier n'existe pas

C'est le point qui distingue cette cible du site 1, et il se vérifie en une
requête :

```
GET https://automationexercise.com/robots.txt
→ 302 Found, Location: /
→ 200 OK, Content-Type: text/html, 51 976 octets
```

**Il n'y a pas de robots.txt.** Le site redirige la requête vers sa page
d'accueil, qui répond 200 avec un document HTML. Conséquences :

- aucun chemin n'est interdit ;
- aucun `Crawl-delay` n'est déclaré, donc **rien ne relève le délai configuré** ;
- le collecteur ne doit pas prendre ce HTML pour un fichier de règles.

Ce dernier point n'est pas théorique. Une page d'accueil peut contenir le mot
`Disallow` dans un texte ou un script ; lue comme un robots.txt, une telle ligne
interdirait le site entier et arrêterait la collecte sur une règle qui n'existe
pas. Le collecteur écarte donc toute réponse dont le type de contenu n'est pas
`text/plain`, et le comportement est verrouillé par
`tests/test_robots_s19.py::test_une_page_html_contenant_disallow_n_est_pas_appliquee`.

**L'absence de règle n'est pas une autorisation d'aller vite.** Le délai d'une
seconde entre deux requêtes est ici entièrement à notre charge : personne ne
l'impose, et il est appliqué quand même.

### 2.2 Légitimité de la collecte

Le site se décrit lui-même comme un terrain d'entraînement à l'automatisation :

```html
<meta name="description" content="This is for automation practice">
```

C'est sa raison d'être. La collecte est donc explicitement dans l'usage prévu,
ce qui n'exempte ni du délai, ni du User-Agent identifiant, ni de l'interdiction
de toute action irréversible — le panier de test n'est **pas** utilisé.

## 3. Rendu observé — la donnée est dans la réponse HTTP

```bash
python -m collecteur diagnostic --config config.s19.toml
```

| Mesure | Réponse HTTP brute |
|---|---|
| Statut | 200 |
| Taille HTML | 47 548 caractères |
| Produits présents dans la réponse | **34** |
| Rendu JavaScript nécessaire | **non** |

Les 34 produits de `/products` sont dans le HTML servi par le serveur. Le DOM
rendu dans le navigateur en montre autant : **l'écart est nul**.

C'est l'inverse du site 1, dont la page de recherche renvoie 0 œuvre sans
JavaScript. Et c'est ce qui décide de l'outillage : **aucun navigateur n'est
nécessaire**, donc ni Playwright, ni crawl4ai, ni Chromium, ni Docker. Un
navigateur coûterait ici une dépendance système et environ une seconde de rendu
par page pour produire exactement la même donnée.

## 4. Ancrages retenus

Ordre de préférence du projet, du plus stable au plus fragile :

| Rang | Type d'ancrage | Utilisé ici ? |
|---|---|---|
| 1 | donnée structurée du site | non — ni JSON-LD, ni bloc injecté |
| 2 | attribut de donnée | **oui** — `data-product-id`, `input#product_id` |
| 3 | rôle ou libellé accessible | non — absent de la page |
| 4 | structure du document | **oui, en second** — `h2` = prix, `p` = nom |
| 5 | classe CSS utilitaire | évité |

| Champ | Où il se lit | Page |
|---|---|---|
| `item_id` | `data-product-id` / `input#product_id` | liste et détail |
| `name` | `.productinfo p` / `.product-information h2` | liste et détail |
| `price` | `.productinfo h2` / `.product-information span span` | liste et détail |
| `currency` | déduit du symbole affiché (« Rs. » → `INR`) | — |
| `category` | `<p>Category: Women > Tops</p>` | **détail uniquement** |
| `brand` | `<p><b>Brand:</b> Polo</p>` | **détail uniquement** |
| `url` | `a[href^="/product_details/"]` | liste |

### Deux pièges de structure, vérifiés et non supposés

**1. Chaque produit figure deux fois dans le HTML de la liste.** Une fois dans
`.productinfo`, une fois dans `.product-overlay` affiché au survol. Un sélecteur
posé sur `[data-product-id]` compte donc **68 nœuds pour 34 produits**. On itère
sur les blocs `.product-image-wrapper` et on ne lit que `.productinfo`.
Verrouillé par `test_liste_compte_34_produits`.

**2. Catégorie et marque ne sont pas sur la page de liste.** Ce sont pourtant
deux des six champs minimaux exigés. Seule la fiche détail les porte, ce qui
impose une seconde requête par produit. Sans elle, un tiers du schéma resterait
vide.

## 5. Stratégie de parcours — catégories et marques tiennent lieu de pagination

Le site **ne pagine pas** `/products` : les 34 produits tiennent sur une page.
Il n'y a donc pas de « page 2 » à suivre. Ce qui structure le catalogue, ce sont
**7 catégories** et **8 marques**, chacune sur sa propre page de liste :

```
/products  →  /category_products/1 … /category_products/7
           →  /brand_products/Polo … /brand_products/Biba
```

Le parcours est un front en largeur amorcé par `/products` et étendu par ces
15 pages. C'est la forme que prend l'exigence « catégories, marques » de la
fiche de cible.

**La déduplication intervient avant la requête de détail**, pas après. Un
produit atteint par sa catégorie puis par sa marque ne coûte ainsi qu'une seule
requête. Le gain est mesuré : 102 produits rencontrés, 68 doublons écartés,
**68 requêtes de détail économisées**.

## 6. Résultats de la collecte réelle

```bash
python -m collecteur collecte --config config.s19.toml
```

| Mesure | Valeur |
|---|---|
| Pages de liste traitées | 16 |
| Requêtes HTTP | 50 |
| Objets vus | 102 |
| **Objets exportés** | **34** |
| Objets rejetés | 0 |
| Doublons détectés | 68 |
| Erreurs réseau | 0 |
| Champs obligatoires manquants | aucun |

L'invariant se vérifie : 34 + 0 + 68 = 102.

**Aucun champ nul sur aucune ligne** : les six champs minimaux sont renseignés
sur les 34 objets. 7 catégories et 8 marques distinctes sont représentées, les
prix vont de 278 à 5 000 INR.

### Pourquoi 34 et non 60

Le plafond de la fiche de cible est de 60 objets. Le catalogue du site en
contient **34**. Le plafond n'est donc jamais atteint : c'est une borne
supérieure, pas un objectif, et la collecte s'arrête quand le catalogue est
épuisé — pas quand un compteur est satisfait.

### Délai réellement appliqué

Mesuré à l'émission des requêtes, sur six requêtes consécutives :

```
écarts entre émissions : 1.000, 1.000, 1.000, 1.000, 1.000 s
```

Le délai configuré est d'une seconde et il est tenu exactement. La mesure porte
sur l'instant d'**émission** de chaque requête, pas sur l'horodatage des objets
produits : ce dernier dérive du temps de réponse du serveur et ne mesure pas
l'espacement réel.

## 7. Limites connues

1. **Le catalogue est petit.** 34 produits, ce qui rend la cible peu
   représentative des problèmes de volume. Le plafond de 60 n'est jamais atteint.
2. **La recherche n'est pas couverte.** La fiche de cible la cite parmi les
   éléments spécifiques. Elle passe par un formulaire `POST /search_product` ;
   les catégories et marques donnent déjà accès à l'intégralité du catalogue,
   donc la recherche n'apporterait aucun produit supplémentaire. C'est un choix
   assumé, pas un oubli.
3. **Le panier de test n'est pas utilisé**, délibérément. Ajouter au panier est
   une action d'écriture ; l'énoncé interdit toute action irréversible, et
   aucune donnée du panier ne figure dans les champs minimaux.
4. **La devise est déduite, pas déclarée.** Le site affiche « Rs. » et n'écrit
   jamais le code ISO. La table de correspondance traduit « Rs. » en `INR`,
   ce qui est une interprétation — correcte pour ce site, mais qui se déclare.
5. **La déduplication ne survit pas au processus** (`normalisation.Deduplicateur`
   vit en mémoire). Deux exécutions successives ne se dédoublonnent pas entre
   elles. Assumé sur ce volume : une base de données serait de la complexité
   gratuite.
