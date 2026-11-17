(function () {
  'use strict';

  var PREVIEW = !!document.querySelector('meta[name="garc-preview"]');
  var DEMO = PREVIEW && !!document.getElementById('catalogo');

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

  /* Página Serviços: um tema de cada vez, com endereço próprio (ex.: /servicos#ecu) e Anterior/Seguinte.
     Sem JavaScript, os temas ficam todos seguidos e a lista serve de índice. */
  var temas = document.querySelector('[data-temas]');
  var passos = temas && temas.querySelector('[data-temas-passos]');
  if (temas && passos) {
    var paineis = Array.prototype.slice.call(temas.querySelectorAll('[data-tema]'));
    var ligacoes = Array.prototype.slice.call(temas.querySelectorAll('[data-tema-link]'));
    var anterior = passos.querySelector('[data-anterior]');
    var seguinte = passos.querySelector('[data-seguinte]');
    var contador = passos.querySelector('[data-contador]');
    var ids = paineis.map(function (p) { return p.id; });
    var atual = -1;

    var indiceDe = function (hash) {
      var id = (hash || '').replace(/^#/, '');
      try { id = decodeURIComponent(id); } catch (err) { /* endereço mal formado: não é nenhum tema */ }
      return ids.indexOf(id);
    };

    // Sem tema antes ou depois, o botão fica sem destino e escondido (ver .temas-passos no CSS).
    var ligarPasso = function (el, i, texto) {
      if (i < 0 || i >= ids.length) {
        el.removeAttribute('href');
        el.removeAttribute('aria-label');
        el.removeAttribute('title');
        return;
      }
      var nome = ligacoes[i] ? ligacoes[i].textContent : ids[i];
      el.setAttribute('href', '#' + ids[i]);
      el.setAttribute('aria-label', texto + ': ' + nome);
      el.title = nome;
    };

    var mostrar = function (i, levar) {
      atual = i;
      paineis.forEach(function (p, j) { p.hidden = j !== i; });
      ligacoes.forEach(function (a, j) {
        if (j === i) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      });
      contador.textContent = (i + 1) + ' de ' + ids.length;
      ligarPasso(anterior, i - 1, 'Anterior');
      ligarPasso(seguinte, i + 1, 'Seguinte');
      if (!levar) return;
      // Leva ao início do tema quando ficou fora de vista (ex.: «Seguinte» no fim de um tema comprido)
      // e passa-lhe o foco, para os leitores de ecrã lerem o título.
      var p = paineis[i];
      var margem = parseFloat(window.getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
      var topo = p.getBoundingClientRect().top;
      if (topo < margem || topo > window.innerHeight * 0.6) p.scrollIntoView();
      var titulo = p.querySelector('h2');
      if (titulo) titulo.focus({ preventScroll: true });
    };

    temas.classList.add('temas-ativos');
    passos.hidden = false;
    var inicial = indiceDe(window.location.hash);
    mostrar(inicial < 0 ? 0 : inicial, false);
    if (inicial >= 0) {
      // Endereço com tema: os outros temas acabaram de ser escondidos, por isso leva-se ao tema pedido.
      window.requestAnimationFrame(function () { paineis[inicial].scrollIntoView(); });
    }

    temas.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
      var i = indiceDe(a.getAttribute('href'));
      if (i < 0) return;
      e.preventDefault();
      if (i !== atual && window.history.pushState) window.history.pushState(null, '', '#' + ids[i]);
      mostrar(i, true);
    });

    // Retroceder e Avançar do browser, ou outro tema escrito no endereço
    var seguirEndereco = function () {
      var i = indiceDe(window.location.hash);
      if (i >= 0 && i !== atual) mostrar(i, true);
      else if (!window.location.hash && atual !== 0) mostrar(0, false);
    };
    window.addEventListener('popstate', seguirEndereco);
    window.addEventListener('hashchange', seguirEndereco);
  }

  /* Página Contacto: assunto vindo de outra página (contacto?assunto=…, ex.: «Pedir diagnóstico») */
  var assunto = document.getElementById('f-c-assunto');
  if (assunto && window.URLSearchParams) {
    var pedido = new URLSearchParams(window.location.search).get('assunto');
    if (pedido) assunto.value = pedido.slice(0, 150);
  }

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

  /* Formulário da página Contacto */
  var contacto = document.getElementById('form-contacto');
  if (contacto) {
    var alternativa = contacto.getAttribute('data-email');
    wireForm(contacto, {
      endpoint: '/api/contacto',
      previewMsg: 'Pré-visualização: a mensagem foi validada, mas não foi enviada.',
      okMsg: 'Mensagem enviada. Respondemos por email.',
      errMsg: 'Não foi possível enviar a mensagem. Tente de novo mais tarde' +
        (alternativa ? ' ou escreva para ' + alternativa : '') + '.'
    });
  }
})();
