/* Gestion de démonstration pour la version GitHub Pages.
   Sur la plateforme Claude, la page de gestion publie par l'API « artifact » et range les photos avec « assets ».
   Sur un hébergement ordinaire ces API n'existent pas : ce script les remplace par un stockage dans le navigateur.
   - Il ne s'active que si l'adresse se termine par #gestion (ou si cet onglet l'a déjà été).
   - « Publier » enregistre le catalogue sur cet appareil et recharge la page : personne d'autre ne voit les essais.
   - Les visiteurs normaux n'y voient rien, sauf un catalogue déjà enregistré sur leur propre appareil. */
(function () {
  var CK = 'emiles-demo-catalog', IK = 'emiles-demo-imgs', OK = 'emiles-demo-owner', DK = 'emiles-draft-v1';
  function ls(f) { try { return f(); } catch (e) { return null; } }
  if (location.hash === '#gestion') ls(function () { sessionStorage.setItem(OK, '1'); });
  var owner = !!ls(function () { return sessionStorage.getItem(OK); });

  /* catalogue et photos enregistrés sur cet appareil */
  var saved = ls(function () { return localStorage.getItem(CK); });
  if (saved) {
    try {
      var o = JSON.parse(saved);
      if (o && Array.isArray(o.products)) document.getElementById('catalog-data').textContent = saved;
    } catch (e) { saved = null; }
  }
  var imgs = ls(function () { return JSON.parse(localStorage.getItem(IK) || '{}'); }) || {};
  window.__demoImgs = imgs;
  if (!owner) return;

  function loadImage(blob) {
    return new Promise(function (res, rej) {
      var u = URL.createObjectURL(blob), i = new Image();
      i.onload = function () { URL.revokeObjectURL(u); res(i); };
      i.onerror = function () { URL.revokeObjectURL(u); rej({ code: 'decode' }); };
      i.src = u;
    });
  }
  function newId() {
    var a = new Uint8Array(16);
    crypto.getRandomValues(a);
    return Array.prototype.map.call(a, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
  }

  var user = {
    canEdit: async function () { return true; },
    isOwner: async function () { return true; },
    can: async function () { return true; }
  };
  var artifact = {
    publish: async function (html) {
      var m = /<script type="application\/json" id="catalog-data">([\s\S]*?)<\/script>/.exec(html);
      if (!m) throw { code: 'invalid_content' };
      var cat;
      try { cat = JSON.parse(m[1]); } catch (e) { throw { code: 'invalid_content' }; }
      if (!cat || !Array.isArray(cat.products)) throw { code: 'invalid_content' };
      var keep = {};
      cat.products.forEach(function (p) { if (p.img) keep[p.img] = 1; });
      Object.keys(imgs).forEach(function (k) { if (!keep[k]) delete imgs[k]; });
      try {
        localStorage.setItem(CK, JSON.stringify(cat));
        localStorage.setItem(IK, JSON.stringify(imgs));
      } catch (e) { throw { code: 'quota_or_state' }; }
      setTimeout(function () { location.reload(); }, 700);
      return { version: 'demo' };
    }
  };
  var assets = {
    upload: async function (blob) {
      var im = await loadImage(blob);
      var w0 = im.naturalWidth, h0 = im.naturalHeight;
      if (!w0 || !h0) throw { code: 'decode' };
      var s = Math.min(1, 900 / Math.max(w0, h0)), w = Math.max(1, Math.round(w0 * s)), h = Math.max(1, Math.round(h0 * s));
      var c = document.createElement('canvas');
      c.width = w; c.height = h;
      var g = c.getContext('2d');
      g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(im, 0, 0, w, h);
      var url = c.toDataURL('image/jpeg', 0.8), id = newId();
      imgs[id] = url;
      try { localStorage.setItem(IK, JSON.stringify(imgs)); }
      catch (e) { delete imgs[id]; throw { code: 'quota_or_state' }; }
      return { id: id, url: url, sizeBytes: url.length, contentType: 'image/jpeg' };
    }
  };
  window.claude = {
    use: async function (name) {
      if (name === 'user') return user;
      if (name === 'artifact') return artifact;
      if (name === 'assets') return assets;
      return null;
    }
  };

  /* bouton pour tout remettre à zéro entre deux présentations */
  document.addEventListener('DOMContentLoaded', function () {
    var act = document.querySelector('.owner-act');
    if (!act) return;
    var b = document.createElement('button'), t = 0;
    b.type = 'button'; b.className = 'btn btn-sm owner-btn'; b.id = 'demoReset';
    b.textContent = 'Remettre la démonstration à zéro';
    b.addEventListener('click', function () {
      if (!t) {
        b.textContent = 'Toucher encore pour confirmer';
        t = setTimeout(function () { t = 0; b.textContent = 'Remettre la démonstration à zéro'; }, 4000);
        return;
      }
      clearTimeout(t);
      ls(function () { localStorage.removeItem(CK); localStorage.removeItem(IK); localStorage.removeItem(DK); });
      try { history.replaceState(null, '', location.pathname + '#gestion'); } catch (e) { }
      location.reload();
    });
    act.appendChild(b);
  });
})();
