#!/usr/bin/env python3
"""Assemble la boutique.
  python3 build.py [catalogue.json]     (par défaut data/catalog.json)
Écrit dans dist/ :
  index.html    = contenu de la page (commence par <title>), tel qu'on le publie sur la plateforme
  full.html     = document complet tel que la page se republie elle-même (sert aux tests et à l'aperçu local)
  template.html = gabarit (avec le marqueur de bloc), sert aux tests
IMPORTANT avant toute republication : partir du catalogue PUBLIÉ (bloc catalog-data de la version en ligne),
pas de data/catalog.json, sinon on écrase ce que le propriétaire a publié depuis."""
import base64, json, os, re, sys

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


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'data', 'catalog.json')
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
