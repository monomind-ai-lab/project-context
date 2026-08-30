/* =====================================================================
   site.js — the shared machinery, loaded by every page.

   Split out of the two hand-authored pages, which each carried their own
   copy. Runs after the page's own `const I18N = {...}` (emitted inline just
   above by scripts/build_site.py) and reads it directly: top-level lexical
   declarations in a classic script are visible to the classic scripts that
   follow it.

   Section 2 is load-bearing and must not be simplified — see its comment.
   ===================================================================== */

/* =====================================================================
   1. LANGUAGE TABLE
   `tier:"native"` = a hand-written dictionary above. `tier:"auto"` = the
   page stays English and Google Translate renders it.
   ===================================================================== */
const LANGS = [
  { code:"en",    tier:"native", label:"EN",    name:"English",             native:"English" },
  { code:"ko",    tier:"native", label:"KO",    name:"Korean",              native:"한국어" },
  { code:"zh-TW", tier:"native", label:"ZH-TW", name:"Traditional Chinese", native:"繁體中文" },
  { code:"ja",    tier:"auto",   label:"JA",    name:"Japanese",            native:"日本語" },
  { code:"zh-CN", tier:"auto",   label:"ZH-CN", name:"Simplified Chinese",  native:"简体中文" },
  { code:"es",    tier:"auto",   label:"ES",    name:"Spanish",             native:"Español" },
  { code:"fr",    tier:"auto",   label:"FR",    name:"French",              native:"Français" },
  { code:"de",    tier:"auto",   label:"DE",    name:"German",              native:"Deutsch" },
  { code:"pt",    tier:"auto",   label:"PT",    name:"Portuguese",          native:"Português" },
  { code:"it",    tier:"auto",   label:"IT",    name:"Italian",             native:"Italiano" },
  { code:"ru",    tier:"auto",   label:"RU",    name:"Russian",             native:"Русский" },
  { code:"hi",    tier:"auto",   label:"HI",    name:"Hindi",               native:"हिन्दी" },
  { code:"ar",    tier:"auto",   label:"AR",    name:"Arabic",              native:"العربية" },
  { code:"id",    tier:"auto",   label:"ID",    name:"Indonesian",          native:"Bahasa Indonesia" },
  { code:"th",    tier:"auto",   label:"TH",    name:"Thai",                native:"ไทย" },
  { code:"vi",    tier:"auto",   label:"VI",    name:"Vietnamese",          native:"Tiếng Việt" },
  { code:"nl",    tier:"auto",   label:"NL",    name:"Dutch",               native:"Nederlands" },
  { code:"pl",    tier:"auto",   label:"PL",    name:"Polish",              native:"Polski" },
  { code:"tr",    tier:"auto",   label:"TR",    name:"Turkish",             native:"Türkçe" },
  { code:"sv",    tier:"auto",   label:"SV",    name:"Swedish",             native:"Svenska" }
];
const RTL = ["ar","he","fa","ur"];
const LANG_KEY = 'pc-lang', THEME_KEY = 'pc-theme';
function langByCode(c){ for (var i=0;i<LANGS.length;i++) if (LANGS[i].code === c) return LANGS[i]; return null; }
function isNative(c){ var l = langByCode(c); return !!l && l.tier === 'native'; }

/* The page's effective locale, resolved once here so every caller agrees.
   A stored native choice wins; otherwise a machine choice from the cookie;
   otherwise English. A googtrans cookie with no stored machine choice is a
   leftover — very likely the domain-scoped twin Google wrote on some other
   page of the registrable domain — so the stored choice is honoured, not
   the cookie.

   BOOT and the sign-off band both depend on this answer. They used to
   compute it separately; if the two ever disagreed, the band would split
   its text under a machine locale and Google would translate the
   one-glyph spans individually into nonsense. One function, one answer. */
function resolveLang(){
  var stored = null;
  try { stored = localStorage.getItem(LANG_KEY); } catch (e) {}
  if (!langByCode(stored)) stored = null;
  var cookieLang = readGoogtrans();
  return stored || (langByCode(cookieLang) && !isNative(cookieLang) ? cookieLang : 'en');
}

/* =====================================================================
   2. GOOGTRANS COOKIE — THE PART THAT MUST NOT BE SIMPLIFIED
   Google's element.js does not only read `googtrans`; it REWRITES it, and
   it writes at the REGISTRABLE DOMAIN (e.g. `.monomind.one`), not at the
   host we wrote it on. So a host-scoped write leaves TWO cookies with the
   same name. document.cookie exposes no domain attribute, so the first
   match wins on read — and that is the stale domain-scoped one. The site
   then freezes on a previously chosen language, on EVERY subdomain, with
   no way for the user to get back. That is the production bug this file
   exists to not reproduce.
   The rule: DELETE at every scope first, then write at exactly one.
   ===================================================================== */
var EXPIRED = 'expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';

function clearGoogtrans(){
  var host = location.hostname;
  /* 1. the no-domain (host-only) copy */
  document.cookie = 'googtrans=; ' + EXPIRED;
  /* 2. every parent-domain suffix, with and without the leading dot.
        A bare IPv4 literal has no domain hierarchy — skip the loop. */
  if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) {
    var parts = host.split('.');
    for (var i = 0; i <= parts.length - 2; i++) {
      var suffix = parts.slice(i).join('.');
      document.cookie = 'googtrans=; domain=' + suffix + '; ' + EXPIRED;
      document.cookie = 'googtrans=; domain=.' + suffix + '; ' + EXPIRED;
    }
  }
}

function setGoogtrans(code){
  clearGoogtrans();                                   /* never write over a stale twin */
  document.cookie = 'googtrans=/en/' + code + '; path=/';   /* exactly one scope: host */
}

/* Do NOT take the first `googtrans=` match blindly — after Google has
   rewritten the cookie there may be several, and the leading one is often
   the stale or malformed copy. Take the first WELL-FORMED `/en/<code>`. */
function readGoogtrans(){
  var jar = document.cookie ? document.cookie.split(/;\s*/) : [];
  for (var i = 0; i < jar.length; i++) {
    if (jar[i].indexOf('googtrans=') !== 0) continue;
    var raw;
    try { raw = decodeURIComponent(jar[i].slice(10)); } catch (e) { raw = jar[i].slice(10); }
    var m = raw.match(/^\/[A-Za-z-]+\/([A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?)$/);
    if (m) return m[1];
  }
  return null;
}

function googleIsLoaded(){
  return !!document.querySelector('.goog-te-combo, iframe.skiptranslate, #goog-gt-tt') ||
         /(^|\s)translated-(ltr|rtl)(\s|$)/.test(document.documentElement.className);
}

var googleInjected = false;
function loadGoogleTranslate(){
  if (googleInjected) return;
  googleInjected = true;
  window.googleTranslateElementInit = function(){
    try {
      new google.translate.TranslateElement({ pageLanguage:'en', autoDisplay:false }, 'googleTranslateHost');
    } catch (e) {}
  };
  var s = document.createElement('script');
  s.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
  s.async = true;
  document.head.appendChild(s);
}

/* =====================================================================
   3. APPLYING A DICTIONARY
   ===================================================================== */
function applyDict(code){
  var dict = I18N[code] || I18N.en;
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var v = dict[el.getAttribute('data-i18n')];
    if (typeof v === 'string') el.innerHTML = v;      /* trusted, static, first-party */
  });
  /* attrs: data-i18n-attr="aria-label:ui.lang;title:ui.theme" */
  document.querySelectorAll('[data-i18n-attr]').forEach(function(el){
    el.getAttribute('data-i18n-attr').split(';').forEach(function(pair){
      var bits = pair.split(':');
      if (bits.length !== 2) return;
      var v = dict[bits[1].trim()];
      if (typeof v === 'string') el.setAttribute(bits[0].trim(), v);
    });
  });
  /* Never-translate tokens: any <code> that arrived inside a dictionary
     string is a command, path or error code. Fence it off from Google, and
     tint the two diagnostic codes semantically. The tokens are on the
     never-translate list, so matching on their literal text is stable
     across every language. */
  document.querySelectorAll('[data-i18n] code').forEach(function(el){
    el.setAttribute('translate','no'); el.classList.add('notranslate');
    var t = el.textContent.trim();
    if (t === 'evidence-drift') el.classList.add('warn');
    else if (t === 'no-delivery-path') el.classList.add('err');
  });
  document.documentElement.lang = code;
  document.documentElement.dir = RTL.indexOf(code.split('-')[0]) >= 0 ? 'rtl' : 'ltr';
  syncLangUI(code);
  refreshSignOff();
  measureScrollHints();
}

function syncLangUI(code){
  var l = langByCode(code) || LANGS[0];
  var dict = I18N[isNative(code) ? code : 'en'] || I18N.en;
  var codeEl = document.getElementById('langCode');
  if (codeEl) codeEl.textContent = l.label;
  var btn = document.getElementById('langBtn');
  if (btn) btn.setAttribute('aria-label', dict['ui.lang'] + ': ' + l.name);
  document.querySelectorAll('.langopt').forEach(function(o){
    o.setAttribute('aria-selected', String(o.dataset.code === code));
  });
}

/* =====================================================================
   4. SELECTING A LANGUAGE
   ===================================================================== */
function selectLang(code){
  if (!langByCode(code)) return;
  try { localStorage.setItem(LANG_KEY, code); } catch (e) {}

  if (isNative(code)) {
    /* Google must NOT run on top of a hand-written Korean or Chinese
       page — it would translate our translation into garbage. Clear the
       cookie at every scope, then reload if Google has already injected
       itself, so its DOM rewrites are gone before our dictionary lands. */
    var hadGoogle = readGoogtrans() || googleIsLoaded();
    clearGoogtrans();
    if (hadGoogle) { location.reload(); return; }
    applyDict(code);
    closeLangPanel(true);
    return;
  }
  /* Machine tier: element.js reads the cookie at init, so the cookie is
     written first and the page reloaded into it. */
  setGoogtrans(code);
  location.reload();
}

/* =====================================================================
   5. LANGUAGE DROPDOWN
   ===================================================================== */
var langWrap  = document.getElementById('langWrap');
var langBtn   = document.getElementById('langBtn');
var langPanel = document.getElementById('langPanel');
var langList  = document.getElementById('langList');
var langInput = document.getElementById('langSearch');
var langEmpty = document.getElementById('langEmpty');
var activeOpt = null;

(function buildOptions(){
  document.querySelectorAll('.langopts').forEach(function(host){
    var tier = host.dataset.tier;
    LANGS.filter(function(l){ return l.tier === tier; }).forEach(function(l){
      var o = document.createElement('div');
      o.className = 'langopt';
      o.id = 'langopt-' + l.code;
      o.setAttribute('role','option');
      o.setAttribute('aria-selected','false');
      o.dataset.code = l.code;
      o.dataset.hay = (l.name + ' ' + l.native + ' ' + l.code).toLowerCase();
      o.innerHTML = '<span class="lo-name notranslate" translate="no"></span>' +
                    '<span class="lo-native notranslate" translate="no"></span>' +
                    '<span class="lo-code notranslate" translate="no"></span>';
      o.querySelector('.lo-name').textContent = l.name;
      o.querySelector('.lo-native').textContent = (l.native === l.name) ? '' : l.native;
      o.querySelector('.lo-code').textContent = l.code;
      o.addEventListener('click', function(){ selectLang(l.code); });
      o.addEventListener('mousemove', function(){ setActive(o); });
      host.appendChild(o);
    });
  });
})();

function visibleOpts(){
  return Array.prototype.filter.call(document.querySelectorAll('.langopt'), function(o){ return !o.hidden; });
}
function setActive(o){
  document.querySelectorAll('.langopt.active').forEach(function(x){ x.classList.remove('active'); });
  activeOpt = o || null;
  if (!o) { langInput.removeAttribute('aria-activedescendant'); return; }
  o.classList.add('active');
  langInput.setAttribute('aria-activedescendant', o.id);
  var top = o.offsetTop, bot = top + o.offsetHeight;
  if (top < langList.scrollTop) langList.scrollTop = top - 8;
  else if (bot > langList.scrollTop + langList.clientHeight) langList.scrollTop = bot - langList.clientHeight + 8;
}
function filterOpts(q){
  q = (q || '').trim().toLowerCase();
  var any = false;
  document.querySelectorAll('.langopt').forEach(function(o){
    var hit = !q || o.dataset.hay.indexOf(q) >= 0;
    o.hidden = !hit;
    if (hit) any = true;
  });
  document.querySelectorAll('.langgroup').forEach(function(g){
    g.hidden = !g.querySelector('.langopt:not([hidden])');
  });
  langEmpty.hidden = any;
  var vis = visibleOpts();
  setActive(vis.length ? vis[0] : null);
}
function openLangPanel(){
  langPanel.hidden = false;
  langWrap.classList.add('open');
  langBtn.setAttribute('aria-expanded','true');
  langInput.value = '';
  filterOpts('');
  var cur = document.querySelector('.langopt[aria-selected="true"]:not([hidden])');
  if (cur) setActive(cur);
  langInput.focus();
}
function closeLangPanel(refocus){
  if (langPanel.hidden) return;
  langPanel.hidden = true;
  langWrap.classList.remove('open');
  langBtn.setAttribute('aria-expanded','false');
  setActive(null);
  if (refocus) langBtn.focus();
}
langBtn.addEventListener('click', function(){ langPanel.hidden ? openLangPanel() : closeLangPanel(true); });
langBtn.addEventListener('keydown', function(e){
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); openLangPanel(); }
});
langInput.addEventListener('input', function(){ filterOpts(langInput.value); });
langInput.addEventListener('keydown', function(e){
  var vis = visibleOpts(), i = activeOpt ? vis.indexOf(activeOpt) : -1;
  if (e.key === 'ArrowDown')      { e.preventDefault(); if (vis.length) setActive(vis[(i + 1) % vis.length]); }
  else if (e.key === 'ArrowUp')   { e.preventDefault(); if (vis.length) setActive(vis[(i - 1 + vis.length) % vis.length]); }
  else if (e.key === 'Home')      { e.preventDefault(); if (vis.length) setActive(vis[0]); }
  else if (e.key === 'End')       { e.preventDefault(); if (vis.length) setActive(vis[vis.length - 1]); }
  else if (e.key === 'Enter')     { e.preventDefault(); if (activeOpt) selectLang(activeOpt.dataset.code); }
  else if (e.key === 'Escape')    { e.preventDefault(); closeLangPanel(true); }
  else if (e.key === 'Tab')       { closeLangPanel(false); }   /* focus leaves naturally */
});
document.addEventListener('pointerdown', function(e){
  if (!langPanel.hidden && !langWrap.contains(e.target)) closeLangPanel(false);
});

/* =====================================================================
   6. THEME
   ===================================================================== */
(function(){
  var root = document.documentElement, btn = document.getElementById('themeBtn');
  function paint(t){
    root.setAttribute('data-theme', t);
    btn.setAttribute('aria-pressed', String(t === 'light'));
  }
  paint(root.getAttribute('data-theme') === 'light' ? 'light' : 'dark');
  btn.addEventListener('click', function(){
    var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    paint(next);
    try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
  });
})();

/* =====================================================================
   7. NAV
   ===================================================================== */
(function(){
  var t = document.getElementById('navToggle'), m = document.getElementById('navMobile');
  t.addEventListener('click', function(){
    var open = m.classList.toggle('open');
    t.setAttribute('aria-expanded', String(open));
  });
  m.addEventListener('click', function(e){
    if (e.target.tagName === 'A') { m.classList.remove('open'); t.setAttribute('aria-expanded','false'); }
  });
})();

/* =====================================================================
   8. COPY + SCROLL AFFORDANCE
   The hint is shown only when the block ACTUALLY overflows, measured
   rather than guessed — a wide viewport fits the command and a badge
   telling you to scroll something that does not scroll is a lie.
   ===================================================================== */
function measureScrollHints(){
  document.querySelectorAll('[data-cmd]').forEach(function(cmd){
    var sc = cmd.querySelector('[data-scroller]'), hint = cmd.querySelector('[data-scrollhint]');
    if (!sc || !hint) return;
    hint.hidden = !(sc.scrollWidth > sc.clientWidth + 2);
  });
}
(function(){
  var status = document.getElementById('copyStatus'), timer = null;
  function announce(){
    var dict = I18N[document.documentElement.lang] || I18N.en;
    status.textContent = dict['cta.copied'] || I18N.en['cta.copied'];
    clearTimeout(timer);
    timer = setTimeout(function(){ status.textContent = ''; }, 2600);
  }
  document.querySelectorAll('[data-copy]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var text = btn.getAttribute('data-copy');
      function done(){
        btn.classList.add('copied');
        setTimeout(function(){ btn.classList.remove('copied'); }, 1800);
        announce();
      }
      function fallback(){
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly','');
        ta.style.cssText = 'position:fixed;top:0;left:-9999px;opacity:0';
        document.body.appendChild(ta);
        ta.select(); ta.setSelectionRange(0, text.length);
        try { document.execCommand('copy'); } catch (e) {}
        ta.remove(); done();
      }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, fallback);
      } else { fallback(); }
    });
  });
  var rt = null;
  window.addEventListener('resize', function(){ clearTimeout(rt); rt = setTimeout(measureScrollHints, 120); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureScrollHints);
})();

/* =====================================================================
   9. REVEAL ON SCROLL — fails visible, never blank
   ===================================================================== */
(function(){
  var els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) {
    els.forEach(function(el){ el.classList.add('in'); });
    return;
  }
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { rootMargin:'0px 0px -8% 0px', threshold:.05 });
  els.forEach(function(el){ io.observe(el); });
  /* Some contexts never deliver callbacks (hidden embed, print preview,
     headless screenshot) and .reveal starts at opacity 0. Show everything
     rather than show nothing. */
  setTimeout(function(){
    if (document.querySelector('.reveal.in')) return;
    els.forEach(function(el){ el.classList.add('in'); io.unobserve(el); });
  }, 1200);
})();

/* =====================================================================
   10. SIGN-OFF BAND
   letter-spacing is a layout property, so it is not animated. Every glyph
   gets a transform instead: no reflow, and — because the wrap is computed
   at final tracking — the line never re-wraps mid-animation.

   The band is rebuilt on every dictionary application. applyDict assigns
   innerHTML to each [data-i18n] element, which would otherwise wipe the
   spans and leave a dead, unanimated line after any language switch.
   ===================================================================== */
var SIGNOFF_KEY = 'brand.tagline';
var signoffSeen = false;

/* Never split on UTF-16 code units: that cuts Hangul syllables and any
   astral character in half. Intl.Segmenter is authoritative; Array.from
   iterates code points, which is the correct fallback. */
function graphemesOf(s){
  if (window.Intl && Intl.Segmenter){
    try {
      var seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
      return Array.from(seg.segment(s)).map(function(x){ return x.segment; });
    } catch (e) {}
  }
  return Array.from(s);
}

/* Closing punctuation must never begin a line. In a space-less script
   every glyph is its own break opportunity, so a trailing mark is glued to
   the glyph before it — this is what keeps the CJK comma and full stop
   from being orphaned onto a line of their own. */
var CJK_TAIL = /[\u3001\u3002\uFF0C\uFF0E\uFF01\uFF1F\uFF1A\uFF1B\uFF09\u300D\u300F\u3011\u300B]/;

function buildSignOff(host, text){
  var frag = document.createDocumentFragment();

  /* The accessible copy: one sentence, one text node. The glyph layer
     beside it is decorative and hidden from assistive tech, so the line is
     announced once, whole, in whichever language is live. */
  var sr = document.createElement('span');
  sr.className = 'visually-hidden';
  sr.textContent = text;
  frag.appendChild(sr);

  var vis = document.createElement('span');
  vis.setAttribute('aria-hidden', 'true');
  vis.setAttribute('translate', 'no');
  vis.className = 'notranslate';

  var units;
  if (/\s/.test(text)) {
    units = text.split(/(\s+)/);            /* Latin, Korean: break at spaces */
  } else {
    units = [];                             /* Han: break between glyphs */
    graphemesOf(text).forEach(function(g){
      if (units.length && CJK_TAIL.test(g)) units[units.length - 1] += g;
      else units.push(g);
    });
  }

  units.forEach(function(u){
    if (u === '') return;
    if (/^\s+$/.test(u)) { vis.appendChild(document.createTextNode(' ')); return; }
    var w = document.createElement('span');
    w.className = 'sw';
    graphemesOf(u).forEach(function(g){
      var sp = document.createElement('span');
      sp.className = 'sg';
      sp.textContent = g;
      w.appendChild(sp);
    });
    vis.appendChild(w);
  });

  frag.appendChild(vis);
  host.textContent = '';
  host.appendChild(frag);
}

/* Push every glyph outward from the centre of ITS OWN rendered line, so a
   wrapped line still reads as words cohering rather than one block sliding.
   The spread is clamped to the room actually left inside the band, so the
   opening frame is never clipped at any width. */
function layoutSignOff(){
  var host = document.querySelector('.sign-line');
  if (!host) return;
  var glyphs = host.querySelectorAll('.sg');
  if (!glyphs.length) return;
  var band = host.closest('.sign-off');
  var bandW = band ? band.getBoundingClientRect().width : window.innerWidth;
  var maxSpread = 0.34 * (parseFloat(getComputedStyle(host).fontSize) || 26);

  var lines = [], cur = null, lastTop = null;
  for (var i = 0; i < glyphs.length; i++){
    var r = glyphs[i].getBoundingClientRect();
    if (lastTop === null || Math.abs(r.top - lastTop) > 2){
      cur = { items: [], left: r.left, right: r.right };
      lines.push(cur);
      lastTop = r.top;
    }
    cur.items.push(glyphs[i]);
    if (r.left  < cur.left)  cur.left  = r.left;
    if (r.right > cur.right) cur.right = r.right;
  }

  lines.forEach(function(ln){
    var n = ln.items.length, maxIdx = (n - 1) / 2;
    var room = (bandW - (ln.right - ln.left)) / 2 - 10;
    var spread = maxIdx > 0 ? Math.min(maxSpread, Math.max(0, room) / maxIdx) : 0;
    ln.items.forEach(function(el, i){
      el.style.setProperty('--tx', ((i - maxIdx) * spread).toFixed(2) + 'px');
    });
  });
}

/* Called at the end of applyDict, so it re-runs on every language change. */
function refreshSignOff(){
  var host = document.querySelector('.sign-line');
  if (!host) return;
  var band = host.closest('.sign-off');
  if (!band) return;

  var target = resolveLang();
  if (!isNative(target)) return;   /* machine tier: leave the text node alone */

  var dict = I18N[target] || I18N.en;
  var text = dict[SIGNOFF_KEY];
  if (typeof text !== 'string') return;

  band.classList.remove('run');
  buildSignOff(host, text);
  layoutSignOff();
  /* Re-resolve the new sentence only if the band has already been seen;
     otherwise the observer will run it when it is scrolled to. */
  if (signoffSeen) requestAnimationFrame(function(){ band.classList.add('run'); });
}

(function(){
  var band = document.querySelector('.sign-off');
  if (!band) return;

  function reveal(){
    signoffSeen = true;
    layoutSignOff();
    band.classList.add('run');
  }

  if ('IntersectionObserver' in window){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (!e.isIntersecting) return;
        reveal();
        io.unobserve(e.target);
      });
    }, { threshold: .35 });
    io.observe(band);
  } else {
    reveal();
  }

  /* Glyph offsets are measured, so they are only right once the webfont
     is in. Geist and the Noto CJK faces all land after first paint. */
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layoutSignOff);

  var t;
  window.addEventListener('resize', function(){
    clearTimeout(t);
    t = setTimeout(layoutSignOff, 180);
  });
})();

/* =====================================================================
   11. BOOT
   ===================================================================== */
(function(){
  var lang = resolveLang();

  if (isNative(lang)) {
    clearGoogtrans();          /* idempotent; guarantees no stale twin survives */
    applyDict(lang);
  } else {
    applyDict('en');           /* Google translates FROM our English DOM */
    setGoogtrans(lang);        /* re-assert host scope on every load */
    syncLangUI(lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = RTL.indexOf(lang.split('-')[0]) >= 0 ? 'rtl' : 'ltr';
    loadGoogleTranslate();
  }
  measureScrollHints();
})();
