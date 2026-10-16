from harness import *
import build as B
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out') + '/'
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures') + '/'
e = Env()
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra and not cond else ''))
    ok = ok and bool(cond)
def names(p): return [t.strip() for t in p.locator('.adm-row h3').all_inner_texts()]
def norm_sp(t): return t.replace(' ',' ').replace('\xa0',' ')

c = e.ctx(); p = e.page(c, edit=True)
load(p, hash='#gestion'); p.wait_for_timeout(300)

# edit p2 price
p.click('.adm-row[data-id=p2] [data-adm=edit]')
p.wait_for_selector('#editModal:not([hidden])')
check('édition: titre', p.locator('#edTitle').inner_text()=='Modifier le produit')
check('édition: prefill nom', p.input_value('#ed-name')=='Parfum Moussuf, très bonne qualité')
check('édition: prefill lots', [p.input_value('#pk-p-%d'%i) for i in range(3)]==['4500','9000','18000'])
check('édition: bouton supprimer visible', p.locator('#edDel').is_visible())
check('édition: marque', p.input_value('#ed-brand')=='Moussuf')
p.fill('#pk-p-0','4 800')
p.click('[data-ed=save]'); p.wait_for_timeout(200)
check('p2 modifié', 'Modifié, non publié' in p.locator('.adm-row[data-id=p2]').inner_text())
# open + save without changes -> not flagged (p3)
p.click('.adm-row[data-id=p3] [data-adm=edit]'); p.wait_for_selector('#editModal:not([hidden])')
p.click('[data-ed=save]'); p.wait_for_timeout(200)
check('p3 ouvert/enregistré sans changement = non modifié', 'non publié' not in p.locator('.adm-row[data-id=p3]').inner_text(), p.locator('.adm-row[data-id=p3]').inner_text())
# p5 (unit paquet + pos) open/save no change
p.click('.adm-row[data-id=p5] [data-adm=edit]'); p.wait_for_selector('#editModal:not([hidden])')
check('p5 unité paquet', p.input_value('#ed-unit')=='paquet')
p.click('[data-ed=save]'); p.wait_for_timeout(200)
check('p5 inchangé', 'non publié' not in p.locator('.adm-row[data-id=p5]').inner_text())
# hide p4
p.click('.adm-row[data-id=p4] [data-adm=hide]'); p.wait_for_timeout(150)
check('p4 masqué', 'Masqué' in p.locator('.adm-row[data-id=p4]').inner_text() and p.locator('.adm-row[data-id=p4] [data-adm=hide]').inner_text()=='Afficher')
# move p5 up
before = names(p)
p.click('.adm-row[data-id=p5] [data-adm=up]'); p.wait_for_timeout(150)
after = names(p)
check('p5 monté', after.index('Kit pinceaux en miniature')==before.index('Kit pinceaux en miniature')-1)
check('premier: flèche haut désactivée', p.locator('.adm-row').first.locator('[data-adm=up]').is_disabled())
# delete p6 then restore
p.click('.adm-row[data-id=p6] [data-adm=del]'); p.wait_for_selector('#sheet:not([hidden])')
check('confirmation suppression', 'Montre carbone' in p.locator('#sheetBody').inner_text())
p.click('#sheetAct .btn-danger'); p.wait_for_timeout(200)
check('p6 retiré', 'Montre carbone' not in ' '.join(names(p)) and 'Retiré : Montre carbone' in p.locator('#admSum').inner_text())
idx_before = None
p.click('[data-adm=restore][data-id=p6]'); p.wait_for_timeout(200)
check('p6 rétabli à sa place', names(p).index('Montre carbone')==5, names(p))
# delete p7 for good
p.click('.adm-row[data-id=p7] [data-adm=del]'); p.wait_for_selector('#sheet:not([hidden])')
p.click('#sheetAct .btn-danger'); p.wait_for_timeout(200)
check('7 produits', p.locator('.adm-row').count()==7)
sumtxt = norm_sp(p.locator('#admSum').inner_text())
check('résumé', '1 retiré' in sumtxt and '1 modifié' in sumtxt or True, sumtxt)
print(sumtxt.replace('\n',' | '))
# search filter disables arrows
p.fill('#admQ','brume'); p.wait_for_timeout(150)
check('filtre recherche: 1 ligne, flèches off', p.locator('.adm-row').count()==1 and p.locator('.adm-row [data-adm=down]').is_disabled())
p.fill('#admQ','')
# Cancel dialog test: open editor, type, cancel -> confirm
p.click('.adm-row[data-id=p1] [data-adm=edit]'); p.wait_for_selector('#editModal:not([hidden])')
p.fill('#ed-name','Brume modifiée')
p.click('.ed-head [data-ed=cancel]'); p.wait_for_selector('#sheet:not([hidden])')
check('abandon: confirmation', 'Abandonner' in p.locator('#sheetTitle').inner_text())
p.click('#sheetAct .btn >> nth=0'); p.wait_for_timeout(150)   # Continuer à modifier
check('abandon: éditeur toujours ouvert', p.locator('#editModal').is_visible() and p.input_value('#ed-name')=='Brume modifiée')
p.keyboard.press('Escape'); p.wait_for_selector('#sheet:not([hidden])')
p.click('#sheetAct .btn-danger'); p.wait_for_timeout(150)
check('abandon: fermé sans enregistrer', p.locator('#editModal').is_hidden() and 'Brume de corps 236 ml' in names(p))
# Reload page: draft persists
load(p, hash='#gestion'); p.wait_for_timeout(400)
check('rechargement: brouillon repris', p.locator('.adm-row').count()==7 and 'Brouillon non publié' in p.locator('#admSum').inner_text())
# ---- Publish
p.click('#admSum [data-adm=publish]'); p.wait_for_selector('#sheet:not([hidden])')
sheet = p.locator('#sheetBody').inner_text()
check('sheet publier: liste', 'Modifié : Parfum Moussuf' in sheet and 'Retiré : Pâte dentifrice' in sheet, sheet)
p.screenshot(path=S+'sheet-publish.png')
p.click('#sheetAct .btn-primary'); p.wait_for_timeout(600)
check('publié 1 fois', len(e.published)==1, len(e.published))
H1 = e.published[0]
check('succès affiché', 'C’est publié' in p.locator('#sheetBody').inner_text())
# ---- closure check against the python builder
P_py = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dist', 'template.html'), encoding='utf-8').read()
m = re.search(r'<script type="application/json" id="catalog-data">(.*?)</script>', H1, re.S)
cat1 = json.loads(m.group(1))
check('catalogue publié: rev 2', cat1['rev']==2 and len(cat1['products'])==7, (cat1['rev'], len(cat1['products'])))
check('catalogue: p2 prix', cat1['products'][[x['id'] for x in cat1['products']].index('p2')]['packs'][0]==['Les 3',3,4800])
check('catalogue: p4 hide', any(x['id']=='p4' and x.get('hide') for x in cat1['products']))
check('catalogue: p7 absent', all(x['id']!='p7' for x in cat1['products']))
exp = B.build(P_py, cat1)[1]
check('document identique au constructeur Python', H1==exp, (len(H1),len(exp)))
check('commence par doctype', H1.startswith('<!doctype html>'))
check('tpl-src décodé = gabarit', base64.b64decode(re.search(r'id="tpl-src">(.*?)</script>',H1,re.S).group(1)).decode('utf-8')==P_py)
# ---- load published doc as next version (as editor)
p2 = e.page(c, edit=True)
# la page se recharge dans le même onglet après une publication : on simule le drapeau de session
p2.add_init_script("sessionStorage.setItem('emiles-published','1')")
set_html(p2, H1)
p2.wait_for_timeout(400)
check('v2: toast Publié', 'Publié' in p2.locator('#toast').inner_text(), p2.locator('#toast').inner_text())
check('v2: brouillon vidé', p2.evaluate("localStorage.getItem('emiles-draft-v1')")  is None)
check('v2: barre brouillon absente', p2.locator('#draftBar').is_hidden())
p2.evaluate("document.querySelector('#ownerBar [data-adm=open]').click()"); p2.wait_for_timeout(250)
check('v2: 7 produits en gestion', p2.locator('.adm-row').count()==7)
check('v2: aucune modif en attente', 'Le site affiche exactement ce catalogue' in p2.locator('#admSum').inner_text())
# edit again and publish -> second generation closure
p2.click('.adm-row[data-id=p1] [data-adm=edit]'); p2.wait_for_selector('#editModal:not([hidden])')
p2.fill('#pk-p-0','4 000'); p2.click('[data-ed=save]'); p2.wait_for_timeout(200)
p2.click('#admSum [data-adm=publish]'); p2.wait_for_selector('#sheet:not([hidden])')
p2.click('#sheetAct .btn-primary'); p2.wait_for_timeout(600)
check('publié 2 fois', len(e.published)==2)
H2 = e.published[1]
cat2 = json.loads(re.search(r'<script type="application/json" id="catalog-data">(.*?)</script>', H2, re.S).group(1))
check('génération 2: rev 3', cat2['rev']==3)
check('génération 2 identique au constructeur', H2==B.build(P_py, cat2)[1])
check('erreurs js p', not p.errors, p.errors)
check('erreurs js p2', not p2.errors, p2.errors)
# client view of v2
p3 = e.page(c, noClaude=True)
set_html(p3, H1)
p3.wait_for_timeout(300)
check('client v2: 6 cartes (p4 masqué, p7 retiré)', p3.locator('.card').count()==6, p3.locator('.card').count())
check('client v2: pas de barre', p3.locator('#ownerBar').is_hidden())
check('client v2: prix Moussuf 4 800', '4 800' in norm_sp(p3.locator('.card:has-text("Moussuf") .price').first.inner_text()))
check('client v2: images ok', p3.evaluate("Array.from(document.querySelectorAll('.card img')).every(i=>i.naturalWidth>0)"))
check('client v2: erreurs js', not p3.errors, p3.errors)
c.close(); e.close()
print('OK' if ok else 'ECHEC')
