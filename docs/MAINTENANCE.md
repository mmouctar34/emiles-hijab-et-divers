# Notes de maintenance

Plateforme de publication : Claude Artifacts (capabilities déclarées : `artifact`, `assets`).

## Architecture
- La page est son propre enregistrement. Catalogue = `<script id="catalog-data">` (JSON). Gabarit complet = `<script id="tpl-src">` (base64).
- Le propriétaire (user.canEdit()) voit « Mode gestion » : ajout/modif/suppression de produits, photos via `assets.upload`,
  brouillon en localStorage, « Publier » = reconstruit la page (gabarit + catalogue) et appelle `artifact.publish(html)`.
- Sources : `src/page.html` (page), `src/admin.css|html|js` (espace de gestion), `data/assets.json` (ids des 8 photos stockées),
  `data/catalog.json` (catalogue de départ, rev 1), `build.py` (assemble).
- `python3 build.py [catalogue.json]` écrit dans `dist/` : `index.html` (contenu à publier), `full.html` (document complet), `template.html`.

## Règle d'or avant toute republication
Le propriétaire a pu publier de nouveaux produits depuis la page. Ne jamais publier avec `data/catalog.json` par défaut :
1. Lire la version en ligne et extraire le JSON de `<script id="catalog-data">` dans `live-catalog.json`.
2. `python3 build.py live-catalog.json`, puis publier `dist/index.html` (même artifact, sans changer les capabilities).
Si on change le catalogue soi-même, incrémenter `rev` (les brouillons du propriétaire deviennent « périmés » et il est averti).

## Tests (Playwright, window.claude simulé) : `tests/harness.py`, `tests/t1.py` à `t5.py`
Le document auto-publié doit être identique octet pour octet à `build.build(template, catalogue)` (test t3).
Squelette Artifact : `<!doctype html>…<body>` + "\n" + contenu + "\n</body></html>" (constantes SKEL_HEAD/SKEL_TAIL).

## Historique
- v10 : espace « Gestion des produits » (ajout, modification, photos, brouillon, publication).
- v11 : barre du haut réduite à Marques, Conseils et réseaux (Nouveautés, Soldes et Idées cadeaux retirés de la barre, du menu mobile et des cases de l'éditeur ; les vues et le champ `tags` existent toujours dans le code).
- v11 : bandeau « Maquette de démonstration, pas encore le site officiel d'Emile's Hijab & Divers » : la boutique est une proposition faite sans accord préalable du commerçant, à retirer s'il valide.
- Gestion : seuls les comptes ayant le droit de modification (menu Partager) voient « Mode gestion ». Pour une remise au commerçant, prévoir un hébergement dédié (domaine et accès administrateur).
- v12 : barre du haut sans Marques ni Conseils ; Facebook et Messenger retirés partout (barre, pied de page, données). Marques et Conseils restent dans le pied de page et le menu mobile.
- Version GitHub Pages (`python3 build.py --pages`) : index.html et _blob/ à la racine, bandeau de démonstration non fermable, noindex, gestion de démonstration (`src/pages-demo.js`, activée par `#gestion`, stockage dans le navigateur).
