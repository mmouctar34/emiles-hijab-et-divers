from harness import *
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out') + '/'
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures') + '/'
e = Env()
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra and not cond else ''))
    ok = ok and bool(cond)

# --- 1. Client sans window.claude
c = e.ctx(); p = e.page(c, noClaude=True)
load(p)
check('client: 8 produits', p.locator('.card').count() == 8, p.locator('.card').count())
check('client: pas de barre propriétaire', p.locator('#ownerBar').is_hidden())
check('client: images chargées', p.evaluate("Array.from(document.querySelectorAll('.card img')).every(i=>i.naturalWidth>0)"))
check('client: hero + tuiles chargés', p.evaluate("Array.from(document.querySelectorAll('.orb img,.tile-art img')).every(i=>i.naturalWidth>0)"))
load(p, hash='#gestion')
check('client: #gestion ignoré', p.locator('#page-gestion').is_hidden() and p.locator('#home').is_visible())
check('client: hash nettoyé', p.evaluate("location.hash")=='' , p.evaluate("location.hash"))
check('client: pas d’erreur JS', not p.errors, p.errors)
p.screenshot(path=S+'client.png')
c.close()

# --- 2. Visiteur connecté sans droit d'édition
c = e.ctx(); p = e.page(c, edit=False)
load(p)
check('lecteur: pas de barre', p.locator('#ownerBar').is_hidden())
check('lecteur: pas d’erreur JS', not p.errors, p.errors)
c.close()

# --- 3. Propriétaire
c = e.ctx(); p = e.page(c, edit=True)
load(p)
check('proprio: barre visible', p.locator('#ownerBar').is_visible())
p.click('#ownerBar [data-adm=open]')
p.wait_for_timeout(200)
check('proprio: page gestion', p.locator('#page-gestion').is_visible() and p.locator('#home').is_hidden())
check('proprio: 8 lignes', p.locator('.adm-row').count() == 8, p.locator('.adm-row').count())
check('proprio: hash #gestion', p.evaluate('location.hash')=='#gestion')
check('proprio: vignettes ok', p.evaluate("Array.from(document.querySelectorAll('.adm-thumb img')).every(i=>i.naturalWidth>0)"))
p.screenshot(path=S+'admin-desktop.png', full_page=True)
check('proprio: pas d’erreur JS', not p.errors, p.errors)
# deep link
load(p, hash='#gestion')
p.wait_for_timeout(300)
check('proprio: lien direct #gestion', p.locator('#page-gestion').is_visible())
c.close()
e.close()
print('OK' if ok else 'ECHEC')
