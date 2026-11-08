/* Funções comuns da área de cliente e do painel de administração. */
(function () {
  'use strict';

  var PREVIEW = !!document.querySelector('meta[name="garc-preview"]');
  var catEl = document.getElementById('catalogo');
  var CAT = { modulos: {}, maxMb: 25, urls: {} };
  try { if (catEl) CAT = JSON.parse(catEl.textContent); } catch (e) { /* catálogo em falta */ }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function tokens(n) {
    n = Number(n) || 0;
    return n + (Math.abs(n) === 1 ? ' token' : ' tokens');
  }

  function sinal(n) {
    n = Number(n) || 0;
    return (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n);
  }

  // As datas chegam em UTC no formato "AAAA-MM-DD HH:MM:SS".
  function data(valor) {
    if (!valor) return '';
    var d = new Date(String(valor).replace(' ', 'T') + 'Z');
    if (isNaN(d)) return String(valor);
    return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ', ' +
      d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
  }

  function tamanho(bytes) {
    bytes = Number(bytes) || 0;
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1).replace('.', ',') + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  var ESTADOS = {
    a_aguardar_ficheiro: ['À espera do ficheiro', 'warn'],
    recebido: ['Recebido', 'info'],
    em_curso: ['Em curso', 'accent'],
    a_aguardar_saldo: ['Falta saldo', 'warn'],
    concluido: ['Concluído', 'ok'],
    recusado: ['Recusado', 'err'],
    cancelado: ['Cancelado', 'muted'],
    pendente: ['Por aprovar', 'warn'],
    aprovada: ['Aprovada', 'ok'],
    recusada: ['Recusada', 'err'],
    suspensa: ['Suspensa', 'muted']
  };

  function pill(estado) {
    var e = ESTADOS[estado] || [estado, 'muted'];
    return '<span class="pill" data-kind="' + e[1] + '">' + esc(e[0]) + '</span>';
  }

  function nomeModulo(k) {
    var m = CAT.modulos[k];
    return m ? m.nome : k;
  }

  var ENTREGAS = { portal: 'Área de cliente', email: 'Email com anexo', whatsapp: 'WhatsApp' };

  function movimentoTexto(m) {
    switch (m.tipo) {
      case 'carregamento': return 'Carregamento' + (m.referencia ? ' (' + m.referencia + ')' : '');
      case 'pedido': return 'Pedido n.º ' + m.pedido_id + (m.referencia ? ' (' + m.referencia + ')' : '');
      case 'devolucao': return 'Devolução do pedido n.º ' + m.pedido_id + (m.referencia ? ' (' + m.referencia + ')' : '');
      default: return 'Acerto' + (m.referencia ? ' (' + m.referencia + ')' : '');
    }
  }

  function erroDe(status, corpo) {
    var err = new Error((corpo && corpo.erro) || 'Erro ' + status + '. Tente de novo.');
    err.status = status;
    err.body = corpo;
    return err;
  }

  function api(caminho, opcoes) {
    opcoes = opcoes || {};
    if (PREVIEW && window.GARC_DEMO) return window.GARC_DEMO(caminho, opcoes);
    var init = { method: opcoes.method || 'GET', headers: { Accept: 'application/json' }, credentials: 'same-origin' };
    if (opcoes.json !== undefined) {
      init.method = 'POST';
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opcoes.json);
    }
    return fetch(caminho, init).then(function (r) {
      return r.text().then(function (t) {
        var corpo = null;
        try { corpo = t ? JSON.parse(t) : null; } catch (e) { corpo = null; }
        if (!r.ok) throw erroDe(r.status, corpo);
        return corpo;
      });
    }, function () {
      throw new Error('Sem ligação ao servidor. Verifique a internet e tente de novo.');
    });
  }

  // Envio de ficheiro com barra de progresso (POST multipart, campo "ficheiro").
  function upload(caminho, ficheiro, progresso) {
    if (PREVIEW && window.GARC_DEMO_UPLOAD) return window.GARC_DEMO_UPLOAD(caminho, ficheiro, progresso);
    return new Promise(function (resolve, reject) {
      var x = new XMLHttpRequest();
      var dados = new FormData();
      dados.append('ficheiro', ficheiro, ficheiro.name);
      x.open('POST', caminho);
      x.setRequestHeader('Accept', 'application/json');
      x.upload.onprogress = function (e) {
        if (e.lengthComputable && progresso) progresso(e.loaded / e.total);
      };
      x.onload = function () {
        var corpo = null;
        try { corpo = JSON.parse(x.responseText); } catch (e) { corpo = null; }
        if (x.status >= 200 && x.status < 300) resolve(corpo);
        else reject(erroDe(x.status, corpo || { erro: 'O envio do ficheiro falhou (erro ' + x.status + ').' }));
      };
      x.onerror = function () {
        reject(new Error('O envio do ficheiro falhou. Verifique a ligação e tente de novo.'));
      };
      x.send(dados);
    });
  }

  function status(el, tipo, msg) {
    if (!el) return;
    el.hidden = !msg;
    el.setAttribute('data-kind', tipo);
    el.textContent = msg || '';
  }

  // Botão que pede um segundo clique para confirmar.
  function confirmar(btn, textoConfirmar, acao) {
    if (btn.getAttribute('data-confirmar') === '1') {
      btn.removeAttribute('data-confirmar');
      clearTimeout(btn._garcT);
      btn.textContent = btn._garcTexto;
      acao();
      return;
    }
    btn._garcTexto = btn.textContent;
    btn.setAttribute('data-confirmar', '1');
    btn.textContent = textoConfirmar;
    btn._garcT = setTimeout(function () {
      btn.removeAttribute('data-confirmar');
      btn.textContent = btn._garcTexto;
    }, 4000);
  }

  // Entrada por código: email, depois os 6 dígitos.
  function ligarEntrada(aoEntrar) {
    var fe = document.getElementById('f-entrar-email');
    var fc = document.getElementById('f-entrar-codigo');
    if (!fe || !fc) return;
    var email = '';

    function pedirCodigo() {
      fc.hidden = false;
      fe.hidden = true;
      fc.querySelector('[data-email-mostra]').textContent = email;
      status(fc.querySelector('.status'), 'info', '');
      fc.elements.codigo.value = '';
      fc.elements.codigo.focus();
    }

    fe.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!fe.checkValidity()) { fe.reportValidity(); return; }
      email = fe.elements.email.value.trim();
      var btn = fe.querySelector('button[type="submit"]');
      btn.disabled = true;
      status(fe.querySelector('.status'), 'info', '');
      api('/api/entrar/codigo', { json: { email: email } })
        .then(pedirCodigo)
        .catch(function (err) { status(fe.querySelector('.status'), 'err', err.message); })
        .then(function () { btn.disabled = false; });
    });

    fc.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!fc.checkValidity()) { fc.reportValidity(); return; }
      var btn = fc.querySelector('button[type="submit"]');
      btn.disabled = true;
      api('/api/entrar/verificar', { json: { email: email, codigo: fc.elements.codigo.value.trim() } })
        .then(function (s) {
          fc.hidden = true;
          fe.hidden = false;
          fe.reset();
          aoEntrar(s);
        })
        .catch(function (err) { status(fc.querySelector('.status'), 'err', err.message); })
        .then(function () { btn.disabled = false; });
    });

    fc.querySelector('[data-outro-email]').addEventListener('click', function () {
      fc.hidden = true;
      fe.hidden = false;
      fe.elements.email.focus();
    });

    // Ligação do email: ?email=...&codigo=... entra diretamente.
    var q = new URLSearchParams(location.search);
    if (q.get('email') && /^\d{6}$/.test(q.get('codigo') || '')) {
      email = q.get('email');
      pedirCodigo();
      fc.elements.codigo.value = q.get('codigo');
      history.replaceState(null, '', location.pathname + location.hash);
      if (fc.requestSubmit) fc.requestSubmit();
      else fc.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  }

  function ligarSaida(aoSair) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-sair]'), function (b) {
      b.addEventListener('click', function () {
        b.disabled = true;
        api('/api/sessao/sair', { json: {} }).catch(function () {}).then(function () {
          b.disabled = false;
          if (aoSair) aoSair();
          else location.reload();
        });
      });
    });
  }

  function mostrarSeparador(nome) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-panel]'), function (p) {
      p.hidden = p.getAttribute('data-panel') !== nome;
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-tab]'), function (a) {
      if (a.getAttribute('data-tab') === nome) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
  }

  // Na pré-visualização não há ficheiros reais para descarregar.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-download]');
    if (a && PREVIEW) {
      e.preventDefault();
      var alvo = a.closest('.order, .detail, .file-row');
      var st = alvo && alvo.querySelector('.status');
      if (st) status(st, 'info', 'Na demonstração não há ficheiros para descarregar.');
    }
  });

  window.GARC = {
    PREVIEW: PREVIEW, CAT: CAT, esc: esc, tokens: tokens, sinal: sinal, data: data, tamanho: tamanho,
    pill: pill, nomeModulo: nomeModulo, ENTREGAS: ENTREGAS, movimentoTexto: movimentoTexto,
    api: api, upload: upload, status: status, confirmar: confirmar,
    ligarEntrada: ligarEntrada, ligarSaida: ligarSaida, mostrarSeparador: mostrarSeparador
  };
})();
