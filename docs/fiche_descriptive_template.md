# Fiche descriptive de cible — modèle

> Gabarit repris du module 01 (`travaux/module01/fiche-catalog-static.txt`) et
> aligné sur la rubrique 2 du compte rendu.
>
> **Règle qui commande tout le reste :** une affirmation sans preuve ne compte pas.
> « Le site est une SPA » est une opinion. « La réponse HTTP contient 812 caractères
> de texte hors balises et aucun titre de produit, le DOM rendu en contient 14 300 »
> est une observation. Chaque case « Preuve » reçoit une commande exécutée et sa
> sortie, pas un commentaire.
>
> Copier ce fichier en `docs/fiche_descriptive.md` (une par cible attribuée) et le
> remplir. Ne pas le remplir de mémoire depuis `MATRICE_CIBLES_ELEVES` : cette
> colonne est une observation datée du 30/07/2026, pas une garantie, et une
> divergence documentée est valorisée.

---

```
Cible ................. S__ — <nom du site>
URL de départ ......... <URL exacte>
Date d'analyse ........ <AAAA-MM-JJ>
Analyste .............. <Nom Prénom> (groupe de 3 — 2 sites)
Objet collecté ........ <Product | Destination | Artwork | Book | ...>
Volume plafond ........ <n> objets (source : fiche de cible — plafond, pas objectif)
Champs minimaux ....... <liste exacte issue de la fiche de cible>
Exigence complémentaire <celle de la fiche, ou « — »>
```

---

## 1. Source

| Élément | Valeur | Preuve (commande + sortie) |
|---|---|---|
| Famille de site | statique / SPA / API / combinaison | |
| Statut HTTP de l'URL de départ | | `curl -sI <URL>` |
| `Content-Type` | | |
| Taille de la réponse | … octets | `curl -s -o /dev/null -w "%{http_code} %{size_download}" <URL>` |
| `robots.txt` publié | oui / non | `curl -s <origine>/robots.txt` |
| `sitemap.xml` publié | oui / non | |

### Lecture du `robots.txt`

> Le piège relevé par la notice : écrire « robots.txt vérifié » sans dire ce qu'il
> contenait. La question n'est pas si vous l'avez ouvert, mais ce que vous en
> concluez **pour votre chemin**.

```
<coller ici le contenu intégral, ou les règles applicables>
```

- Mon chemin de collecte est-il autorisé ? Par quelle règle exactement ?
- `Crawl-delay` déclaré : `<valeur ou « non déclaré »>`
- Délai réellement appliqué : `<valeur>` s → **doit être ≥ au Crawl-delay**
- Chemins interdits croisant mon périmètre : `<liste ou « aucun »>`

### Conditions d'utilisation

- URL des CGU : `<URL ou « aucune publiée »>`
- Ce qu'elles disent de la collecte automatisée : `<citation courte>`
- Conclusion : `<collecte poursuivie / cible à basculer>`

---

## 2. Surface porteuse de la donnée

> Le piège : conclure depuis ce que montre le navigateur. Le navigateur affiche le
> DOM **après** exécution du JavaScript ; il ne dit rien de la réponse HTTP.
> **La comparaison chiffrée entre les deux est le diagnostic.**
>
> `python -m collecteur diagnostic --url <URL>` produit la moitié gauche du tableau.

| Élément | Observation | Preuve |
|---|---|---|
| HTML initial — marqueur cherché | `<ex. data-sku=, itemprop=name>` | occurrences : … |
| HTML initial — objets présents | … / … | |
| DOM après rendu — objets présents | … | outils de dév., onglet Éléments |
| **Écart chiffré HTML brut ↔ DOM** | | ← c'est le diagnostic |
| Requête(s) réseau porteuse(s) | `<méthode + URL>` | onglet Réseau, filtre XHR/Fetch |
| Format de réponse | HTML / JSON / JSON-LD | |
| Pagination, défilement ou filtre | `<motif observé>` | |
| Condition d'arrêt | `<ex. absence de <a rel="next">>` | vérifiée par dépassement volontaire |

**Conformité à la fiche de cible :** ☐ conforme ☐ divergence, voici ce que j'ai observé :

Si une requête réseau porte les données, répondre aux deux questions qui décident
de son usage :
- qu'est-ce qui prouve qu'elle est **publique** et **réellement utilisée par la page** ?
- exige-t-elle un jeton, une signature ou un en-tête privé ? Si oui : **on n'y touche pas**.

---

## 3. Champs disponibles et couverture du contrat

| Champ du modèle | Source exacte | Obligatoire ? | Règle si absent |
|---|---|---|---|
| | | | |

Champs minimaux de la fiche **non trouvés sur la cible** : `<liste ou « aucun »>`
→ pour chacun : est-ce une absence réelle, ou un ancrage que je n'ai pas su écrire ?

---

## 4. Technique d'acquisition retenue

| Niveau | Statut | Justification |
|---|---|---|
| 1 — jeu de données publié | | testé : `<URLs essayées>` → `<statuts>` |
| 2 — API documentée et autorisée | | |
| 3 — endpoint JSON interne | | |
| 4 — HTTP + parser | | |
| 5 — navigateur | | |
| 6 — extraction LLM | | |

**Niveau retenu :** `<n>` — **pourquoi celui-ci et pas le précédent :**

> Une réponse qui tient : « le niveau *n-1* ne fonctionne pas parce que *observation
> chiffrée* ». Une réponse qui ne tient pas : « le niveau *n* est plus pratique ».

**En-têtes nécessaires :** `<liste ou « aucun »>` — et la preuve que l'appel nu suffit,
ou pas.

---

## 5. Ancrage des sélecteurs (les deux champs les plus importants)

| Champ | Ancrage retenu | Alternative écartée | Pourquoi elle est plus fragile **sur cette page** | Si l'ancrage disparaît demain |
|---|---|---|---|---|
| | | | | erreur bruyante / champ vide / repli sur `<second ancrage>` |
| | | | | |

Ordre de préférence appliqué : donnée structurée > attribut de données >
rôle ou libellé accessible > structure > classe CSS utilitaire.

**Hypothèse vérifiée ?** ☐ oui, en retirant l'ancrage de la page enregistrée et en
observant ce que fait le programme ☐ non, seulement raisonnée

---

## 6. Risques et contraintes

**Techniques**
-

**Juridiques**
- `robots.txt` : chemin visé autorisé / interdit
- CGU : `<statut>`
- RGPD : donnée personnelle dans le périmètre ? `<oui/non>` — si oui, **on ne collecte pas**
- Part substantielle de la base collectée : `<n>/<total>`

**Charge**
- concurrence max : `<n>` connexion(s)
- délai min : `<n>` s — **source : `<Crawl-delay` du robots.txt / choix documenté>`**
- conduite sur 429 : respect de `Retry-After`, sinon repli exponentiel plafonné à `<n>` s
- conduite sur 403/401/CAPTCHA : **arrêt**, preuve conservée, formateur prévenu

---

## 7. Point de rupture et repli

- **Ce qui casserait le collecteur, et où précisément :**
- **Détection :** `<commande de non-régression exécutable en une ligne>`
- **Repli 1 :** `<lequel, coût estimé>`
- **Repli 2 :** `<lequel, coût estimé>`
- **Repli écarté :** `<lequel, et pourquoi il ne résout aucun des modes de panne identifiés>`
