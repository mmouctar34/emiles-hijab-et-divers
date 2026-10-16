#!/usr/bin/env python3
"""Assemble la boutique.
  python3 build.py [catalogue.json] [--pages]     (catalogue par défaut : data/catalog.json)
Écrit dans dist/ :
  index.html    = contenu de la page (commence par <title>), tel qu'on le publie sur la plateforme
  full.html     = document complet tel que la page se republie elle-même (sert aux tests et à l'aperçu local)
  template.html = gabarit (avec le marqueur de bloc), sert aux tests
Avec --pages, écrit aussi la version pour GitHub Pages à la racine du dépôt (index.html + photos dans _blob/).
IMPORTANT avant toute republication : partir du catalogue PUBLIÉ (bloc catalog-data de la version en ligne),
pas de data/catalog.json, sinon on écrase ce que le propriétaire a publié depuis."""
import base64, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))

KEYS = ['id', 'name', 'cat', 'group', 'sub', 'brand', 'img', 'alt', 'pos', 'unit', 'note', 'badge', 'tags', 'hide', 'packs']
MARK = '%' + '%BLOCKS%' + '%'
SKEL_HEAD = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
             'html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}'
             'img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>')
SKEL_TAIL = '</body></html>'
LOGO = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(HERE, 'assets', 'logo-sphere.png'), 'rb').read()).decode('ascii')


def canon(p):
    o = {}
    for k in KEYS:
        v = p.get(k)
        if v in (None, '', False):
            continue
        if k == 'tags' and not v:
            continue
        o[k] = v
    return o


def json_safe(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return s.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def sub(s, token, text):
    n = s.count(token)
    if n != 1:
        sys.exit('jeton %r présent %d fois' % (token, n))
    return s.replace(token, text)  # texte inséré tel quel


def make_template():
    s = open(os.path.join(HERE, 'src', 'page.html'), encoding='utf-8').read()
    css = open(os.path.join(HERE, 'src', 'admin.css'), encoding='utf-8').read()
    html = open(os.path.join(HERE, 'src', 'admin.html'), encoding='utf-8').read()
    js = open(os.path.join(HERE, 'src', 'admin.js'), encoding='utf-8').read()
    m = re.match(r'@@BAR\n(.*?)\n@@PAGE\n(.*)\Z', html, re.S)
    bar, page = m.group(1), m.group(2)
    s = sub(s, '/*__ADMIN_CSS__*/', css.rstrip('\n'))
    s = sub(s, '__ADMIN_BAR__', bar)
    s = sub(s, '__ADMIN_PAGE__', page.rstrip('\n'))
    s = sub(s, '/*__ADMIN_JS__*/', js.rstrip('\n'))
    s = s.replace('__LOGO_SPHERE__', LOGO)
    assets = json.load(open(os.path.join(HERE, 'data', 'assets.json')))
    def asset(m):
        return assets[m.group(1)]
    s = re.sub(r'__A:([a-z-]+)__', asset, s)
    for bad in ('__A:', '__ADMIN', '__LOGO'):
        if bad in s:
            sys.exit('jeton restant : ' + bad)
    if s.count(MARK) != 1:
        sys.exit('marqueur de bloc présent %d fois' % s.count(MARK))
    if not s.startswith('<title>'):
        sys.exit('le gabarit doit commencer par <title>')
    return s


def blocks(P, cat):
    b64 = base64.b64encode(P.encode('utf-8')).decode('ascii')
    return ('<script type="application/json" id="catalog-data">' + json_safe(cat) + '</script>\n'
            '<script type="text/plain" id="tpl-src">' + b64 + '</script>')


def build(P, cat):
    content = P.replace(MARK, blocks(P, cat), 1)
    return content, SKEL_HEAD + '\n' + content + '\n' + SKEL_TAIL


def pages_version(full, assets):
    """Version pour un hébergement ordinaire (GitHub Pages) : même page, trois adaptations.
    1. les photos sont lues dans _blob/<id>.jpg à côté de la page (au lieu de /_blob/<id> de la plateforme) ;
    2. le bandeau « Maquette de démonstration » ne peut plus être fermé ;
    3. la page n'est pas référencée par les moteurs de recherche."""
    n = len(re.findall(r'/_blob/[0-9a-f]{32}', full))
    full = re.sub(r'/_blob/([0-9a-f]{32})', r'_blob/\1.jpg', full)
    old = "return '/_blob/'+v;"
    if full.count(old) != 1:
        sys.exit('imgSrc introuvable')
    full = full.replace(old, "return '_blob/'+v+'.jpg';")
    if '/_blob/' in full:
        sys.exit('lien /_blob/ restant')
    css_old = '.preview-in button{border:0;background:none;width:32px;height:32px;border-radius:50%;flex:none;font-size:16px}'
    if full.count(css_old) != 1:
        sys.exit('règle du bandeau introuvable')
    full = full.replace(css_old, css_old + '\n#noteClose{display:none}')
    head_old = '<meta charset=utf8>'
    if not full.startswith('<!doctype html><html><head>' + head_old):
        sys.exit('en-tête introuvable')
    # seulement la première occurrence : le même texte existe aussi dans le script de publication
    full = full.replace(head_old, head_old + '<meta name="robots" content="noindex,nofollow">', 1)
    return full, n


def write_pages(full):
    assets = json.load(open(os.path.join(HERE, 'data', 'assets.json')))
    out, n = pages_version(full, assets)
    d = HERE
    blob = os.path.join(d, '_blob')
    if os.path.isdir(blob):
        shutil.rmtree(blob)
    os.makedirs(blob)
    for name, bid in assets.items():
        shutil.copy(os.path.join(HERE, 'assets', 'photos', name + '.jpg'), os.path.join(blob, bid + '.jpg'))
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    open(os.path.join(d, '.nojekyll'), 'w').write('')
    print('pages : index.html', len(out), 'octets,', n, 'liens photo,', len(assets), 'photos copiées')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(HERE, 'data', 'catalog.json')
    cat = json.load(open(path, encoding='utf-8'))
    cat['products'] = [canon(p) for p in cat['products']]
    P = make_template()
    content, full = build(P, cat)
    out = os.path.join(HERE, 'dist')
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'template.html'), 'w', encoding='utf-8').write(P)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(content)
    open(os.path.join(out, 'full.html'), 'w', encoding='utf-8').write(full)
    print('gabarit', len(P), 'contenu', len(content), 'complet', len(full), 'rev', cat.get('rev'), 'produits', len(cat['products']))
    if '--pages' in sys.argv:
        write_pages(full)
