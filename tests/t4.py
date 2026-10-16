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
def norm_sp(t): return t.replace(' ',' ').replace('\xa0',' ')

c = e.ctx(); p = e.page(c, edit=True)
load(p, hash='#gestion'); p.wait_for_timeout(300)

# --- validation
p.click('[data-adm=new]'); p.wait_for_selector('#editModal:not([hidden])')
p.fill('#pk-q-0','x'); 
p.click('[data-ed=save]')
err = p.locator('#edErr').inner_text()
check('val: nom requis', 'nom du produit' in err, err)
check('val: lot 1 prix manquant', 'Lot 1' in err and 'quantité' in err or 'prix' in err, err)
check('val: champ nom marqué invalide', p.get_attribute('#ed-name','aria-invalid')=='true')
check('val: erreurs visibles (bandeau pied)', p.locator('#edErr').is_visible())
# fix: name, all 3 prices, duplicate qty
p.fill('#ed-name','Test lots'); p.fill('#pk-q-0','3')
p.fill('#pk-p-0','1000'); p.fill('#pk-p-1','2000'); p.fill('#pk-p-2','4000')
p.fill('#pk-q-1','3')
p.click('[data-ed=save]')
err = p.locator('#edErr').inner_text()
check('val: quantités en double', 'même quantité' in err, err)
p.fill('#pk-q-1','6')
# remove all packs
for i in range(3): p.click('[data-ed=rmpack] >> nth=0')
check('lots retirés', p.locator('.ed-pack').count()==0)
p.click('[data-ed=save]')
check('val: au moins un lot', 'au moins un lot' in p.locator('#edErr').inner_text(), p.locator('#edErr').inner_text())
# preset chips re-add
p.click('[data-ed=addpack][data-pre="0"]'); p.click('[data-ed=addpack][data-pre="2"]')
check('chips: 2 lots, chips désactivés', p.locator('.ed-pack').count()==2 and p.locator('[data-ed=addpack][data-pre="0"]').is_disabled())
p.fill('#pk-p-0','900'); p.fill('#pk-p-1','3 600')
# unit change -> info text
p.select_option('#ed-unit','boîte')
check('unité boîte: info', 'la boîte' in norm_sp(p.locator('#pk-info-0').inner_text()) and 'boîtes' in p.locator('#pk-info-0').inner_text(), p.locator('#pk-info-0').inner_text())
p.select_option('#ed-unit','sachet')
check('unité sachet: info (le)', 'le sachet' in norm_sp(p.locator('#pk-info-0').inner_text()), p.locator('#pk-info-0').inner_text())
# flat category: cheveux
p.select_option('#ed-cat','cheveux')
check('flat: pas de rayon', p.locator('#ed-group').count()==0)
check('flat: types', p.locator('#ed-sub option').count()==13, p.locator('#ed-sub option').count())
p.select_option('#ed-sub','Masque')
# 'visage' coffret group has no items -> no sub select
p.select_option('#ed-cat','visage'); p.select_option('#ed-group','Coffret soin visage')
check('groupe sans types: pas de select type', p.locator('#ed-sub').count()==0)
p.select_option('#ed-cat','cheveux'); p.select_option('#ed-sub','Masque')
p.click('[data-ed=save]'); p.wait_for_timeout(200)
first = p.locator('.adm-row').first
check('ajouté (cheveux)', 'Test lots' in first.inner_text() and 'Cheveux · Masque' in first.inner_text(), first.inner_text())
d = p.evaluate("JSON.parse(localStorage.getItem('emiles-draft-v1')).products[0]")
check('données: pas de group pour cheveux', 'group' not in d and d['cat']=='cheveux' and d['sub']=='Masque' and d['unit']=='sachet', d)
check('données: lots triés', d['packs']==[['Les 3',3,900],['Douzaine',12,3600]], d['packs'])
check('données: pas de champs vides', all(v not in ('',None,False) for v in d.values()), d)
# product without photo shows placeholder in shop
p.evaluate("document.querySelector('#page-gestion [data-page=home]').click()"); p.wait_for_timeout(250)
check('sans photo: logo de remplacement', p.evaluate("document.querySelector('.card img').classList.contains('ph') && document.querySelector('.card img').naturalWidth>0"))

# --- publish failure modes
for code, expect in [('conflict','modifié ailleurs'),('not_writer','compte propriétaire'),('rate_limited','Patientez'),('too_large','volumineux'),('upstream_error','Réessayez'),('invalid_content','conservé')]:
    p.evaluate("window.__OPT.pubErr=%s" % json.dumps(code))
    p.click('#draftBar [data-adm=publish]'); p.wait_for_selector('#sheet:not([hidden])')
    p.click('#sheetAct .btn-primary'); p.wait_for_timeout(300)
    msg = p.locator('#sheetErr').inner_text()
    check('échec %s: message' % code, expect in msg, msg)
    check('échec %s: boutons réactivés + liste' % code, not p.locator('#sheetAct .btn-primary').is_disabled() and 'Ajouté' in p.locator('#sheetBody').inner_text())
    check('échec %s: brouillon gardé' % code, p.evaluate("!!localStorage.getItem('emiles-draft-v1')"))
    p.click('#sheetAct .btn >> nth=0'); p.wait_for_timeout(100)
check('aucune publication après échecs', len(e.published)==0)
p.evaluate("window.__OPT.pubErr=null")
p.click('#draftBar [data-adm=publish]'); p.wait_for_selector('#sheet:not([hidden])')
p.click('#sheetAct .btn-primary'); p.wait_for_timeout(500)
check('publication ok après erreurs', len(e.published)==1)
check('flag toast posé', p.evaluate("sessionStorage.getItem('emiles-published')")=='1')
# same tab "reload" with published doc -> toast
set_html(p, e.published[0]); p.wait_for_timeout(500)
check('même onglet: toast Publié', 'Publié' in p.locator('#toast').inner_text(), p.locator('#toast').inner_text())
check('flag consommé', p.evaluate("sessionStorage.getItem('emiles-published')") is None)
check('brouillon effacé après publication', p.evaluate("localStorage.getItem('emiles-draft-v1')") is None)

# --- upload failure modes
p.evaluate("document.querySelector('#ownerBar [data-adm=open]').click()"); p.wait_for_timeout(200)
p.click('[data-adm=new]'); p.wait_for_selector('#editModal:not([hidden])')
for code, expect in [('quota_or_state','plein'),('rate_limited','Patientez'),('not_granted','compte propriétaire'),('upstream_error','Réessayez')]:
    p.evaluate("window.__OPT.upErr=%s" % json.dumps(code))
    p.set_input_files('#edFile', FIX+'photo-big.jpg'); p.wait_for_timeout(700)
    msg = p.locator('#edPhoto .err').inner_text()
    check('photo échec %s' % code, expect in msg, msg)
    check('photo échec %s: bouton réactivé' % code, not p.locator('[data-ed=pick]').is_disabled())
p.evaluate("window.__OPT.upErr=null")
# bad file (not an image)
FAKE = os.path.join(__import__('tempfile').gettempdir(), '_emiles_fake.jpg')
open(FAKE,'wb').write(b'not an image at all')
p.set_input_files('#edFile',FAKE); p.wait_for_timeout(500)
check('fichier illisible', 'ne peut pas être lue' in p.locator('#edPhoto .err').inner_text(), p.locator('#edPhoto .err').inner_text())
# good upload then remove photo, slider
p.set_input_files('#edFile', FIX+'photo-big.jpg'); p.wait_for_selector('#edImg')
check('erreur effacée après succès', p.locator('#edPhoto .err').count()==0)
p.evaluate("(()=>{const r=document.getElementById('ed-pos');r.value=20;r.dispatchEvent(new Event('input',{bubbles:true}))})()")
check('cadrage: aperçu', 'center 20%' in p.evaluate("document.getElementById('edImg').style.objectPosition") or '20%' in p.evaluate("document.getElementById('edImg').style.objectPosition"))
p.click('[data-ed=rmphoto]')
check('photo retirée', p.locator('#edImg').count()==0 and p.locator('.ed-noimg').is_visible())
p.click('.ed-head [data-ed=cancel]'); p.wait_for_selector('#sheet:not([hidden])'); p.click('#sheetAct .btn-danger')

# --- stale draft
p.evaluate("""localStorage.setItem('emiles-draft-v1', JSON.stringify({base:1,t:1,products:JSON.parse(document.getElementById('catalog-data').textContent).products.slice(1)}))""")
p.reload(); p.wait_for_timeout(500)
check('brouillon périmé: avertissement', 'modifié depuis le début' in p.locator('#admSum').inner_text(), p.locator('#admSum').inner_text())
check('brouillon périmé: bouton repartir', 'Repartir de la version publiée' in p.locator('#admSum').inner_text())
p.click('#admSum [data-adm=discard]'); p.wait_for_selector('#sheet:not([hidden])'); p.click('#sheetAct .btn-danger'); p.wait_for_timeout(200)
check('repartir: brouillon effacé', p.evaluate("localStorage.getItem('emiles-draft-v1')") is None and 'Le site affiche exactement' in p.locator('#admSum').inner_text())
check('erreurs js', not p.errors, p.errors)
c.close()

# --- capability absences
c = e.ctx(); p = e.page(c, edit=True, noArtifact=True)
load(p, hash='#gestion'); p.wait_for_timeout(300)
check('sans capability artifact: pas de mode gestion', p.locator('#ownerBar').is_hidden() and p.locator('#page-gestion').is_hidden())
c.close()
c = e.ctx(); p = e.page(c, edit=True, noAssets=True)
load(p, hash='#gestion'); p.wait_for_timeout(300)
p.click('[data-adm=new]'); p.wait_for_selector('#editModal:not([hidden])')
p.set_input_files('#edFile', FIX+'photo-big.jpg'); p.wait_for_timeout(600)
check('sans assets: message clair', 'pas disponible' in p.locator('#edPhoto .err').inner_text(), p.locator('#edPhoto .err').inner_text())
p.fill('#ed-name','Sans photo'); p.fill('#pk-p-0','100'); p.fill('#pk-p-1','200'); p.fill('#pk-p-2','400')
p.click('[data-ed=save]'); p.wait_for_timeout(200)
check('sans assets: ajout possible sans photo', 'Sans photo' in p.locator('.adm-row').first.inner_text())
check('erreurs js (sans assets)', not p.errors, p.errors)
c.close()
e.close()
print('OK' if ok else 'ECHEC')
