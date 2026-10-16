"""Version GitHub Pages : boutique pour les clients + gestion de démonstration (adresse ...#gestion).
Prérequis : python3 build.py --pages"""
import os, re, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'tests', 'fixtures') + '/'
S = os.path.join(ROOT, 'tests', 'out') + '/'
os.makedirs(S, exist_ok=True)
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra and not cond else ''))
    ok = ok and bool(cond)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]

def newpage(b, mobile=False):
    c = b.new_context(viewport={'width': 390 if mobile else 1280, 'height': 844 if mobile else 900},
                      is_mobile=mobile, has_touch=mobile)
    c.route(re.compile(r'https://fonts\.(googleapis|gstatic)\.com/.*'), lambda r: r.abort())
    p = c.new_page(); p.errors = []
    p.on('pageerror', lambda e: p.errors.append(str(e)))
    return c, p

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # 1. client
    c, p = newpage(b)
    p.goto(URL); p.wait_for_timeout(500)
    check('client: 8 produits', p.locator('.card').count() == 8, p.locator('.card').count())
    check('client: aucune barre de gestion', p.locator('#ownerBar').is_hidden())
    check('client: pas de bouton de réinitialisation', p.locator('#demoReset').count() == 0)
    check('client: pas d’erreur JS', not p.errors, p.errors)
    c.close()
    # 2. gestion de démonstration
    c, p = newpage(b)
    p.goto(URL + '#gestion'); p.wait_for_timeout(700)
    check('gestion: barre visible', p.locator('#ownerBar').is_visible())
    check('gestion: texte de démonstration', 'Démonstration' in p.locator('.owner-msg').inner_text(), p.locator('.owner-msg').inner_text())
    check('gestion: page ouverte', p.locator('#page-gestion').is_visible() and p.locator('.adm-row').count() == 8, p.locator('.adm-row').count())
    check('gestion: note de démonstration', p.locator('.demo-note').is_visible())
    p.screenshot(path=S + 'pages-gestion.png')
    p.click('[data-adm=new]'); p.wait_for_selector('#editModal:not([hidden])')
    p.set_input_files('#edFile', FIX + 'photo-big.jpg'); p.wait_for_selector('#edImg', timeout=8000)
    check('gestion: aperçu de la photo', p.evaluate("document.getElementById('edImg').naturalWidth>0"))
    p.fill('#ed-name', 'Gel douche coco 500 ml')
    p.select_option('#ed-cat', 'corps')
    p.select_option('#ed-group', 'Bain et douche'); p.select_option('#ed-sub', 'Gel et crème de douche')
    p.fill('#ed-up', '1 250'); p.click('[data-ed=calc]')
    p.click('[data-ed=save]'); p.wait_for_timeout(300)
    check('gestion: 9 lignes (brouillon)', p.locator('.adm-row').count() == 9, p.locator('.adm-row').count())
    p.click('#ownerPub'); p.wait_for_selector('#sheet:not([hidden])')
    p.screenshot(path=S + 'pages-publier.png')
    p.click('#sheetAct .btn-primary'); p.wait_for_timeout(2200)
    check('publié: la page s’est rechargée avec 9 produits', p.locator('.adm-row').count() == 9 or p.locator('.card').count() == 9, (p.locator('.adm-row').count(), p.locator('.card').count()))
    check('publié: toast', 'Publié' in p.locator('#toast').inner_text(), p.locator('#toast').inner_text())
    p.evaluate("document.querySelector('[data-page=home]').click()"); p.wait_for_timeout(400)
    p.evaluate("document.querySelector('#boutique').scrollIntoView()"); p.wait_for_timeout(400)
    check('boutique: 9 cartes', p.locator('.card').count() == 9, p.locator('.card').count())
    check('boutique: photo du nouveau produit', p.evaluate("[...document.querySelectorAll('.card')].some(c=>c.innerText.includes('Gel douche coco')&&c.querySelector('img').naturalWidth>0)"))
    check('boutique: prix du nouveau produit', p.evaluate("[...document.querySelectorAll('.card')].some(c=>c.innerText.includes('Gel douche coco')&&/3\\s?750/.test(c.innerText))"))
    p.screenshot(path=S + 'pages-boutique-9.png')
    # persistance : rechargement de la même page
    p.reload(); p.wait_for_timeout(600)
    check('persistance: toujours 9 produits après rechargement', p.locator('.card').count() == 9, p.locator('.card').count())
    check('persistance: photo toujours là', p.evaluate("[...document.querySelectorAll('.card')].some(c=>c.innerText.includes('Gel douche coco')&&c.querySelector('img').naturalWidth>0)"))
    check('gestion: pas d’erreur JS', not p.errors, p.errors)
    # 3. un autre appareil ne voit rien
    c2, p2 = newpage(b)
    p2.goto(URL); p2.wait_for_timeout(500)
    check('autre appareil: 8 produits', p2.locator('.card').count() == 8, p2.locator('.card').count())
    c2.close()
    # 4. remise à zéro
    p.goto(URL + '#gestion'); p.wait_for_timeout(600)
    p.click('#demoReset'); check('remise à zéro: demande de confirmation', 'confirmer' in p.locator('#demoReset').inner_text())
    p.click('#demoReset'); p.wait_for_timeout(900)
    check('remise à zéro: 8 produits', p.locator('.adm-row').count() == 8 or p.locator('.card').count() == 8, (p.locator('.adm-row').count(), p.locator('.card').count()))
    check('remise à zéro: stockage vidé', p.evaluate("localStorage.getItem('emiles-demo-catalog')") is None)
    c.close()
    # 5. téléphone
    c, p = newpage(b, mobile=True)
    p.goto(URL + '#gestion'); p.wait_for_timeout(700)
    check('mobile: gestion sans débordement', p.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    p.screenshot(path=S + 'pages-gestion-mobile.png')
    c.close()
    b.close()
srv.shutdown()
print('OK' if ok else 'ECHEC')
