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