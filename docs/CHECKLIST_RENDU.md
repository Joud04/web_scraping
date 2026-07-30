# Ordre de travail et checklist de rendu

Reconstitué depuis `ENONCE_TP`, `GRILLES_NOTATION` et `NOTICE_TRAME`.
Ces fichiers portent la mention « diffusion restreinte » : ils **ne sont pas**
versionnés dans ce dépôt public (voir `.gitignore`).

## Les trois notes — indépendantes, non compensées

| Note | Objet | Support | Poids |
|---|---|---|---|
| 1 | conception, architecture et choix des outils | dépôt + rapport | /20 |
| 2 | présentation de **5 minutes** | passage à l'oral | /20 |
| 3 | réponses aux **5 questions** | échange après la présentation | /20 |

### Note 1 — répartition des points

| Critère | Pts | Ce qui fait la différence |
|---|---|---|
| Diagnostic et stratégie d'acquisition | **4** | le plus lourd : à traiter en premier, chiffres à l'appui |
| Architecture et séparation | 3 | six responsabilités identifiables, config séparée du code |
| Modèle de données et qualité | 3 | identifiant, traçabilité, normalisations, absent ≠ vide, dédup |
| Choix des outils et comparaison | 3 | alternative écartée, **absence de complexité gratuite** |
| Ancrage des sélecteurs | 2 | deux champs, et ce qui se passe si l'ancrage disparaît |
| Vérification et reproductibilité | 3 | rejouable **sans réseau**, commandes copiables |
| Usage responsable et IA | 2 | robots.txt, volume, délai, aucun secret, IA déclarée |

Paliers : absent 0 · amorcé 1 · fonctionnel 2 · solide 3 · maîtrisé 4
(sur /3 : 0 / 1 / 1,5 / 2,5 / 3 — sur /2 : 0 / 0,5 / 1 / 1,5 / 2).
Somme exacte, aucun arrondi.

### Note 2 — la pénalité de temps est mécanique

| Durée mesurée | Plafond sur « Respect du temps » (/4) |
|---|---|
| **4:30 – 5:30** | 4 — aucune pénalité |
| 4:00 – 4:29 ou 5:31 – 6:00 | 3 |
| < 4:00 ou > 6:00 | **1** |

Chronomètre déclenché au premier mot, durée consignée. Interruption à 6:30.
Découpage indicatif de l'énoncé : 0:00–0:40 cible et difficulté · 0:40–1:40
diagnostic et stratégie · 1:40–2:40 architecture et modèle · 2:40–4:10
démonstration et preuves · 4:10–5:00 limites, IA, amélioration prioritaire.

### Note 3 — cinq questions, une par famille

1. **Chemin d'une donnée** — suivre un champ de la réponse Web jusqu'au fichier exporté
2. **Choix des outils** — pourquoi celui-ci, et ce qui le remplacerait
3. **Diagnostic et panne** — raisonner sur un cas non rencontré
4. **Modèle et qualité** — schéma, normalisations, déduplication
5. **Accès responsable et IA** — où l'on s'arrête, et ce qui a été vérifié

0 à 4 par réponse. **Une reformulation du rapport sans lien avec le code est notée 1.**
Répondre en désignant le fichier et la ligne.

> Aucune question ne porte sur l'orchestration, le stockage distribué ou
> l'observabilité : ils ne font pas partie du programme évalué ici.

## Règles impératives — le non-respect rend l'élément non évaluable

1. Ne **jamais** contourner un CAPTCHA, un challenge, un blocage, une
   authentification ou une limitation explicite.
2. Ne collecter **aucune** donnée personnelle ou sensible, ni derrière un espace privé.
3. **Aucune action irréversible** : pas d'achat, pas de réservation, pas d'envoi de
   formulaire réel. Sur un panier de démonstration, on ne valide jamais la commande.
4. Ne versionner **aucun** secret : jeton, cookie de session, mot de passe, donnée
   personnelle.

En cas de refus de la cible : conserver la preuve (URL, heure, statut), prévenir le
formateur, obtenir une cible de secours, consigner le changement dans le rapport.
**Un diagnostic correct de blocage est un résultat, pas un échec — et il est valorisé.**

## Ordre de travail

### 1. Dès l'attribution de la cible

- [ ] Renseigner `[cible]` dans `config.toml`
- [ ] `python -m collecteur diagnostic --url <URL>` → relever les chiffres
- [ ] Lire le `robots.txt` **en entier** et conclure **pour son chemin**
- [ ] Ouvrir la même URL dans le navigateur, compter les objets dans le DOM
- [ ] **Chiffrer l'écart HTML brut ↔ DOM** — c'est le diagnostic, 4 points
- [ ] Copier `docs/fiche_descriptive_template.md` → `docs/fiche_descriptive.md` et le remplir
- [ ] Enregistrer `tests/fixtures/page_liste.html` et `page_detail.html`

### 2. Modèle et extraction

- [ ] Écrire la classe métier dans `modele.py` (hérite d'`ObjetCollecte`)
- [ ] Choisir la règle d'identifiant — **tient-elle si le site réorganise ses URL ?**
- [ ] Choisir l'ancrage des **deux** champs les plus importants, et noter tout de
      suite l'alternative écartée
- [ ] Implémenter `extraction.py`
- [ ] Vérifier qu'un ancrage retiré de la fixture lève bien `ChampObligatoireAbsent`

### 3. Vérification — sans réseau

- [ ] Renseigner `NOMBRE_ATTENDU` dans `test_extraction.py` et retirer le skip
- [ ] `pytest` passe, **débranché du réseau**
- [ ] Vérifier qu'un test échoue si l'on retire un objet de la fixture

### 4. Collecte et rapport

- [ ] Implémenter la boucle dans `cli.py::_collecte`
- [ ] Collecte limitée exécutée → relever `Compteurs.resume()` pour la rubrique 7
- [ ] **Les compteurs se raccordent** : vus = exportés + rejetés + doublons
- [ ] `samples/sample_output.json` produit, 5 à 10 objets
- [ ] Remplir la trame, rubrique par rubrique, **le dépôt ouvert à côté**
- [ ] Rédiger le résumé exécutif **en dernier**

### 5. Avant l'envoi

- [ ] **Au moins 5 commits personnels et significatifs** — un import final unique ne
      permet pas d'observer la démarche
- [ ] Dépôt **public**, lien testé en **navigation privée**
- [ ] Aucun fichier du formateur dans le dépôt (diffusion restreinte)
- [ ] Aucun secret, aucun `config.toml`, aucun état de session
- [ ] Test honnête : cloner son propre dépôt dans un autre dossier et suivre le
      README **à la lettre**, sans rien corriger de mémoire
- [ ] Noter le **hash complet** du commit évalué (pas les sept premiers caractères)
- [ ] Rapport nommé `NOM_Prenom_TP_Scraping.docx`, envoyé avec le lien cliquable

> Le dépôt est évalué **au hash inscrit dans le rapport**. Ce qui est poussé après
> n'est pas regardé.

### 6. Préparation de l'oral

- [ ] Message essentiel en **une** phrase, dite sans notes
- [ ] Un extrait de code choisi **difficile plutôt que confortable**
- [ ] Une panne dont on sait expliquer la **démarche** de diagnostic
- [ ] Sortie déjà produite + traces lisibles, en secours de la démonstration en direct
- [ ] Chronométrer une répétition complète

> « Trente démonstrations en direct depuis la même salle sur la même connexion
> échouent parfois. » Un incident n'est pas sanctionné ; l'incapacité à commenter
> une preuve préparée l'est.

## Les quatre règles de rédaction du rapport

1. **Une affirmation sans preuve ne compte pas.** « Le site est une SPA » est une
   opinion ; « la réponse HTTP contient 812 caractères de texte et aucun titre de
   produit, le DOM rendu en contient 14 300 » est une observation.
2. **Chiffrer.** Partout où un nombre peut remplacer un adjectif.
3. **Renvoyer au code.** Fichier, fonction, lignes.
4. **Ne pas bluffer.** « Non traité, faute de temps ; voici ce que j'aurais fait et
   pourquoi » vaut mieux qu'une case décrivant une fonctionnalité absente du dépôt.
   La contradiction entre la trame et le dépôt **est cherchée**, et elle se paie
   deux fois : sur la conception et sur les questions.
