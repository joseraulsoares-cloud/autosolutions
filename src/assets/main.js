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

  /* Página inicial: o sinal da rede CAN passa no ecrã, como num osciloscópio.
     data-bits traz a sequência real (0 = dominante, 1 = recessivo); com movimento reduzido, fica parado. */
  var tela = document.querySelector('.sinal-tela');
  if (tela && tela.getContext) {
    var bits = tela.getAttribute('data-bits') || '1';
    var ctx = tela.getContext('2d');
    var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var cores = getComputedStyle(tela.closest('.sinal'));
    var corH = cores.getPropertyValue('--sinal-h').trim() || '#8AB0FF';
    var corL = cores.getPropertyValue('--sinal-l').trim() || '#D7DCE2';
    var largura = 0, altura = 0, bitPx = 12, desloc = 0, ultimo = null, aCorrer = false, pedido = 0;
    var BITS_POR_MS = 0.009;

    var medir = function () {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      largura = tela.clientWidth; altura = tela.clientHeight;
      tela.width = Math.round(largura * dpr); tela.height = Math.round(altura * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      bitPx = Math.max(7, Math.min(14, largura / 100));
    };
    var dominante = function (i) {
      var n = bits.length;
      return bits.charAt(((i % n) + n) % n) === '0';
    };
    var tracar = function (yRec, yDom, cor) {
      var i = Math.floor(desloc / bitPx), x = i * bitPx - desloc, rampa = Math.max(1.5, bitPx * 0.12);
      var anterior = dominante(i - 1) ? yDom : yRec;
      ctx.beginPath();
      ctx.moveTo(x - 1, anterior);
      for (; x < largura + bitPx; i++, x += bitPx) {
        var y = dominante(i) ? yDom : yRec;
        if (y !== anterior) {
          var excesso = (y - anterior) * 0.12;
          ctx.lineTo(x, anterior);
          ctx.lineTo(x + rampa, y + excesso);
          ctx.lineTo(x + rampa * 2.2, y - excesso * 0.4);
          ctx.lineTo(x + rampa * 3.2, y);
        }
        ctx.lineTo(x + bitPx, y);
        anterior = y;
      }
      ctx.strokeStyle = cor;
      ctx.lineJoin = 'round';
      ctx.shadowColor = cor; ctx.shadowBlur = 14; ctx.lineWidth = 2.4; ctx.globalAlpha = 0.5; ctx.stroke();
      ctx.shadowBlur = 0; ctx.lineWidth = 1.6; ctx.globalAlpha = 1; ctx.stroke();
    };
    var desenhar = function () {
      ctx.clearRect(0, 0, largura, altura);
      var meio = altura / 2, amplitude = altura / 4;
      tracar(meio, meio - amplitude, corH);
      tracar(meio, meio + amplitude, corL);
    };
    var passo = function (t) {
      if (!aCorrer) return;
      if (ultimo !== null) desloc += Math.min(t - ultimo, 50) * BITS_POR_MS * bitPx;
      ultimo = t;
      desenhar();
      pedido = requestAnimationFrame(passo);
    };
    var correr = function (sim) {
      if (calmo || sim === aCorrer) return;
      aCorrer = sim; ultimo = null;
      if (sim) pedido = requestAnimationFrame(passo); else cancelAnimationFrame(pedido);
    };

    medir();
    desloc = bitPx * 150;
    desenhar();
    window.addEventListener('resize', function () { medir(); desenhar(); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entradas) { correr(entradas[0].isIntersecting); }).observe(tela);
    } else {
      correr(true);
    }
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
