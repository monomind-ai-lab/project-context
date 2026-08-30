/* =====================================================================
   10. TABS
   Real tab semantics: roving tabindex, arrow/Home/End navigation, and the
   selection mirrored into the URL hash so a tab is linkable and survives a
   reload. The hash values (`#coding`, `#collaborative`) deliberately do NOT
   match any element id — a matching id would make the browser jump-scroll
   to the panel on load, which is not what a linked tab should do.
   ===================================================================== */
(function(){
  var tablist = document.getElementById('ucTabs');
  if (!tablist) return;
  var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));

  function select(tab, focus, writeHash){
    tabs.forEach(function(t){
      var on = (t === tab);
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      var p = document.getElementById(t.getAttribute('aria-controls'));
      if (!p) return;
      p.hidden = !on;
      /* A .reveal inside a display:none panel never intersects, so the
         observer would leave it at opacity 0 on first show. */
      if (on) p.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('in'); });
    });
    if (focus) tab.focus();
    if (writeHash) {
      var h = '#' + tab.dataset.hash;
      if (location.hash !== h) {
        try { history.replaceState(null, '', h); } catch (e) { location.hash = h; }
      }
    }
    measureScrollHints();
  }

  tabs.forEach(function(t){
    t.addEventListener('click', function(){ select(t, false, true); });
    t.addEventListener('keydown', function(e){
      var i = tabs.indexOf(t), next = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown')     next = tabs[(i + 1) % tabs.length];
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp')   next = tabs[(i - 1 + tabs.length) % tabs.length];
      else if (e.key === 'Home')                               next = tabs[0];
      else if (e.key === 'End')                                next = tabs[tabs.length - 1];
      else return;
      e.preventDefault();
      select(next, true, true);
    });
  });

  function fromHash(){
    var h = (location.hash || '').replace(/^#/, '');
    for (var i = 0; i < tabs.length; i++) if (tabs[i].dataset.hash === h) return tabs[i];
    return null;
  }
  window.addEventListener('hashchange', function(){
    var t = fromHash();
    if (t) select(t, false, false);
  });
  select(fromHash() || tabs[0], false, false);
})();
