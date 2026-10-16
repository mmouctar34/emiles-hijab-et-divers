# Emile's Hijab & Divers

Prototype de boutique en ligne, en gros et au détail, réalisé pour un commerçant de Rufisque (Sénégal) dans le cadre d'une prospection.

> **Statut : prototype de démonstration.** Ce n'est pas le site officiel de la boutique. Le nom, le logo, les photos et les coordonnées appartiennent à leurs propriétaires et ne servent ici qu'à la maquette.

## Le contexte

Le commerce vend des foulards, des cosmétiques, des parfums et des accessoires, au détail et en gros, et prend ses commandes sur WhatsApp. Le prototype montre à quoi pourrait ressembler sa boutique en ligne, avec les mêmes habitudes de travail : prix en FCFA, vente par lots (les 3, la douzaine, le carton) et commande confirmée par un conseiller.

## Ce que fait le site

**Pour le client**
- Page d'accueil avec en-tête à menus déroulants par catégorie : Maquillage, Soin visage, Cheveux, Corps et bain, Parfum, Mode.
- Boutique avec filtres, tri, recherche, favoris, et pages « Marques » et « Conseils ».
- Chaque produit se vend par lots. Le prix du lot et le prix à la pièce sont affichés.
- Panier : la commande part sur WhatsApp, vers le conseiller que le client choisit parmi six.
- Infos pratiques : horaires, adresse, service réclamations, Instagram et TikTok.
- Adapté au téléphone, avec mode sombre et navigation au clavier.

**Pour le propriétaire (espace « Gestion des produits »)**
- Ajouter un produit avec sa photo, son nom, sa catégorie et ses prix par lot, depuis le téléphone.
- Modifier un prix, masquer un produit épuisé, le déplacer ou le supprimer (avec « Rétablir »).
- Les changements restent un brouillon, visible du seul propriétaire, jusqu'à « Publier ».
- Seules les personnes qui ont le droit de modification voient cet espace.

## Comment c'est construit

Une seule page HTML, sans framework ni dépendance : HTML, CSS et JavaScript écrits à la main. Polices : Bodoni Moda, Hanken Grotesk et Great Vibes (Google Fonts).

La page est **sa propre base de données** :

- le catalogue est un bloc JSON dans la page (`<script id="catalog-data">`) ;
- le gabarit complet de la page est embarqué en base64 (`<script id="tpl-src">`) ;
- « Publier » regénère le document complet (gabarit + catalogue modifié) et le republie par l'API `artifact.publish` de la plateforme Claude Artifacts ;
- les photos envoyées passent par `assets.upload` de la même plateforme.

`build.py` assemble la page à partir de `src/` et de `data/`. Les tests vérifient que le document que la page publie elle-même est identique, octet pour octet, à celui que produit `build.py`.

```
build.py            assemble la page (résultat dans dist/)
src/page.html       la boutique (HTML, CSS, JS)
src/admin.*         l'espace de gestion (CSS, HTML, JS)
data/catalog.json   catalogue de départ : 8 produits, prix en FCFA
data/assets.json    correspondance photo -> identifiant sur la plateforme
assets/             logo et photos d'origine des produits
tests/              tests Playwright (window.claude simulé)
docs/MAINTENANCE.md notes de maintenance
index.html          la boutique pour GitHub Pages (générée par build.py --pages)
_blob/              les photos pour GitHub Pages (générées)
```

## Utiliser le projet

Il faut Python 3.

```bash
python3 build.py              # écrit dist/index.html, dist/full.html, dist/template.html
python3 build.py --pages      # écrit en plus la version GitHub Pages (index.html et _blob/ à la racine)
```

- `dist/index.html` est le contenu à publier sur la plateforme Claude Artifacts. Les capacités `artifact` et `assets` doivent être déclarées à la publication.
- `dist/full.html` s'ouvre dans un navigateur pour un aperçu de la mise en page. Hors de la plateforme, les photos ne s'affichent pas (elles sont servies depuis le stockage de l'artifact, sous `/_blob/<id>`), et le logo les remplace. L'espace de gestion reste caché.

### Version en ligne (GitHub Pages)

`python3 build.py --pages` produit à la racine la même boutique, prête pour un hébergement ordinaire : les photos sont lues dans `_blob/`, le bandeau « Maquette de démonstration » ne peut pas être fermé et la page n'est pas référencée par les moteurs de recherche (`noindex`). L'espace de gestion n'y apparaît pas, il dépend de la plateforme Claude Artifacts.

Pour la publier : Settings, Pages, Source « Deploy from a branch », branche `main`, dossier `/ (root)`.
Adresse : https://mmouctar34.github.io/emiles-hijab-et-divers/

### Tests

```bash
pip install playwright && playwright install chromium
for t in tests/t?.py; do python3 $t; done
```

Les tests simulent la plateforme : propriétaire et visiteur, ajout de produit avec photo, modification, brouillon, publication, erreurs, affichage mobile et mode sombre.

## Limites connues

- La page de gestion dépend de la plateforme Claude Artifacts (droits de modification, publication, stockage des photos). Elle n'a été testée qu'avec une simulation de ces appels.
- Pour un vrai site avec nom de domaine, l'espace de gestion serait à refaire : un serveur avec connexion protégée, et un stockage pour le catalogue et les photos. L'apparence et le catalogue se reprennent tels quels.
- Les catégories sont fixes. Les rubriques Nouveautés, Soldes et Idées cadeaux ont été retirées de la navigation ; leur code est conservé dans la page.
- Le lien de la chaîne WhatsApp, la page Facebook et les prix de détail ne sont pas renseignés.
- Les produits, prix et numéros WhatsApp viennent de captures fournies pour la maquette. Ils doivent être validés par le commerçant avant tout usage réel.
