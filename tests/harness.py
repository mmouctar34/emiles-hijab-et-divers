import json, base64, sys, os, re, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = json.load(open(ROOT + '/data/assets.json'))
ID2FILE = {v: ROOT + '/assets/photos/' + k + '.jpg' for k, v in ASSETS.items()}
UPLOADS = {}   # id -> bytes (uploads captured from the mock)

INIT = r"""
(function(){
  var OPT = %s;
  window.__OPT = OPT;
  if (OPT.noClaude) return;
  window.claude = { use: async function(name){
    if (name === 'user') return { canEdit: async function(){ return OPT.edit }, isOwner: async function(){ return OPT.edit }, can: async function(){ return OPT.edit } };
    if (!OPT.edit) return null;
    if (name === 'artifact') {
      if (OPT.noArtifact) return null;
      return { publish: async function(html){
        if (window.__OPT.pubErr) { throw { code: window.__OPT.pubErr, message: 'x' } }
        await window.__capHtml(html);
        return { version: 'v-test' };
      } };
    }
    if (name === 'assets') {
      if (OPT.noAssets) return null;
      return { upload: async function(blob, o){
        if (window.__OPT.upErr) { throw { code: window.__OPT.upErr, message: 'x' } }
        var buf = new Uint8Array(await blob.arrayBuffer()), s = '';
        for (var i = 0; i < buf.length; i += 8192) s += String.fromCharCode.apply(null, buf.subarray(i, i + 8192));
        var id = await window.__capUpload(btoa(s), blob.type);
        return { id: id, url: '/_blob/' + id, sizeBytes: buf.length, contentType: (o && o.type) || blob.type };
      } };
    }
    return null;
  } };
})();
"""

class Env:
    def __init__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.published = []
    def ctx(self, w=1280, h=900, scheme='light', mobile=False):
        c = self.browser.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme,
                                     device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
        def blob_route(route):
            url = route.request.url
            bid = url.rsplit('/', 1)[-1].split('?')[0]
            if bid in ID2FILE:
                route.fulfill(status=200, content_type='image/jpeg', body=open(ID2FILE[bid], 'rb').read())
            elif bid in UPLOADS:
                route.fulfill(status=200, content_type='image/jpeg', body=UPLOADS[bid])
            else:
                route.fulfill(status=404, body='')
        c.route('**/_blob/*', blob_route)
        c.route(re.compile(r'https://fonts\.(googleapis|gstatic)\.com/.*'), lambda r: r.abort())
        return c
    def page(self, ctx, edit=True, **opt):
        o = dict(edit=edit, noClaude=False, pubErr=None, upErr=None, noArtifact=False, noAssets=False)
        o.update(opt)
        p = ctx.new_page()
        p.errors = []
        p.on('pageerror', lambda e: p.errors.append(str(e)))
        p.on('console', lambda m: p.errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        def cap_html(html):
            self.published.append(html)
            return True
        def cap_up(b64, typ):
            n = len(UPLOADS) + 1
            bid = ('%032x' % (0xabc000 + n))
            UPLOADS[bid] = base64.b64decode(b64)
            return bid
        p.expose_function('__capHtml', cap_html)
        p.expose_function('__capUpload', cap_up)
        p.add_init_script(INIT % json.dumps(o))
        return p
    def close(self):
        self.browser.close(); self.pw.stop()

def load(p, path=ROOT + '/dist/full.html', hash=''):
    p.goto('file://' + path + hash)
    p.wait_for_timeout(250)

def set_html(p, html, hash=''):
    open(os.path.join(__import__('tempfile').gettempdir(), '_emiles_cur.html'), 'w', encoding='utf-8').write(html)
    p.goto('file://' + os.path.join(__import__('tempfile').gettempdir(), '_emiles_cur.html') + hash)
    p.wait_for_timeout(250)
