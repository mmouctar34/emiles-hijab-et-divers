/* ===================== GESTION DES PRODUITS (réservé au propriétaire) =====================
   Principe : la page est son propre enregistrement. Le catalogue est écrit dans la page (bloc catalog-data) et le
   gabarit complet de la page est gardé en base64 (bloc tpl-src). « Publier » reconstruit la page entière à partir
   du gabarit et du nouveau catalogue, puis la publie. Les clients ne voient le changement qu'après « Publier ». */
var ME={edit:false,checked:false,artifact:null,assets:null};
var DKEY='emiles-draft-v1',PUBFLAG='emiles-published';
var KEYS=['id','name','cat','group','sub','brand','img','alt','pos','unit','note','badge','tags','hide','packs'];
var PRESETS=[['Les 3',3],['Demi-douzaine',6],['Douzaine',12],['Demi-carton',48],['Carton',96]];
var UNIT_LIST=['pièce','paquet','boîte','sachet','flacon'];
var BADGES=['Nouveau','Stock limité','Promo','Dernières pièces','Meilleure vente'];
var draft=null,draftStale=false;
var ed=null,edDirty=false,edTrigger=null,sheetCfg=null,sheetBusy=false,sheetTrigger=null;

/* ----- outils ----- */
function clone(o){return JSON.parse(JSON.stringify(o))}
function ls(fn){try{return fn()}catch(e){return null}}
function pl(n,one,many){return n+' '+(n>1?many:one)}
function toInt(v){var n=parseInt(String(v==null?'':v).replace(/[^\d]/g,''),10);return isFinite(n)?n:0}
function canon(p){
  var o={};
  KEYS.forEach(function(k){
    var v=p[k];
    if(v===undefined||v===null||v===''||v===false)return;
    if(k==='tags'&&!v.length)return;
    o[k]=v;
  });
  return o;
}
function canonStr(p){return JSON.stringify(canon(p))}
function sameList(a,b){return a.length===b.length&&a.every(function(p,i){return canonStr(p)===canonStr(b[i])})}
function diffLists(base,cur){
  var bm={},cm={};
  base.forEach(function(p){bm[p.id]=p});cur.forEach(function(p){cm[p.id]=p});
  var added=cur.filter(function(p){return !bm[p.id]});
  var removed=base.filter(function(p){return !cm[p.id]});
  var changed=cur.filter(function(p){return bm[p.id]&&canonStr(p)!==canonStr(bm[p.id])});
  var ob=base.filter(function(p){return cm[p.id]}).map(function(p){return p.id}).join();
  var oc=cur.filter(function(p){return bm[p.id]}).map(function(p){return p.id}).join();
  var moved=ob!==oc;
  return {added:added,removed:removed,changed:changed,moved:moved,n:added.length+removed.length+changed.length+(moved?1:0)};
}
function work(){return draft||LIVE.products}
function brandsAll(){
  var seen={},out=[];
  ALL.forEach(function(p){if(p.brand&&!seen[p.brand]){seen[p.brand]=1;out.push(p.brand)}});
  return out.sort();
}
function subsOf(c,g){
  if(c.flat)return c.groups[0].items;
  var gg=c.groups.filter(function(x){return x.title===g})[0];
  return gg?gg.items:[];
}
function syncLock(){
  var any=!$('#editModal').hidden||!$('#sheet').hidden||!$('#searchModal').hidden||$('.drawer.open');
  document.body.style.overflow=any?'hidden':'';
}
function refreshAll(){
  renderTiles();renderBrands();renderShop();renderCart();
  if(!$('#searchModal').hidden)renderSearch();
}

/* ----- accès : seulement pour la personne qui peut modifier le site ----- */
function startAdmin(){
  (async function(){
    try{
      if(!window.claude||typeof window.claude.use!=='function')return;
      var u=await window.claude.use('user');
      var ok=u?await u.canEdit():false;
      if(!ok)return;
      ME.artifact=await window.claude.use('artifact');
      if(!ME.artifact)return;
      ME.assets=await window.claude.use('assets');
      enableAdmin();
    }catch(e){}
    finally{
      ME.checked=true;
      if(!ME.edit&&location.hash==='#gestion')clearHash();
    }
  })();
}
function enableAdmin(){
  ME.edit=true;
  $('#ownerBar').hidden=false;
  loadDraft();
  updateDraftUI();
  var pubd=ls(function(){var v=sessionStorage.getItem(PUBFLAG);sessionStorage.removeItem(PUBFLAG);return v});
  if(pubd)toast('Publié : le site est à jour',3500);
  if(location.hash==='#gestion')route();
}

/* ----- brouillon (gardé dans ce navigateur jusqu'à la publication) ----- */
function readDraft(){
  var d=ls(function(){return JSON.parse(localStorage.getItem(DKEY)||'null')});
  return d&&Array.isArray(d.products)?d:null;
}
function writeDraft(){
  ls(function(){
    if(draft)localStorage.setItem(DKEY,JSON.stringify({base:LIVE.rev,t:Date.now(),products:draft}));
    else localStorage.removeItem(DKEY);
  });
}
function loadDraft(){
  var d=readDraft();
  if(!d)return;
  if(sameList(d.products,LIVE.products)){ls(function(){localStorage.removeItem(DKEY)});return}
  draft=d.products;draftStale=d.base!==LIVE.rev;
  applyCatalog(work());refreshAll();
}
function setDraft(list){
  if(sameList(list,LIVE.products)){draft=null;draftStale=false}
  else draft=list;
  writeDraft();
  applyCatalog(work());
  refreshAll();
  updateDraftUI();
  if(!$('#page-gestion').hidden)renderAdmin();
}
function updateDraftUI(){
  var n=draft?diffLists(LIVE.products,draft).n:0;
  var show=ME.edit&&n>0;
  $('#draftBar').hidden=!show||!$('#page-gestion').hidden;
  $('#draftTxt').textContent=n+' '+(n>1?'modifications non publiées':'modification non publiée');
  $('#ownerPub').hidden=!show;
}

/* ----- page « Gestion des produits » ----- */
function renderAdmin(){
  if(!ME.edit)return;
  var list=work(),bm={};
  LIVE.products.forEach(function(p){bm[p.id]=p});
  var q=norm(($('#admQ').value||'').trim());
  var rows=list.map(function(p,i){return {p:p,i:i}}).filter(function(r){
    return !q||norm(r.p.name+' '+(r.p.brand||'')+' '+subLabel(r.p)+' '+catById(r.p.cat).label).indexOf(q)>=0;
  });
  var d=draft?diffLists(LIVE.products,draft):null;
  var hidden=list.filter(function(p){return p.hide}).length;
  var h='<p><b>'+pl(list.length,'produit','produits')+'</b>'+(hidden?' dont '+pl(hidden,'masqué','masqués'):'')+'.</p>';
  if(!d){
    h+='<p class="fine">Le site affiche exactement ce catalogue.</p>';
  }else{
    var parts=[];
    if(d.added.length)parts.push(pl(d.added.length,'ajouté','ajoutés'));
    if(d.changed.length)parts.push(pl(d.changed.length,'modifié','modifiés'));
    if(d.removed.length)parts.push(pl(d.removed.length,'retiré','retirés'));
    if(d.moved)parts.push('ordre changé');
    h+='<p><b>Brouillon non publié</b> : '+parts.join(', ')+'. Les clients ne voient rien de tout cela tant que vous n’avez pas publié.</p>';
    if(draftStale)h+='<p class="adm-warn">Le site a été modifié depuis le début de ce brouillon. Publier remplacerait ces modifications récentes.</p>';
    if(d.removed.length){
      h+='<div class="adm-gone">'+d.removed.map(function(p){return '<span>Retiré : '+esc(p.name)+' <button type="button" data-adm="restore" data-id="'+esc(p.id)+'">Rétablir</button></span>'}).join('')+'</div>';
    }
    h+='<div class="row"><button type="button" class="btn btn-primary btn-sm" data-adm="publish">Publier sur le site</button><button type="button" class="btn btn-ghost btn-sm" data-adm="discard">'+(draftStale?'Repartir de la version publiée':'Annuler tous les changements')+'</button></div>';
  }
  var sum=$('#admSum');sum.innerHTML=h;sum.classList.toggle('dirty',!!d);
  $('#admList').innerHTML=rows.length?rows.map(function(r){return admRow(r.p,r.i,list.length,bm,!!q)}).join(''):'<div class="empty"><h3>'+(q?'Aucun produit trouvé':'Aucun produit pour le moment')+'</h3><p>'+(q?'Essayez un autre mot.':'Touchez « Ajouter un produit » pour commencer.')+'</p></div>';
}
var ICON_TRASH='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12h10l1-12M9 7V4h6v3"/></svg>';
function admRow(p,i,total,bm,filtered){
  var st=!bm[p.id]?'new':(canonStr(p)!==canonStr(bm[p.id])?'mod':'');
  var pk=p.packs&&p.packs[0];
  var price=pk?'Dès '+fmt(pk[2])+' · '+pk[0]:'Aucun prix';
  var tags='';
  if(st==='new')tags+='<span class="tagx new">Ajouté, non publié</span>';
  else if(st==='mod')tags+='<span class="tagx mod">Modifié, non publié</span>';
  if(p.hide)tags+='<span class="tagx off">Masqué</span>';
  if(p.badge)tags+='<span class="tagx">'+esc(p.badge)+'</span>';
  (p.tags||[]).forEach(function(t){if(VIEW_LABEL[t])tags+='<span class="tagx">'+esc(VIEW_LABEL[t])+'</span>'});
  var id=esc(p.id),nm=esc(p.name);
  return '<article class="adm-row'+(st?' '+st:'')+(p.hide?' off':'')+'" data-id="'+id+'">'
   +'<div class="adm-thumb">'+imgEl(p.img,'','loading="lazy"')+'</div>'
   +'<div class="adm-info"><h3>'+nm+'</h3><p class="adm-meta">'+esc(catById(p.cat).label+' · '+subLabel(p))+(p.brand?' · '+esc(p.brand):'')+'</p>'
   +'<p class="adm-price">'+esc(price)+(p.packs.length>1?' <span class="adm-meta">('+p.packs.length+' lots)</span>':'')+'</p>'
   +(tags?'<div class="adm-tags">'+tags+'</div>':'')+'</div>'
   +'<div class="adm-act"><button type="button" class="btn btn-primary btn-sm" data-adm="edit" data-id="'+id+'" aria-label="Modifier '+nm+'">Modifier</button>'
   +'<button type="button" class="btn btn-ghost btn-sm" data-adm="hide" data-id="'+id+'" aria-label="'+(p.hide?'Afficher ':'Masquer ')+nm+'">'+(p.hide?'Afficher':'Masquer')+'</button>'
   +'<button type="button" class="ib" data-adm="up" data-id="'+id+'" aria-label="Monter '+nm+'"'+(filtered||i===0?' disabled':'')+'>↑</button>'
   +'<button type="button" class="ib" data-adm="down" data-id="'+id+'" aria-label="Descendre '+nm+'"'+(filtered||i===total-1?' disabled':'')+'>↓</button>'
   +'<button type="button" class="ib danger" data-adm="del" data-id="'+id+'" aria-label="Supprimer '+nm+'">'+ICON_TRASH+'</button></div></article>';
}

function adminAction(a,el){
  var id=el.dataset.id,l,i,p;
  switch(a){
    case 'open':showPage('gestion');setHash('#gestion');break;
    case 'new':openEditor(null);break;
    case 'edit':openEditor(id);break;
    case 'hide':
      l=clone(work());p=l.filter(function(x){return x.id===id})[0];
      if(p){if(p.hide)delete p.hide;else p.hide=true;setDraft(l);toast(p.hide?'Masqué : retiré de la boutique à la publication':'Affiché de nouveau')}
      break;
    case 'up':case 'down':
      l=clone(work());i=l.map(function(x){return x.id}).indexOf(id);
      var j=a==='up'?i-1:i+1;
      if(i>=0&&j>=0&&j<l.length){var t=l[i];l[i]=l[j];l[j]=t;setDraft(l)}
      break;
    case 'del':askDelete(id,false);break;
    case 'restore':
      var gone=LIVE.products.filter(function(x){return x.id===id})[0];
      if(gone){l=clone(work());l.splice(Math.min(LIVE.products.indexOf(gone),l.length),0,clone(gone));setDraft(l)}
      break;
    case 'discard':
      openSheet({title:draftStale?'Repartir de la version publiée ?':'Annuler tous les changements ?',
        body:'<p>Votre brouillon sera effacé et la boutique reviendra à la version actuellement publiée.</p>',
        actions:[{label:'Garder mon brouillon'},{label:'Effacer le brouillon',cls:'btn-danger',fn:function(){setDraft(clone(LIVE.products));toast('Brouillon effacé')}}]});
      break;
    case 'publish':openPublish();break;
  }
}
function askDelete(id,fromEditor){
  var p=work().filter(function(x){return x.id===id})[0];
  if(!p)return;
  openSheet({title:'Supprimer ce produit ?',
    body:'<p>« <b>'+esc(p.name)+'</b> » sera retiré de la boutique à la prochaine publication. Tant que vous n’avez pas publié, vous pouvez le rétablir.</p>',
    actions:[{label:'Garder'},{label:'Supprimer',cls:'btn-danger',fn:function(){
      setDraft(clone(work()).filter(function(x){return x.id!==id}));
      if(fromEditor)closeEditor();
      toast('Produit retiré du brouillon');
    }}]});
}

/* ----- fenêtre de confirmation ----- */
function openSheet(o){
  sheetCfg=o;sheetBusy=false;
  $('#sheetTitle').textContent=o.title;
  $('#sheetBody').innerHTML=o.body||'';
  var er=$('#sheetErr');er.hidden=true;er.textContent='';
  $('#sheetAct').innerHTML=o.actions.map(function(a,i){return '<button type="button" class="btn '+(a.cls||'btn-ghost')+' btn-sm" data-sheet="'+i+'">'+esc(a.label)+'</button>'}).join('');
  sheetTrigger=document.activeElement;
  $('#sheet').hidden=false;syncLock();
  var f=$('#sheetAct .btn-primary,#sheetAct .btn-danger')||$('#sheetAct .btn');
  if(f)f.focus();
}
function closeSheet(){
  $('#sheet').hidden=true;sheetCfg=null;sheetBusy=false;syncLock();
  if(sheetTrigger&&document.contains(sheetTrigger)&&!sheetTrigger.disabled)sheetTrigger.focus();
}
function sheetBusySet(on){
  sheetBusy=on;
  $$('#sheetAct .btn').forEach(function(b){b.disabled=on});
}
function sheetAction(i){
  if(!sheetCfg||sheetBusy)return;
  var a=sheetCfg.actions[i];if(!a)return;
  var r=a.fn?a.fn():undefined;
  if(r!==false)closeSheet();
}

/* ----- éditeur de produit ----- */
function openEditor(id){
  var src=id?work().filter(function(p){return p.id===id})[0]:null;
  if(id&&!src)return;
  var c0=(state.cat!=='all'&&catById(state.cat))||CATS[0];
  var has=function(t){return !!(src&&src.tags&&src.tags.indexOf(t)>=0)};
  if(src){
    ed={id:src.id,isNew:false,name:src.name,name0:src.name,alt0:src.alt||'',cat:src.cat,group:src.group||'',sub:src.sub||'',brand:src.brand||'',
      img:src.img||'',pos:src.pos||'',posNum:parseInt((/(\d+)%/.exec(src.pos||'')||[0,50])[1],10),unit:src.unit||'pièce',note:src.note||'',badge:src.badge||'',
      tags:{new:has('new'),promo:has('promo'),gift:has('gift')},hide:!!src.hide,
      packs:src.packs.map(function(k){return {l:k[0],q:String(k[1]),p:String(k[2])}}),up:'',upStatus:'',photoErr:''};
  }else{
    ed={id:null,isNew:true,name:'',name0:'',alt0:'',cat:c0.id,group:c0.flat?'':c0.groups[0].title,sub:'',brand:'',img:'',pos:'',posNum:50,unit:'pièce',note:'',badge:'',
      tags:{new:false,promo:false,gift:false},hide:false,
      packs:PRESETS.slice(0,3).map(function(a){return {l:a[0],q:String(a[1]),p:''}}),up:'',upStatus:'',photoErr:''};
  }
  edDirty=false;edTrigger=document.activeElement;hideEdErrors();
  $('#edTitle').textContent=ed.isNew?'Ajouter un produit':'Modifier le produit';
  $('#edBody').innerHTML=edFormHTML();
  renderEdPhoto();renderEdCats();renderEdPacks();
  $('#edDel').hidden=ed.isNew;
  $('#editModal').hidden=false;syncLock();
  $('#edBody').scrollTop=0;
  setTimeout(function(){var f=$('#ed-name');if(f&&ed&&ed.isNew)f.focus()},40);
}
function fldOpt(v,l,sel){return '<option value="'+esc(v)+'"'+(v===sel?' selected':'')+'>'+esc(l)+'</option>'}
function edFormHTML(){
  return '<section class="ed-sec"><h3>1. La photo</h3><div id="edPhoto"></div>'
   +'<input type="file" id="edFile" accept="image/*" class="sr-only" tabindex="-1" aria-hidden="true"></section>'
   +'<section class="ed-sec"><h3>2. Le produit</h3>'
   +'<div class="fld"><label for="ed-name">Nom du produit</label><input id="ed-name" data-f="name" type="text" maxlength="90" autocomplete="off" placeholder="Ex. : Parfum Moussuf" value="'+esc(ed.name)+'"></div>'
   +'<div id="edCats"></div>'
   +'<div class="fld"><label for="ed-brand">Marque (si vous la connaissez)</label><input id="ed-brand" data-f="brand" type="text" maxlength="40" autocomplete="off" list="edBrands" placeholder="Ex. : Moussuf" value="'+esc(ed.brand)+'"><datalist id="edBrands">'+brandsAll().map(function(b){return '<option value="'+esc(b)+'">'}).join('')+'</datalist></div>'
   +'</section>'
   +'<section class="ed-sec"><h3>3. Les lots et les prix</h3><div id="edPacks"></div></section>'
   +'<section class="ed-sec"><h3>4. L’affichage</h3>'
   +'<div class="fld"><label for="ed-note">Petite note sous le nom (facultatif)</label><input id="ed-note" data-f="note" type="text" maxlength="90" autocomplete="off" placeholder="Ex. : Livraison à Dakar offerte dès la douzaine" value="'+esc(ed.note)+'"></div>'
   +'<div class="fld"><label for="ed-badge">Étiquette sur la photo (facultatif)</label><input id="ed-badge" data-f="badge" type="text" maxlength="22" autocomplete="off" list="edBadges" placeholder="Ex. : Nouveau" value="'+esc(ed.badge)+'"><datalist id="edBadges">'+BADGES.map(function(b){return '<option value="'+esc(b)+'">'}).join('')+'</datalist></div>'
   +'<div class="checks"><label class="chk"><input type="checkbox" data-f="show"'+(ed.hide?'':' checked')+'> Afficher ce produit aux clients</label></div>'
   +'<p class="hint">Décochez si le produit est épuisé : il disparaît de la boutique sans être supprimé, et vous pouvez le réafficher plus tard.</p>'
   +'</section>';
}
function renderEdPhoto(){
  var src=ed.img?imgSrc(ed.img):'';
  var h='<div class="ed-frame">'+(src
    ?'<img id="edImg" src="'+esc(src)+'" alt="Aperçu de la photo du produit" style="object-position:center '+ed.posNum+'%">'
    :'<div class="ed-noimg"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h3l1.6-2.4h6.8L17 8h3v11H4z"/><circle cx="12" cy="13.5" r="3.5"/></svg><span>Aucune photo</span></div>')+'</div>';
  if(ed.upStatus)h+='<p class="ed-busy" role="status"><span class="spin" aria-hidden="true"></span>'+esc(ed.upStatus)+'</p>';
  if(ed.photoErr)h+='<p class="err" role="alert">'+esc(ed.photoErr)+'</p>';
  h+='<div class="ed-photo-btns"><button type="button" class="btn btn-primary btn-sm" data-ed="pick"'+(ed.upStatus?' disabled':'')+'>'+(ed.img?'Changer la photo':'Choisir une photo')+'</button>'
    +(ed.img?'<button type="button" class="btn btn-ghost btn-sm" data-ed="rmphoto"'+(ed.upStatus?' disabled':'')+'>Retirer la photo</button>':'')+'</div>';
  if(ed.img)h+='<div class="fld"><label for="ed-pos">Cadrage de la photo</label><input id="ed-pos" type="range" min="0" max="100" step="1" value="'+ed.posNum+'" data-f="pos"><span class="hint">Faites glisser pour monter ou descendre la photo dans le cadre, comme elle apparaîtra dans la boutique.</span></div>';
  else h+='<p class="hint">Prenez la photo avec le téléphone ou choisissez-la dans la galerie. Elle est réduite automatiquement. Sans photo, le logo s’affiche à la place.</p>';
  $('#edPhoto').innerHTML=h;
}
function renderEdCats(){
  var c=catById(ed.cat);
  var h='<div class="fld"><label for="ed-cat">Catégorie</label><select id="ed-cat" data-f="cat">'+CATS.map(function(x){return fldOpt(x.id,x.label,ed.cat)}).join('')+'</select></div>';
  if(!c.flat){
    var gs=c.groups.map(function(g){return g.title});
    if(ed.group&&gs.indexOf(ed.group)<0)gs.push(ed.group);
    h+='<div class="fld"><label for="ed-group">Rayon</label><select id="ed-group" data-f="group">'+gs.map(function(g){return fldOpt(g,g,ed.group)}).join('')+'</select></div>';
  }
  var subs=subsOf(c,ed.group).slice();
  if(ed.sub&&subs.indexOf(ed.sub)<0)subs.push(ed.sub);
  if(subs.length)h+='<div class="fld"><label for="ed-sub">Type de produit</label><select id="ed-sub" data-f="sub"><option value="">Non précisé</option>'+subs.map(function(s){return fldOpt(s,s,ed.sub)}).join('')+'</select></div>';
  $('#edCats').innerHTML=h;
}
function packText(k){
  var q=toInt(k.q),p=toInt(k.p);
  if(!q||!p)return 'Le prix à la pièce s’affichera ici.';
  return packInfo({unit:ed.unit==='pièce'?'':ed.unit},[k.l,q,p]);
}
function renderEdPacks(focusId){
  var rows=ed.packs.map(function(k,i){
    return '<div class="ed-pack">'
     +'<div class="fld pk-l"><label for="pk-l-'+i+'">Nom du lot</label><input id="pk-l-'+i+'" data-pk="'+i+'" data-k="l" type="text" maxlength="40" autocomplete="off" value="'+esc(k.l)+'"></div>'
     +'<div class="fld pk-q"><label for="pk-q-'+i+'">Quantité</label><input id="pk-q-'+i+'" data-pk="'+i+'" data-k="q" type="text" inputmode="numeric" autocomplete="off" value="'+esc(k.q)+'"></div>'
     +'<div class="fld pk-p"><label for="pk-p-'+i+'">Prix du lot (FCFA)</label><input id="pk-p-'+i+'" data-pk="'+i+'" data-k="p" type="text" inputmode="numeric" autocomplete="off" placeholder="Ex. : 4500" value="'+esc(k.p)+'"></div>'
     +'<button type="button" class="icon-btn pk-x" data-ed="rmpack" data-i="'+i+'" aria-label="Retirer le lot '+(i+1)+'"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg></button>'
     +'<p class="pk-info" id="pk-info-'+i+'">'+esc(packText(k))+'</p></div>';
  }).join('');
  var have={};ed.packs.forEach(function(k){have[toInt(k.q)]=1});
  var h='<div class="fld"><label for="ed-unit">Les articles se comptent à la…</label><select id="ed-unit" data-f="unit">'+UNIT_LIST.map(function(u){return fldOpt(u,u,ed.unit)}).join('')+'</select></div>'
   +rows
   +'<div class="ed-chips" role="group" aria-label="Ajouter un lot">'+PRESETS.map(function(a,i){return '<button type="button" data-ed="addpack" data-pre="'+i+'"'+(have[a[1]]?' disabled':'')+'>+ '+esc(a[0])+'</button>'}).join('')+'<button type="button" data-ed="addpack" data-pre="-1">+ Autre lot</button></div>'
   +'<div class="ed-calc"><div class="fld"><label for="ed-up">Prix à la pièce (FCFA)</label><input id="ed-up" data-f="up" type="text" inputmode="numeric" autocomplete="off" placeholder="Ex. : 1500" value="'+esc(ed.up)+'"></div>'
   +'<button type="button" class="btn btn-ghost btn-sm" data-ed="calc">Calculer les prix des lots</button>'
   +'<p class="hint">Si tous vos lots suivent le même prix à la pièce, écrivez-le ici : le prix de chaque lot se remplit tout seul. Vous pouvez ensuite le corriger.</p></div>';
  $('#edPacks').innerHTML=h;
  if(focusId){var f=$('#'+focusId);if(f)f.focus()}
}
function addPack(pre){
  var a=PRESETS[pre];
  ed.packs.push(a?{l:a[0],q:String(a[1]),p:''}:{l:'',q:'',p:''});
  edDirty=true;
  var i=ed.packs.length-1;
  renderEdPacks(a?'pk-p-'+i:'pk-l-'+i);
}
function calcPacks(){
  var u=toInt(ed.up);
  if(!u){showEdErrors([{f:'ed-up',m:'Écrivez d’abord le prix à la pièce.'}]);return}
  hideEdErrors();
  ed.packs.forEach(function(k){var q=toInt(k.q);if(q)k.p=String(q*u)});
  edDirty=true;renderEdPacks();
}
function showEdErrors(errs){
  var box=$('#edErr');
  box.innerHTML='<p>Il manque quelques informations :</p><ul>'+errs.map(function(e){return '<li>'+esc(e.m)+'</li>'}).join('')+'</ul>';
  box.hidden=false;
  errs.forEach(function(e){var f=e.f&&$('#'+e.f);if(f)f.setAttribute('aria-invalid','true')});
  var first=errs.map(function(e){return e.f&&$('#'+e.f)}).filter(Boolean)[0];
  if(first){first.focus({preventScroll:true});first.scrollIntoView({block:'center'})}
}
function hideEdErrors(){var b=$('#edErr');if(b){b.hidden=true;b.innerHTML=''}}

/* photo : réduite sur le téléphone puis envoyée dans le stockage de la page */
function readDataURL(blob){
  return new Promise(function(res,rej){
    var r=new FileReader();
    r.onload=function(){res(r.result)};
    r.onerror=function(){rej({code:'decode'})};
    r.readAsDataURL(blob);
  });
}
function loadImg(src){
  return new Promise(function(res,rej){
    var im=new Image();
    im.onload=function(){res(im)};
    im.onerror=function(){rej({code:'decode'})};
    im.src=src;
  });
}
async function shrink(file){
  var im=await loadImg(await readDataURL(file));
  var w=im.naturalWidth,h=im.naturalHeight;
  if(!w||!h)throw {code:'decode'};
  var s=Math.min(1,1400/Math.max(w,h)),cw=Math.max(1,Math.round(w*s)),ch=Math.max(1,Math.round(h*s));
  var c=document.createElement('canvas');c.width=cw;c.height=ch;
  var g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,cw,ch);g.drawImage(im,0,0,cw,ch);
  var blob=await new Promise(function(res){c.toBlob(res,'image/jpeg',.86)});
  if(!blob)throw {code:'decode'};
  return blob;
}
function uploadMsg(e){
  switch(e&&e.code){
    case 'decode':return 'Cette photo ne peut pas être lue. Essayez une photo JPEG ou PNG.';
    case 'no_assets':case 'not_granted':case 'capability_disabled':case 'capability_removed':return 'L’envoi de photo n’est pas disponible depuis cet affichage. Ouvrez le site avec le compte propriétaire.';
    case 'too_large':return 'La photo est trop lourde.';
    case 'quota_or_state':return 'L’espace de stockage du site est plein.';
    case 'rate_limited':return 'Trop d’envois d’affilée. Patientez un instant puis réessayez.';
    case 'unsupported_type':return 'Ce type de fichier n’est pas accepté. Choisissez une photo.';
    default:return 'L’envoi a échoué (problème temporaire). Réessayez.';
  }
}
async function onFile(file){
  if(!file||!ed)return;
  var mine=ed;
  mine.photoErr='';mine.upStatus='Préparation de la photo…';renderEdPhoto();
  try{
    var blob=await shrink(file);
    if(!ME.assets)throw {code:'no_assets'};
    var preview=await readDataURL(blob);
    mine.upStatus='Envoi de la photo…';if(ed===mine)renderEdPhoto();
    var r=await ME.assets.upload(blob,{type:'image/jpeg'});
    urlCache[r.id]=preview;
    mine.img=r.id;mine.pos='';mine.posNum=50;mine.upStatus='';edDirty=true;
  }catch(e){
    mine.upStatus='';mine.photoErr=uploadMsg(e);
  }
  if(ed===mine)renderEdPhoto();
}

function validateEd(){
  var errs=[],packs=[],seen={};
  if(!ed.name.trim())errs.push({f:'ed-name',m:'Écrivez le nom du produit.'});
  if(ed.upStatus)errs.push({f:'',m:'Patientez : la photo est en cours d’envoi.'});
  ed.packs.forEach(function(k,i){
    var q=toInt(k.q),p=toInt(k.p),l=k.l.trim(),n=i+1;
    if(!l&&!q&&!p)return;
    if(q<1){errs.push({f:'pk-q-'+i,m:'Lot '+n+' : indiquez la quantité.'});return}
    if(p<1){errs.push({f:'pk-p-'+i,m:'Lot '+n+' : indiquez le prix en FCFA.'});return}
    if(seen[q]){errs.push({f:'pk-q-'+i,m:'Deux lots ont la même quantité ('+q+'). Gardez-en un seul.'});return}
    seen[q]=1;
    packs.push([l||(q+' '+ed.unit+(q>1?'s':'')),q,p]);
  });
  if(!packs.length&&!errs.some(function(e){return /^pk-/.test(e.f)}))errs.push({f:ed.packs.length?'pk-p-0':'ed-unit',m:'Ajoutez au moins un lot avec son prix.'});
  packs.sort(function(a,b){return a[1]-b[1]});
  return {errs:errs,packs:packs};
}
function saveEditor(){
  if(!ed)return;
  hideEdErrors();$$('#edBody [aria-invalid]').forEach(function(x){x.removeAttribute('aria-invalid')});
  var v=validateEd();
  if(v.errs.length){showEdErrors(v.errs);return}
  var c=catById(ed.cat),name=ed.name.trim();
  var p=canon({
    id:ed.id||('p'+Date.now().toString(36)),name:name,cat:ed.cat,group:c.flat?'':ed.group,sub:ed.sub,brand:ed.brand.trim(),img:ed.img,
    alt:(ed.isNew||name!==ed.name0)?name:ed.alt0,pos:ed.pos,unit:ed.unit==='pièce'?'':ed.unit,note:ed.note.trim(),badge:ed.badge.trim(),
    tags:['new','promo','gift'].filter(function(t){return ed.tags[t]}),hide:ed.hide,packs:v.packs
  });
  var l=clone(work());
  if(ed.isNew)l.unshift(p);
  else{var i=l.map(function(x){return x.id}).indexOf(ed.id);if(i>=0)l[i]=p;else l.unshift(p)}
  var wasNew=ed.isNew;
  setDraft(l);closeEditor();
  toast(wasNew?'Ajouté au brouillon. Touchez « Publier » pour l’afficher.':'Enregistré dans le brouillon. Touchez « Publier » pour l’afficher.',4200);
}
function tryCloseEditor(){
  if(!ed){return}
  if(!edDirty){closeEditor();return}
  openSheet({title:'Abandonner les changements ?',body:'<p>Ce que vous avez saisi pour ce produit ne sera pas enregistré.</p>',
    actions:[{label:'Continuer à modifier'},{label:'Abandonner',cls:'btn-danger',fn:function(){closeEditor()}}]});
}
function closeEditor(){
  $('#editModal').hidden=true;ed=null;edDirty=false;
  syncLock();
  if(edTrigger&&document.contains(edTrigger)&&!edTrigger.disabled)edTrigger.focus();
}

/* ----- publication : la page se reconstruit à partir de son gabarit ----- */
var MARK='%'+'%BLOCKS%'+'%';
var SKEL_HEAD='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>';
var SKEL_TAIL='</body></html>';
var S_OPEN='<scr'+'ipt',S_CLOSE='</scr'+'ipt>';
function b64e(s){
  var b=new TextEncoder().encode(s),r='';
  for(var i=0;i<b.length;i+=0x8000)r+=String.fromCharCode.apply(null,b.subarray(i,i+0x8000));
  return btoa(r);
}
function b64d(t){
  var r=atob(String(t).replace(/\s+/g,'')),b=new Uint8Array(r.length);
  for(var i=0;i<r.length;i++)b[i]=r.charCodeAt(i);
  return new TextDecoder().decode(b);
}
function jsonSafe(o){return JSON.stringify(o).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029')}
function blocksFor(P,cat){
  return S_OPEN+' type="application/json" id="catalog-data">'+jsonSafe(cat)+S_CLOSE+'\n'+S_OPEN+' type="text/plain" id="tpl-src">'+b64e(P)+S_CLOSE;
}
function buildDoc(P,cat){
  var content=P.replace(MARK,function(){return blocksFor(P,cat)});
  return SKEL_HEAD+'\n'+content+'\n'+SKEL_TAIL;
}
function getTpl(){var t=$('#tpl-src');return t?b64d(t.textContent):''}
function checkDoc(html,P,cat){
  var bad=function(){throw {code:'invalid_content'}};
  if(html.indexOf('<!doctype html>')!==0||html.length>12000000)bad();
  if(P.split(MARK).length!==2||P.indexOf('<title>')!==0)bad();
  var d=new DOMParser().parseFromString(html,'text/html');
  var cd=d.getElementById('catalog-data'),ts=d.getElementById('tpl-src');
  if(!cd||!ts)bad();
  if(JSON.stringify(JSON.parse(cd.textContent))!==JSON.stringify(cat))bad();
  if(b64d(ts.textContent)!==P)bad();
}
function openPublish(){
  if(!draft)return;
  var d=diffLists(LIVE.products,draft),it='';
  d.added.forEach(function(p){it+='<li>Ajouté : <b>'+esc(p.name)+'</b></li>'});
  d.changed.forEach(function(p){it+='<li>Modifié : <b>'+esc(p.name)+'</b></li>'});
  d.removed.forEach(function(p){it+='<li>Retiré : <b>'+esc(p.name)+'</b></li>'});
  if(d.moved)it+='<li>Ordre des produits modifié</li>';
  var warn=draftStale?'<p class="adm-warn">Le site a changé depuis que vous avez commencé ce brouillon : publier remplacera ces changements récents.</p>':'';
  openSheet({title:'Publier sur le site ?',body:'<p>Dès la publication, les clients verront :</p><ul>'+it+'</ul>'+warn,
    actions:[{label:'Pas maintenant'},{label:'Publier maintenant',cls:'btn-primary',fn:doPublish}]});
}
function publishMsg(e){
  switch(e&&e.code){
    case 'conflict':return 'Le site vient d’être modifié ailleurs. La page se recharge avec la dernière version ; votre brouillon est conservé.';
    case 'not_writer':case 'not_granted':case 'consent_required':case 'not_declared':case 'capability_disabled':case 'capability_removed':return 'Vous ne pouvez pas publier depuis cet affichage. Ouvrez le site avec le compte propriétaire.';
    case 'too_large':return 'Le site est devenu trop volumineux. Retirez quelques produits.';
    case 'rate_limited':return 'Trop de publications d’affilée. Patientez une minute puis recommencez.';
    case 'invalid_content':case 'transform_error':return 'La page n’a pas pu être préparée. Rien n’a été publié et votre brouillon est conservé.';
    default:return 'La publication a échoué (problème temporaire). Rien n’a été publié. Réessayez dans un instant.';
  }
}
function doPublish(){
  var cfg=sheetCfg,keep=cfg.body;
  sheetBusySet(true);
  $('#sheetBody').innerHTML='<p class="ed-busy" role="status"><span class="spin" aria-hidden="true"></span>Publication en cours…</p>';
  (async function(){
    try{
      var P=getTpl();
      var cat={v:1,rev:LIVE.rev+1,updated:new Date().toISOString().slice(0,10),products:clone(draft).map(canon)};
      var html=buildDoc(P,cat);
      checkDoc(html,P,cat);
      ls(function(){sessionStorage.setItem(PUBFLAG,'1')});
      await ME.artifact.publish(html);
      $('#sheetBody').innerHTML='<p><b>C’est publié.</b> La page se recharge…</p>';
      $('#sheetAct').innerHTML='<button type="button" class="btn btn-primary btn-sm" data-reload>Recharger maintenant</button>';
    }catch(e){
      ls(function(){sessionStorage.removeItem(PUBFLAG)});
      if(sheetCfg!==cfg)return;
      $('#sheetBody').innerHTML=keep;
      var er=$('#sheetErr');er.textContent=publishMsg(e);er.hidden=false;
      sheetBusySet(false);
    }
  })();
  return false;
}

/* ----- clics, saisie et clavier de l'espace de gestion ----- */
document.addEventListener('click',function(e){
  var t=e.target;
  if(!t||!t.closest)return;
  if(t.closest('[data-reload]')){location.reload();return}
  var a=t.closest('[data-adm]');
  if(a&&ME.edit){adminAction(a.dataset.adm,a);return}
  var d=t.closest('[data-ed]');
  if(d&&ed){
    switch(d.dataset.ed){
      case 'pick':$('#edFile').click();break;
      case 'rmphoto':ed.img='';ed.pos='';ed.posNum=50;ed.photoErr='';edDirty=true;renderEdPhoto();break;
      case 'addpack':addPack(+d.dataset.pre);break;
      case 'rmpack':ed.packs.splice(+d.dataset.i,1);edDirty=true;renderEdPacks();break;
      case 'calc':calcPacks();break;
      case 'save':saveEditor();break;
      case 'cancel':tryCloseEditor();break;
      case 'del':askDelete(ed.id,true);break;
    }
    return;
  }
  var s=t.closest('[data-sheet]');
  if(s){sheetAction(+s.dataset.sheet);return}
});
$('#editModal').addEventListener('input',function(e){
  var t=e.target;
  if(!ed||!t.dataset)return;
  edDirty=true;
  if(t.dataset.pk!==undefined){
    var k=ed.packs[+t.dataset.pk];
    if(!k)return;
    k[t.dataset.k]=t.value;
    t.removeAttribute('aria-invalid');
    var inf=$('#pk-info-'+t.dataset.pk);if(inf)inf.textContent=packText(k);
    return;
  }
  var f=t.dataset.f;
  if(f==='pos'){ed.posNum=+t.value;ed.pos='center '+t.value+'%';var im=$('#edImg');if(im)im.style.objectPosition='center '+t.value+'%';return}
  if(f==='name'||f==='brand'||f==='note'||f==='badge'||f==='up'){ed[f]=t.value;t.removeAttribute('aria-invalid')}
});
$('#editModal').addEventListener('change',function(e){
  var t=e.target;
  if(!ed||!t)return;
  if(t.id==='edFile'){var fl=t.files&&t.files[0];t.value='';onFile(fl);return}
  var f=t.dataset&&t.dataset.f;
  if(!f)return;
  edDirty=true;
  if(f==='cat'){
    var c=catById(t.value);ed.cat=c.id;ed.group=c.flat?'':c.groups[0].title;ed.sub='';renderEdCats();
  }else if(f==='group'){ed.group=t.value;ed.sub='';renderEdCats()}
  else if(f==='sub'){ed.sub=t.value}
  else if(f==='unit'){ed.unit=t.value;renderEdPacks()}
  else if(f==='show'){ed.hide=!t.checked}
  else if(f.indexOf('tag-')===0){ed.tags[f.slice(4)]=t.checked}
});
$('#admQ').addEventListener('input',renderAdmin);
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){
    if(!$('#sheet').hidden){if(!sheetBusy)closeSheet();return}
    if(!$('#editModal').hidden){tryCloseEditor()}
  }
  if(e.key==='Enter'&&ed&&e.target&&e.target.tagName==='INPUT'&&e.target.type!=='checkbox'){e.preventDefault()}
});
