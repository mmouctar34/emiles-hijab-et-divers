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

c = e.ctx(); p = e.page(c, edit=True)
load(p, hash='#gestion')
p.wait_for_timeout(300)
# ---- Ajout d'un produit
p.click('[data-adm=new]')
p.wait_for_selector('#editModal:not([hidden])')
check('éditeur ouvert (nouveau)', p.locator('#edTitle').inner_text()=='Ajouter un produit')
check('3 lots par défaut', p.locator('.ed-pack').count()==3)
# Enregistrer vide -> erreurs
p.click('[data-ed=save]')
check('erreurs nom + prix', p.locator('#edErr').is_visible() and 'nom' in p.locator('#edErr').inner_text().lower(), p.locator('#edErr').inner_text())
p.screenshot(path=S+'editor-errors.png')
# photo
p.set_input_files('#edFile', FIX+'photo-big.jpg')
p.wait_for_selector('#edImg', timeout=8000)
check('aperçu photo', p.evaluate("document.getElementById('edImg').naturalWidth>0"))
up = list(UPLOADS.values())[-1]
from PIL import Image
im = Image.open(io.BytesIO(up))
check('photo réduite (max 1400 px, JPEG)', max(im.size)<=1400 and im.format=='JPEG', (im.size, im.format, len(up)))
check('ratio conservé', abs(im.size[0]/im.size[1]-0.75)<0.01, im.size)
# nom + catégorie
p.fill('#ed-name', 'Gel douche coco 500 ml')
p.select_option('#ed-cat', 'corps')
check('rayons corps', p.locator('#ed-group option').count()==7, p.locator('#ed-group option').count())
p.select_option('#ed-group', 'Bain et douche')
p.select_option('#ed-sub', 'Gel et crème de douche')
p.fill('#ed-brand', 'Coco Fresh')
# prix à la pièce -> calcul
p.fill('#ed-up', '1 250')
p.click('[data-ed=calc]')
check('calcul lots', [p.input_value('#pk-p-%d'%i) for i in range(3)]==['3750','7500','15000'], [p.input_value('#pk-p-%d'%i) for i in range(3)])
check('info par pièce', '1 250' in p.locator('#pk-info-0').inner_text().replace(' ',' ').replace('\xa0',' '), p.locator('#pk-info-0').inner_text())
# un lot personnalisé
p.click('[data-ed=addpack][data-pre="-1"]')
p.fill('#pk-l-3','Carton de 24'); p.fill('#pk-q-3','24'); p.fill('#pk-p-3','27 000')
check('info carton', 'environ' not in p.locator('#pk-info-3').inner_text(), p.locator('#pk-info-3').inner_text())
p.fill('#ed-note','Livraison à Dakar offerte dès le carton')
p.fill('#ed-badge','Nouveau')
check('plus de case Nouveautés/Soldes dans l’éditeur', p.locator('[data-f^=tag-]').count()==0)
p.screenshot(path=S+'editor-filled.png')
p.click('[data-ed=save]')
p.wait_for_timeout(200)
check('éditeur fermé', p.locator('#editModal').is_hidden())
check('9 lignes', p.locator('.adm-row').count()==9)
first = p.locator('.adm-row').first
check('nouveau en premier', 'Gel douche coco' in first.inner_text() and 'Ajouté, non publié' in first.inner_text(), first.inner_text())
check('miniature visible (aperçu local)', p.evaluate("document.querySelector('.adm-row .adm-thumb img').naturalWidth>0"))
check('résumé brouillon', 'Brouillon non publié' in p.locator('#admSum').inner_text() and '1 ajouté' in p.locator('#admSum').inner_text(), p.locator('#admSum').inner_text())
check('brouillon enregistré localement', p.evaluate("JSON.parse(localStorage.getItem('emiles-draft-v1')).products.length")==9)
# La boutique (aperçu brouillon)
p.click('#ownerBar [data-adm=open]')
p.evaluate("document.querySelector('[data-page=home]') && document.querySelector('#page-gestion [data-page=home]').click()")
p.wait_for_timeout(300)
check('boutique: 9 produits', p.locator('.card').count()==9, p.locator('.card').count())
card = p.locator('.card').first
check('boutique: nom + prix', 'Gel douche coco 500 ml' in card.inner_text() and '3 750' in card.inner_text().replace(' ',' ').replace('\xa0',' '), card.inner_text())
check('boutique: badge + note', 'NOUVEAU' in card.inner_text() and 'Livraison à Dakar offerte dès le carton' in card.inner_text())
check('boutique: barre brouillon', p.locator('#draftBar').is_visible() and '1 modification non publiée' in p.locator('#draftTxt').inner_text(), p.locator('#draftTxt').inner_text())
check('boutique: image', p.evaluate("document.querySelector('.card img').naturalWidth>0"))
p.evaluate("window.scrollTo(0, document.querySelector('#boutique').offsetTop-80)")
p.wait_for_timeout(200)
p.screenshot(path=S+'shop-draft.png')
# Barre du haut : plus de Nouveautés/Soldes/Idées cadeaux, mais Marques, Conseils et les réseaux
check('barre du haut sans Nouveautés/Soldes/Idées', p.evaluate("document.querySelectorAll('.util [data-view]').length")==0)
check('barre du haut: Marques et Conseils', p.evaluate("document.querySelectorAll('.util [data-page=marques],.util [data-page=conseils]').length")==2)
check('barre du haut: réseaux', p.evaluate("document.querySelectorAll('#utilSoc a').length")>=1)
p.evaluate("document.querySelector('#menuBtn').click()")
p.wait_for_timeout(200)
check('menu mobile sans Nouveautés/Soldes/Idées', p.evaluate("document.querySelectorAll('#navDrawer [data-view=new],#navDrawer [data-view=promo],#navDrawer [data-view=gift]').length")==0)
p.evaluate("document.querySelector('#navDrawer [aria-label],#navDrawer .icon-btn') && document.querySelector('#navDrawer .icon-btn').click()")
p.wait_for_timeout(300)
# Catégorie corps -> 2 produits
p.evaluate("document.querySelector('#chips [data-cat=corps]').click()")
p.wait_for_timeout(200)
check('Corps: 2 produits', p.locator('.card').count()==2, p.locator('.card').count())
# panier avec le nouveau produit
p.evaluate("document.querySelector('.card [data-add]').click()")
check('panier: 1', p.locator('#cartCount').inner_text()=='1')
check('erreurs js', not p.errors, p.errors)
c.close()
e.close()
print('OK' if ok else 'ECHEC')
