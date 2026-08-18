/* ==========================================================================
   Happy Grill — the basket
   --------------------------------------------------------------------------
   One store, shared by the menu (index.html) and the basket page (cart.html),
   so the two can never disagree about what has been ordered. It lives in
   localStorage: there is no server behind this site, the order is finally sent
   as a WhatsApp message, and a basket that survives a refresh — or a walk from
   the menu to the basket and back — is the whole point.

   Everything that comes back out of storage is treated as untrusted. It is
   text the visitor can edit, it may have been written by an older version of
   this file, and one bad line must not take the basket down with it, so a line
   that doesn't pass `clean()` is dropped rather than repaired.

   Each line carries both languages. Nothing here knows which one is on screen —
   the pages ask for the one they need, and switching language never has to
   touch stored data.
   ========================================================================== */
(function () {
  'use strict';

  var KEY   = 'hg-cart';
  var PHONE = '972545251210';

  var MAX_QTY   = 99;   // a per-line ceiling, so a stuck ＋ can't reach 10,000
  var MAX_LINES = 60;   // and a ceiling on distinct lines, for the same reason

  var listeners = [];

  /* ---------------- Storage ---------------- */

  /* "Without onion, without pickles" and "plus a 100g patty" are lists of
     names, so they are cleaned the same way as everything else: strings only,
     capped in count and in length, and anything else dropped. */
  function strList(v) {
    if (Object.prototype.toString.call(v) !== '[object Array]') return [];
    var out = [];
    for (var i = 0; i < v.length && out.length < 16; i++) {
      if (typeof v[i] === 'string' && v[i]) out.push(v[i].slice(0, 60));
    }
    return out;
  }

  function clean(line) {
    if (!line || typeof line !== 'object') return null;

    var price = Number(line.price);
    var qty   = Math.round(Number(line.qty));

    if (typeof line.id !== 'string' || !line.id) return null;
    if (!isFinite(price) || price < 0) return null;
    if (!isFinite(qty) || qty < 1) return null;

    return {
      id:    line.id,
      ar:    String(line.ar || ''),
      he:    String(line.he || ''),
      optAr: String(line.optAr || ''),
      optHe: String(line.optHe || ''),
      noAr:  strList(line.noAr),
      noHe:  strList(line.noHe),
      addAr: strList(line.addAr),
      addHe: strList(line.addHe),
      price: price,
      qty:   Math.min(qty, MAX_QTY),
      img:   String(line.img || '')
    };
  }

  function read() {
    var raw;
    try { raw = localStorage.getItem(KEY); } catch (e) { return []; }
    if (!raw) return [];

    var parsed;
    try { parsed = JSON.parse(raw); } catch (e) { return []; }
    if (Object.prototype.toString.call(parsed) !== '[object Array]') return [];

    var out = [];
    for (var i = 0; i < parsed.length && out.length < MAX_LINES; i++) {
      var line = clean(parsed[i]);
      if (line) out.push(line);
    }
    return out;
  }

  /* Private storage, a full disk or a browser that refuses to keep anything at
     all are all the same answer here: the basket still works for this page
     view, it just won't outlive it. Nothing is worth breaking the page over. */
  function write(items) {
    try { localStorage.setItem(KEY, JSON.stringify(items)); } catch (e) {}
    emit();
  }

  function emit() {
    var snapshot = read();
    for (var i = 0; i < listeners.length; i++) {
      try { listeners[i](snapshot); } catch (e) {}
    }
  }

  /* ---------------- Reading ---------------- */

  function count() {
    var items = read(), n = 0;
    for (var i = 0; i < items.length; i++) n += items[i].qty;
    return n;
  }

  function total() {
    var items = read(), sum = 0;
    for (var i = 0; i < items.length; i++) sum += items[i].price * items[i].qty;
    return sum;
  }

  /* ---------------- Writing ---------------- */

  /* Adding the same dish in the same size again is not a second line — it is
     the first line, one louder. */
  function add(line, qty) {
    var fresh = clean({
      id: line.id, ar: line.ar, he: line.he,
      optAr: line.optAr, optHe: line.optHe,
      noAr: line.noAr, noHe: line.noHe,
      addAr: line.addAr, addHe: line.addHe,
      price: line.price, img: line.img,
      qty: qty || 1
    });
    if (!fresh) return false;

    var items = read();
    for (var i = 0; i < items.length; i++) {
      if (items[i].id === fresh.id) {
        items[i].qty   = Math.min(items[i].qty + fresh.qty, MAX_QTY);
        items[i].price = fresh.price;    // a price edited in the menu wins
        write(items);
        return true;
      }
    }

    if (items.length >= MAX_LINES) return false;
    items.push(fresh);
    write(items);
    return true;
  }

  function setQty(id, qty) {
    qty = Math.round(Number(qty));
    if (!isFinite(qty)) return;
    if (qty < 1) return remove(id);

    var items = read();
    for (var i = 0; i < items.length; i++) {
      if (items[i].id === id) {
        items[i].qty = Math.min(qty, MAX_QTY);
        write(items);
        return;
      }
    }
  }

  function remove(id) {
    var items = read(), out = [];
    for (var i = 0; i < items.length; i++) {
      if (items[i].id !== id) out.push(items[i]);
    }
    write(out);
  }

  function clear() { write([]); }

  /* ---------------- Change notification ----------------
     Same page: every write emits. Other tabs: the storage event, which only
     fires in the tabs that did not do the writing — exactly what is wanted, so
     a basket open in a second tab keeps up without echoing its own changes. */
  function subscribe(fn) {
    if (typeof fn !== 'function') return;
    listeners.push(fn);
    fn(read());
  }

  window.addEventListener('storage', function (e) {
    if (e.key === KEY || e.key === null) emit();
  });

  /* ---------------- Presentation helpers ---------------- */

  /* Prices on this menu are whole shekels; a total only grows a decimal if
     something on the menu ever gains one. */
  function money(n) {
    var v = Math.round(n * 100) / 100;
    return v % 1 === 0 ? String(v) : v.toFixed(2);
  }

  function name(line, lang) {
    return (lang === 'he' ? line.he : line.ar) || line.ar || line.he || '';
  }

  function opt(line, lang) {
    return (lang === 'he' ? line.optHe : line.optAr) || '';
  }

  /* What was taken out, and what was added on, in one language */
  function removed(line, lang) {
    return (lang === 'he' ? line.noHe : line.noAr) || [];
  }

  function extras(line, lang) {
    return (lang === 'he' ? line.addHe : line.addAr) || [];
  }

  /* ---------------- Who it's for ----------------
     The name, and whether it is being collected or delivered, kept beside the
     basket rather than inside it: they outlive any single line, and a visitor
     who steps away mid-order should not have to type their name again.

     This is the visitor's own name and address, held on their own device and
     sent only in the message they choose to send. Nothing here goes anywhere
     on its own. */
  var DKEY = 'hg-order';

  function details() {
    var raw, parsed;
    try { raw = localStorage.getItem(DKEY); } catch (e) { return blank(); }
    if (!raw) return blank();
    try { parsed = JSON.parse(raw); } catch (e) { return blank(); }
    if (!parsed || typeof parsed !== 'object') return blank();

    return {
      name:    String(parsed.name || '').slice(0, 80),
      mode:    parsed.mode === 'delivery' ? 'delivery' : 'pickup',
      address: String(parsed.address || '').slice(0, 200)
    };
  }

  function blank() { return { name: '', mode: 'pickup', address: '' }; }

  function setDetails(next) {
    var d = {
      name:    String(next.name || '').slice(0, 80),
      mode:    next.mode === 'delivery' ? 'delivery' : 'pickup',
      address: String(next.address || '').slice(0, 200)
    };
    try { localStorage.setItem(DKEY, JSON.stringify(d)); } catch (e) {}
    return d;
  }

  /* Every cart button on a page carries [data-cart-badge]; this keeps all of
     them counting, on this tab and on any other. A basket of nothing shows no
     badge at all rather than a zero.

     The badge pops each time the number actually changes — the count is the
     only confirmation a second tab ever gets, and a digit quietly swapping
     itself out is easy to miss. The first paint is exempt: arriving at a page
     is not a change. */
  var lastCount = null;

  function wireBadges() {
    subscribe(function () {
      var n = count();
      var changed = lastCount !== null && lastCount !== n;
      lastCount = n;

      var badges = document.querySelectorAll('[data-cart-badge]');
      for (var i = 0; i < badges.length; i++) {
        badges[i].textContent = n > MAX_QTY ? MAX_QTY + '+' : String(n);
        badges[i].hidden = n === 0;

        if (changed && n > 0) {
          badges[i].classList.remove('is-bump');
          void badges[i].offsetWidth;      // restart the animation, don't queue it
          badges[i].classList.add('is-bump');
        }
      }

      var links = document.querySelectorAll('[data-cart-link]');
      for (var j = 0; j < links.length; j++) {
        links[j].classList.toggle('has-items', n > 0);
      }
    });
  }

  window.HGCart = {
    PHONE:   PHONE,
    MAX_QTY: MAX_QTY,
    items:   read,
    count:   count,
    total:   total,
    add:     add,
    setQty:  setQty,
    remove:  remove,
    clear:   clear,
    subscribe: subscribe,
    money:   money,
    name:    name,
    opt:     opt,
    removed: removed,
    extras:  extras,
    details:    details,
    setDetails: setDetails,
    wireBadges: wireBadges
  };
})();
