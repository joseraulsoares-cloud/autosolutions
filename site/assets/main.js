(function () {
  'use strict';

  var PREVIEW = !!document.querySelector('meta[name="garc-preview"]');
  var DEMO = PREVIEW && !!document.getElementById('catalogo');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Preview notice */
  if (PREVIEW) {
    var bar = document.createElement('div');
    bar.className = 'preview-bar';
    bar.innerHTML = DEMO
      ? '<div class="wrap">Demonstração com dados de exemplo: nada é gravado. Para entrar, use qualquer email e qualquer código de 6 dígitos.</div>'
      : '<div class="wrap">Pré-visualização. O texto a amarelo está por preencher e os formulários ainda não enviam.</div>';
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
