(function () {
  'use strict';

  var PREVIEW = !!document.querySelector('meta[name="garc-preview"]');
  var MAX_FILE = 25 * 1024 * 1024;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Preview notice */
  if (PREVIEW) {
    var bar = document.createElement('div');
    bar.className = 'preview-bar';
    bar.innerHTML = '<div class="wrap">Pré-visualização. O texto a amarelo está por preencher e os formulários ainda não enviam.</div>';
    document.body.insertBefore(bar, document.body.firstChild);
  }

  /* Mobile menu */
  var nav = document.querySelector('.nav');
  var toggle = document.querySelector('.nav-toggle');
  function setMenu(open) {
    if (!nav || !toggle) return;
    nav.setAttribute('data-open', String(open));
    toggle.setAttribute('aria-expanded', String(open));
  }
  if (nav && toggle) {
    toggle.addEventListener('click', function () {
      setMenu(nav.getAttribute('data-open') !== 'true');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('.nav-list a')) setMenu(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.getAttribute('data-open') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });
  }

  /* Calibration map: stock vs. Stage 1 */
  var map = document.querySelector('[data-map]');
  if (map) {
    var buttons = map.querySelectorAll('[data-variant]');
    var cells = map.querySelectorAll('td[data-s]');
    var readout = map.querySelector('[data-readout]');
    var bucket = function (v) { return v < 100 ? 1 : v < 180 ? 2 : v < 260 ? 3 : v < 330 ? 4 : 5; };
    var show = function (variant) {
      var max = 0;
      Array.prototype.forEach.call(cells, function (td) {
        var v = Number(variant === 't' ? td.getAttribute('data-t') : td.getAttribute('data-s'));
        td.textContent = String(v);
        td.className = 'h' + bucket(v);
        if (v > max) max = v;
      });
      if (readout) readout.textContent = max + ' Nm';
      Array.prototype.forEach.call(buttons, function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-variant') === variant));
      });
    };
    Array.prototype.forEach.call(buttons, function (b) {
      b.addEventListener('click', function () { show(b.getAttribute('data-variant')); });
    });
  }

  /* Buttons that prefill the contact subject (shop, diagnosis) */
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-subject]');
    if (!trigger) return;
    var subject = document.getElementById('f-c-assunto');
    if (subject) subject.value = trigger.getAttribute('data-subject');
    var target = document.getElementById('contacto');
    if (target) target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    var first = document.getElementById('f-c-nome');
    if (first) first.focus({ preventScroll: true });
  });

  /* Forms */
  function setStatus(el, kind, msg) {
    if (!el) return;
    el.hidden = false;
    el.setAttribute('data-kind', kind);
    el.textContent = msg;
  }

  function wireForm(form, opts) {
    var status = form.querySelector('.status');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      if (opts.validate) {
        var problem = opts.validate(form);
        if (problem) {
          setStatus(status, 'err', problem.msg);
          if (problem.focus) problem.focus.focus();
          return;
        }
      }
      if (PREVIEW) {
        setStatus(status, 'info', opts.previewMsg);
        return;
      }
      var btn = form.querySelector('button[type="submit"]');
      var label = btn ? btn.textContent : '';
      if (btn) { btn.disabled = true; btn.textContent = 'A enviar…'; }
      fetch(opts.endpoint, { method: 'POST', body: new FormData(form) })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          form.reset();
          if (opts.afterReset) opts.afterReset();
          setStatus(status, 'ok', opts.okMsg);
        })
        .catch(function () {
          setStatus(status, 'err', opts.errMsg);
        })
        .then(function () {
          if (btn) { btn.disabled = false; btn.textContent = label; }
        });
    });
  }

  /* File request form */
  var pedido = document.getElementById('form-pedido');
  function syncEmissions() {
    if (!pedido) return;
    var any = !!pedido.querySelector('input[data-emissions]:checked');
    var wrap = document.getElementById('decl-wrap');
    var box = document.getElementById('f-declaracao');
    if (!wrap || !box) return;
    wrap.hidden = !any;
    box.required = any;
    if (!any) box.checked = false;
  }
  if (pedido) {
    pedido.addEventListener('change', function (e) {
      if (e.target.matches('input[name="modulos"]')) syncEmissions();
    });
    syncEmissions();
    wireForm(pedido, {
      endpoint: '/api/pedido',
      validate: function (f) {
        if (!f.querySelector('input[name="modulos"]:checked')) {
          return { msg: 'Escolha pelo menos um módulo.', focus: f.querySelector('input[name="modulos"]') };
        }
        var input = f.querySelector('#f-ficheiro');
        var file = input && input.files && input.files[0];
        if (file && file.size > MAX_FILE) {
          return { msg: 'O ficheiro tem mais de 25 MB. Comprima-o em .zip ou contacte-nos.', focus: input };
        }
        return null;
      },
      afterReset: syncEmissions,
      previewMsg: 'Pré-visualização: o pedido foi validado, mas não foi enviado. O envio fica ativo quando o site estiver no ar.',
      okMsg: 'Pedido enviado. Vai receber a resposta por email.',
      errMsg: 'Não foi possível enviar o pedido. Verifique a ligação e tente de novo; se o erro continuar, contacte-nos por telefone.'
    });
  }

  /* Contact form (footer) */
  var contacto = document.getElementById('form-contacto');
  if (contacto) {
    wireForm(contacto, {
      endpoint: '/api/contacto',
      previewMsg: 'Pré-visualização: a mensagem foi validada, mas não foi enviada.',
      okMsg: 'Mensagem enviada. Respondemos por email.',
      errMsg: 'Não foi possível enviar a mensagem. Tente de novo ou contacte-nos por telefone.'
    });
  }
})();
