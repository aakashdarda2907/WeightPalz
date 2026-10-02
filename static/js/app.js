(function () {
  'use strict';

  function $(sel) { return document.querySelector(sel); }

  function toast(message, kind) {
    var box = $('.toasts');
    if (!box) {
      box = document.createElement('div');
      box.className = 'toasts';
      box.setAttribute('role', 'status');
      document.body.appendChild(box);
    }
    var t = document.createElement('div');
    t.className = 'toast ' + (kind || 'success');
    t.textContent = message;
    box.appendChild(t);
    setTimeout(function () { t.remove(); }, 4500);
  }

  // Meal buttons: update the card instantly, before the server replies
  function applyMeal(form, answer) {
    var card = form.closest('.meal');
    var yes = answer === 'yes';
    card.classList.toggle('yes', yes);
    card.classList.toggle('no', !yes);
    card.querySelector('.y').classList.toggle('on', yes);
    card.querySelector('.n').classList.toggle('on', !yes);
    card.querySelector('.mark').textContent = yes ? '✓' : '✕';
    card.classList.remove('pop');
    void card.offsetWidth;            // restart the animation
    card.classList.add('pop');
    var count = $('#yes-count');
    if (count) count.textContent = document.querySelectorAll('.meal.yes').length + '/4';
  }

  function setText(sel, value) {
    var el = $(sel);
    if (el) el.textContent = value;
  }

  var handlers = {
    meal: function (form, d) {
      setText('#yes-count', d.yes_count + '/4');
      setText('#streak-num', d.streak);
    },

    weight: function (form, d) {
      var ring = $('#ring-prog');
      if (ring) ring.style.strokeDasharray = d.progress + ' 100';
      var box = $('#ring-box');
      if (box) box.setAttribute('aria-valuenow', d.progress);
      setText('#ring-pct', d.progress + '%');
      setText('#target-val', d.target);
      setText('#now-val', d.current);
      setText('#motive', d.motivation);
      setText('#to-go', d.to_go + ' kg');
      setText('#since-start', (d.since_start > 0 ? '+' : '') + d.since_start + ' kg');
      setText('#streak-num', d.streak);
      var banner = $('#weight-banner');
      if (banner) banner.remove();
      setText('#weight-btn', 'Update');
      toast(d.message);
    },

    cheer: function (form, d) {
      var b = form.querySelector('button');
      b.className = 'sm on';
      b.type = 'button';
      b.disabled = true;
      b.textContent = 'Cheered ✓';
      toast(d.message);
    }
  };

  document.addEventListener('submit', function (e) {
    var form = e.target;
    var kind = form.dataset ? form.dataset.ajax : null;
    if (!kind || !window.fetch || !handlers[kind]) return;   // fall back to a normal submit

    e.preventDefault();
    var sub = e.submitter;
    var fd = new FormData(form);
    if (sub && sub.name && !fd.has(sub.name)) fd.append(sub.name, sub.value);

    if (kind === 'meal' && sub) applyMeal(form, sub.value);
    if (kind === 'weight' && sub) sub.disabled = true;

    fetch(form.action, {
      method: 'POST',
      body: fd,
      headers: { 'X-Requested-With': 'fetch' },
      credentials: 'same-origin'
    }).then(function (res) {
      if (res.redirected) { window.location.href = res.url; return null; }   // session expired
      return res.json().then(function (d) { return { ok: res.ok && d.ok, d: d }; });
    }).then(function (r) {
      if (!r) return;
      if (!r.ok) {
        toast(r.d.message || 'Could not save. Try again.', 'error');
        if (kind === 'meal') setTimeout(function () { window.location.reload(); }, 900);
        return;
      }
      handlers[kind](form, r.d);
    }).catch(function () {
      toast('No connection. Try again.', 'error');
      if (kind === 'meal') setTimeout(function () { window.location.reload(); }, 900);
    }).then(function () {
      if (kind === 'weight' && sub) sub.disabled = false;
    });
  });
})();
// ---------------------------------------------------------------------------
// Install as app: banner, steps sheet, native install prompt
// ---------------------------------------------------------------------------
(function () {
  'use strict';

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  var FLAG = 'wp-installed';
  var banner = document.getElementById('install-banner');
  var sheet = document.getElementById('install-sheet');
  var deferred = null;
  var standalone = (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
                   window.navigator.standalone === true;

  function installed() {
    try { return localStorage.getItem(FLAG) === '1'; } catch (e) { return false; }
  }
  function setInstalled(v) {
    try {
      if (v) localStorage.setItem(FLAG, '1'); else localStorage.removeItem(FLAG);
    } catch (e) {}
  }
  if (standalone) setInstalled(true);

  function refresh() {
    if (banner) banner.hidden = standalone || installed();
    document.querySelectorAll('[data-if-standalone]').forEach(function (el) { el.hidden = !standalone; });
    document.querySelectorAll('[data-if-browser]').forEach(function (el) { el.hidden = standalone; });
  }

  // ----- Work out which device and browser this is -----
  function detect() {
    var ua = navigator.userAgent || '';
    var ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    var safari = /safari/i.test(ua) && !/chrome|crios|fxios|edgios|android|opr|edg/i.test(ua);
    if (ios) return safari ? 'ios-safari' : 'ios-other';
    if (/android/i.test(ua)) {
      if (/samsungbrowser/i.test(ua)) return 'samsung';
      if (/firefox/i.test(ua)) return 'android-firefox';
      return 'android-chrome';
    }
    if (safari) return 'mac-safari';
    if (/firefox/i.test(ua)) return 'desktop-firefox';
    return 'desktop-chromium';
  }

  var INFO = {
    'ios-safari': {
      label: 'iPhone or iPad · Safari',
      steps: [
        'Tap the <b>Share</b> button (the square with an arrow) at the bottom of Safari.',
        'Scroll down and tap <b>Add to Home Screen</b>.',
        'Tap <b>Add</b> in the top right corner.',
        'Open WeightPalz from your home screen.'
      ]
    },
    'ios-other': {
      label: 'iPhone or iPad · this browser',
      steps: [
        'Installing works best in <b>Safari</b>. Open this page in Safari first.',
        'Tap the <b>Share</b> button, then <b>Add to Home Screen</b>.',
        'Tap <b>Add</b> in the top right corner.'
      ]
    },
    'samsung': {
      label: 'Samsung Internet',
      steps: [
        'Tap the <b>menu</b> button (three lines) at the bottom right.',
        'Tap <b>Add page to</b>, then <b>Home screen</b>.',
        'Tap <b>Add</b> to confirm.'
      ]
    },
    'android-chrome': {
      label: 'Android · Chrome',
      steps: [
        'Tap the <b>menu</b> button (three dots) at the top right.',
        'Tap <b>Install app</b> or <b>Add to Home screen</b>.',
        'Tap <b>Install</b> to confirm.'
      ]
    },
    'android-firefox': {
      label: 'Android · Firefox',
      steps: [
        'Tap the <b>menu</b> button (three dots).',
        'Tap <b>Install</b>.',
        'Tap <b>Add</b> to confirm.'
      ]
    },
    'mac-safari': {
      label: 'Mac · Safari',
      steps: [
        'In the menu bar, choose <b>File</b>, then <b>Add to Dock</b>.',
        'Click <b>Add</b>.'
      ]
    },
    'desktop-chromium': {
      label: 'Computer · Chrome or Edge',
      steps: [
        'Click the <b>install icon</b> at the right end of the address bar.',
        'Click <b>Install</b>.',
        'No icon? Open the browser menu and choose <b>Install WeightPalz</b>.'
      ]
    },
    'desktop-firefox': {
      label: 'Computer · Firefox',
      steps: [
        'Firefox cannot install web apps on computers.',
        'Open this site in <b>Chrome</b> or <b>Edge</b> to install it.'
      ]
    }
  };

  // ----- Steps sheet -----
  function openSheet() {
    if (!sheet) return;
    var info = INFO[detect()];
    document.getElementById('sheet-device').textContent = info.label;
    document.getElementById('sheet-steps').innerHTML =
      info.steps.map(function (s) { return '<li><span>' + s + '</span></li>'; }).join('');
    sheet.hidden = false;
    document.body.style.overflow = 'hidden';
    var close = sheet.querySelector('.sheet-head [data-sheet-close]');
    if (close) close.focus();
  }

  function closeSheet() {
    if (!sheet) return;
    sheet.hidden = true;
    document.body.style.overflow = '';
  }

  // ----- Install: use the browser's own dialog when we can, otherwise show steps -----
  function startInstall() {
    if (deferred) {
      var d = deferred;
      deferred = null;
      d.prompt();
      d.userChoice.then(function (choice) {
        if (choice.outcome === 'accepted') { setInstalled(true); refresh(); }
      });
      return;
    }
    openSheet();
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
  });

  window.addEventListener('appinstalled', function () {
    deferred = null;
    setInstalled(true);
    closeSheet();
    refresh();
  });

  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-install-open]')) { startInstall(); return; }

    if (e.target.closest('[data-install-done]')) {
      setInstalled(true);
      closeSheet();
      refresh();
      return;
    }

    if (e.target.closest('[data-sheet-close]')) { closeSheet(); return; }

    var reset = e.target.closest('[data-install-reset]');
    if (reset) {
      setInstalled(false);
      document.documentElement.classList.remove('no-ib');
      refresh();
      reset.textContent = 'The banner will show again ✓';
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSheet();
  });

  // Open the Profile instructions that match this device
  var me = detect();
  document.querySelectorAll('details[data-platform]').forEach(function (d) {
    if (d.dataset.platform.split(' ').indexOf(me) !== -1) d.open = true;
  });

  refresh();
})();