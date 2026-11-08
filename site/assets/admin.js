/* Painel de administração: pedidos, oficinas e tokens. */
(function () {
  'use strict';

  var G = window.GARC;
  if (!G) return;
  var esc = G.esc;

  function $(id) { return document.getElementById(id); }

  var vistas = { carregar: $('p-carregar'), entrar: $('v-entrar'), painel: $('v-painel') };
  var est = { sessao: null, filtroPedidos: 'tratar', filtroOficinas: 'pendente', pedido: null, oficina: null };

  var VAZIO_PEDIDOS = {
    tratar: 'Não há pedidos por tratar.',
    a_aguardar_ficheiro: 'Não há pedidos à espera do ficheiro.',
    concluido: 'Ainda não há pedidos concluídos.',
    fechado: 'Não há pedidos recusados nem cancelados.',
    todos: 'Ainda não há pedidos.'
  };
  var VAZIO_OFICINAS = {
    pendente: 'Não há registos por aprovar.',
    aprovada: 'Ainda não há oficinas aprovadas.',
    todas: 'Ainda não há oficinas registadas.'
  };

  function mostrar(nome) {
    Object.keys(vistas).forEach(function (k) { if (vistas[k]) vistas[k].hidden = k !== nome; });
  }

  function kv(pares) {
    return '<dl class="kv">' + pares.map(function (x) { return '<div><dt>' + x[0] + '</dt><dd>' + x[1] + '</dd></div>'; }).join('') + '</dl>';
  }

  function tratarErro(el) {
    return function (err) {
      if (err.status === 401 || err.status === 403) { est.sessao = null; rota(); return; }
      if (el) el.innerHTML = '<p class="status" data-kind="err">' + esc(err.message) + '</p>';
    };
  }

  function semAcesso() {
    mostrar('carregar');
    vistas.carregar.innerHTML = 'Esta conta não tem acesso ao painel. <a href="' + esc(G.CAT.urls.areaCliente || '/area-cliente') + '">Ir para a área de cliente</a>.';
  }

  function atualizarContagens() {
    G.api('/api/admin/resumo').then(function (r) {
      $('a-n-pedidos').textContent = r.pedidos_por_tratar || '';
      $('a-n-oficinas').textContent = r.oficinas_pendentes || '';
    }).catch(function () {});
  }

  function rota() {
    if (!est.sessao) { mostrar('entrar'); return; }
    mostrar('painel');
    atualizarContagens();
    var h = (location.hash || '').slice(1);
    var m;
    if ((m = /^pedido-(\d+)$/.exec(h))) {
      G.mostrarSeparador('pedidos');
      est.pedido = m[1];
      carregarPedidos();
      abrirPedido(m[1]);
      return;
    }
    if ((m = /^oficina-(\d+)$/.exec(h))) {
      G.mostrarSeparador('oficinas');
      est.oficina = m[1];
      carregarOficinas();
      abrirOficina(m[1]);
      return;
    }
    if (h === 'oficinas') {
      G.mostrarSeparador('oficinas');
      est.oficina = null;
      $('a-oficina').hidden = true;
      carregarOficinas();
      return;
    }
    G.mostrarSeparador('pedidos');
    est.pedido = null;
    $('a-pedido').hidden = true;
    carregarPedidos();
  }

  function ligarFiltros(id, chave, recarregar) {
    $(id).addEventListener('click', function (e) {
      var b = e.target.closest('[data-filtro]');
      if (!b) return;
      est[chave] = b.getAttribute('data-filtro');
      Array.prototype.forEach.call(this.querySelectorAll('[data-filtro]'), function (x) {
        x.setAttribute('aria-pressed', String(x === b));
      });
      recarregar();
    });
  }

  /* ---------------------------------------------------------------- Pedidos */

  function viaturaTxt(p) {
    return p.viatura + (p.matricula ? ' · ' + p.matricula : '');
  }

  function itemPedido(p) {
    var atual = String(est.pedido) === String(p.id) ? ' aria-current="true"' : '';
    return '<a class="list-item" href="#pedido-' + p.id + '"' + atual + '>' +
      '<span class="row"><strong>N.º ' + p.id + '</strong>' + G.pill(p.estado) + '</span>' +
      '<span class="row"><span>' + esc(p.oficina_nome) + '</span><span>' + esc(G.tokens(p.tokens)) + '</span></span>' +
      '<span class="row"><span>' + esc(viaturaTxt(p)) + ', ' + esc(p.ecu) + '</span><span>' + esc(G.data(p.criado_em)) + '</span></span>' +
      '</a>';
  }

  function carregarPedidos() {
    var el = $('a-pedidos');
    G.api('/api/admin/pedidos?filtro=' + encodeURIComponent(est.filtroPedidos)).then(function (r) {
      el.innerHTML = r.pedidos.length ? r.pedidos.map(itemPedido).join('') : '<div class="empty">' + VAZIO_PEDIDOS[est.filtroPedidos] + '</div>';
    }).catch(tratarErro(el));
  }

  function abrirPedido(id) {
    var el = $('a-pedido');
    el.hidden = false;
    el.innerHTML = '<p class="muted">A carregar o pedido…</p>';
    G.api('/api/admin/pedidos/' + id).then(function (r) { desenharPedido(r.pedido); }).catch(tratarErro(el));
  }

  function linhaFicheiro(rotulo, p, tipo, extra) {
    var nome = p[tipo + '_nome'];
    var info = nome
      ? esc(nome) + ' <span class="muted">(' + G.tamanho(p[tipo + '_tamanho']) + ')</span>'
      : '<span class="muted">' + (tipo === 'original' ? 'Ainda não enviado' : 'Ainda não carregado') + '</span>';
    var botoes = nome ? '<a class="btn btn-secondary btn-sm" data-download href="/api/pedidos/' + p.id + '/' + tipo + '">Descarregar</a>' : '';
    return '<div class="file-row"><div><strong>' + rotulo + '</strong><br>' + info + '</div><div class="actions">' + botoes + (extra || '') + '</div></div>';
  }

  function desenharPedido(p) {
    var el = $('a-pedido');
    var o = p.oficina || {};
    var podeCarregar = ['recebido', 'em_curso', 'concluido'].indexOf(p.estado) >= 0;
    var podeConcluir = podeCarregar && !!p.modificado_nome;
    var podeRecusar = ['a_aguardar_ficheiro', 'recebido', 'em_curso'].indexOf(p.estado) >= 0;
    var pares = [
      ['Oficina', '<a href="#oficina-' + o.id + '">' + esc(o.nome) + '</a>'],
      ['Contacto', esc(o.email) + '<br>' + esc(o.telefone)],
      ['Viatura', esc(p.viatura) + (p.motor ? ', ' + esc(p.motor) : '') + (p.ano ? ', ' + esc(p.ano) : '')],
      ['Matrícula', esc(p.matricula || '—')],
      ['ECU', esc(p.ecu)],
      ['Ferramenta e método', esc([p.ferramenta, p.metodo].filter(Boolean).join(', ') || 'Não indicados')],
      ['Módulos', esc(p.modulos.map(G.nomeModulo).join(', '))],
      ['Tokens', esc(G.tokens(p.tokens)) + (p.devolvido ? ' <span class="muted">(devolvidos)</span>' : '')],
      ['Entrega', esc(G.ENTREGAS[p.entrega] || p.entrega) + (p.entrega === 'whatsapp' && p.whatsapp ? ', ' + esc(p.whatsapp) : '')],
      ['Enviado', esc(G.data(p.criado_em))]
    ];
    if (p.declaracao_emissoes) pares.push(['Declaração', 'Uso em competição ou fora da via pública, aceite no envio do pedido']);

    var carregar = podeCarregar
      ? '<label class="btn btn-primary btn-sm file-pick">' + (p.modificado_nome ? 'Substituir' : 'Carregar ficheiro') +
        '<input type="file" data-modificado aria-label="Carregar o ficheiro modificado"></label>'
      : '';

    var h = '<div class="detail-head"><h2>Pedido n.º ' + p.id + '</h2>' + G.pill(p.estado) + '</div>' + kv(pares);
    if (p.observacoes) h += '<div class="stack"><h3>Observações da oficina</h3><p class="note">' + esc(p.observacoes) + '</p></div>';
    h += '<div class="stack"><h3>Ficheiros</h3>' + linhaFicheiro('Original', p, 'original') + linhaFicheiro('Modificado', p, 'modificado', carregar) + '</div>';

    if (podeConcluir || podeRecusar) {
      h += '<div class="field"><label for="a-nota">Mensagem para o cliente</label>' +
        '<textarea id="a-nota" maxlength="2000" placeholder="Opcional ao concluir. Obrigatória ao recusar.">' + esc(p.nota || '') + '</textarea></div>';
    } else if (p.nota) {
      h += '<div class="stack"><h3>Mensagem enviada ao cliente</h3><p class="note">' + esc(p.nota) + '</p></div>';
    }

    var acoes = [];
    if (p.estado === 'recebido') acoes.push('<button class="btn btn-secondary" type="button" data-acao="em_curso">Marcar em curso</button>');
    if (podeConcluir) acoes.push('<button class="btn btn-primary" type="button" data-acao="concluir">' + (p.estado === 'concluido' ? 'Entregar de novo' : 'Concluir e entregar') + '</button>');
    if (p.estado === 'concluido' && p.whatsapp_url) acoes.push('<a class="btn btn-secondary" href="' + esc(p.whatsapp_url) + '" target="_blank" rel="noopener">Abrir WhatsApp</a>');
    if (podeRecusar) acoes.push('<button class="btn btn-secondary" type="button" data-acao="recusar">Recusar e devolver tokens</button>');
    if (acoes.length) h += '<div class="actions">' + acoes.join('') + '</div>';
    if (podeCarregar && !p.modificado_nome) h += '<p class="hint">Para concluir, carregue primeiro o ficheiro modificado.</p>';
    h += '<p class="status" role="status" aria-live="polite" hidden></p>';

    el.innerHTML = h;
    el.setAttribute('data-id', p.id);
    el.hidden = false;
  }

  var MSG_ACAO = {
    em_curso: 'Pedido marcado como em curso.',
    recusar: 'Pedido recusado. Os tokens voltaram ao saldo da oficina e a oficina foi avisada por email.'
  };

  $('a-pedido').addEventListener('click', function (e) {
    var b = e.target.closest('[data-acao]');
    if (!b) return;
    var painel = this;
    var id = painel.getAttribute('data-id');
    var acao = b.getAttribute('data-acao');
    var st = painel.querySelector('.status');
    var notaEl = $('a-nota');
    var nota = notaEl ? notaEl.value : '';
    function executar() {
      b.disabled = true;
      G.api('/api/admin/pedidos/' + id + '/estado', { json: { acao: acao, nota: nota } }).then(function (r) {
        desenharPedido(r.pedido);
        var msg = MSG_ACAO[acao];
        if (acao === 'concluir') {
          msg = r.pedido.entrega === 'whatsapp'
            ? 'Pedido concluído e oficina avisada por email. Envie agora o ficheiro pelo WhatsApp: descarregue-o e use o botão Abrir WhatsApp.'
            : r.pedido.entrega === 'email'
              ? 'Pedido concluído. O ficheiro seguiu por email e está na área de cliente.'
              : 'Pedido concluído. A oficina foi avisada por email.';
        }
        G.status($('a-pedido').querySelector('.status'), 'ok', msg);
        carregarPedidos();
        atualizarContagens();
      }).catch(function (err) {
        b.disabled = false;
        if (err.status === 401) { est.sessao = null; rota(); return; }
        G.status(st, 'err', err.message);
      });
    }
    if (acao === 'recusar') {
      if (!nota.trim()) {
        G.status(st, 'err', 'Escreva o motivo da recusa na mensagem para o cliente.');
        if (notaEl) notaEl.focus();
        return;
      }
      G.confirmar(b, 'Confirmar recusa', executar);
      return;
    }
    executar();
  });

  $('a-pedido').addEventListener('change', function (e) {
    var input = e.target.closest('[data-modificado]');
    if (!input || !input.files[0]) return;
    var id = this.getAttribute('data-id');
    var st = this.querySelector('.status');
    var f = input.files[0];
    if (f.size > G.CAT.maxMb * 1048576) {
      G.status(st, 'err', 'O ficheiro tem mais de ' + G.CAT.maxMb + ' MB.');
      return;
    }
    G.status(st, 'info', 'A carregar o ficheiro…');
    G.upload('/api/admin/pedidos/' + id + '/modificado', f, function (x) {
      G.status(st, 'info', 'A carregar o ficheiro: ' + Math.round(x * 100) + '%');
    }).then(function (r) {
      desenharPedido(r.pedido);
      G.status($('a-pedido').querySelector('.status'), 'ok', 'Ficheiro modificado carregado. Conclua o pedido para o entregar.');
    }).catch(function (err) { G.status(st, 'err', err.message); });
  });

  /* ---------------------------------------------------------------- Oficinas */

  function itemOficina(o) {
    var atual = String(est.oficina) === String(o.id) ? ' aria-current="true"' : '';
    return '<a class="list-item" href="#oficina-' + o.id + '"' + atual + '>' +
      '<span class="row"><strong>' + esc(o.nome) + '</strong>' + G.pill(o.estado) + '</span>' +
      '<span class="row"><span>NIF ' + esc(o.nif) + '</span><span>' + esc(G.tokens(o.saldo)) + '</span></span>' +
      '<span class="row"><span>' + esc(o.email) + '</span><span>' + esc(G.data(o.criada_em)) + '</span></span>' +
      '</a>';
  }

  function carregarOficinas() {
    var el = $('a-oficinas');
    G.api('/api/admin/oficinas?filtro=' + encodeURIComponent(est.filtroOficinas)).then(function (r) {
      el.innerHTML = r.oficinas.length ? r.oficinas.map(itemOficina).join('') : '<div class="empty">' + VAZIO_OFICINAS[est.filtroOficinas] + '</div>';
    }).catch(tratarErro(el));
  }

  function abrirOficina(id) {
    var el = $('a-oficina');
    el.hidden = false;
    el.innerHTML = '<p class="muted">A carregar a oficina…</p>';
    G.api('/api/admin/oficinas/' + id).then(desenharOficina).catch(tratarErro(el));
  }

  function desenharOficina(r) {
    var o = r.oficina;
    var el = $('a-oficina');
    var botoesEstado = [];
    if (o.estado === 'pendente') {
      botoesEstado.push('<button class="btn btn-primary" type="button" data-estado="aprovada">Aprovar conta</button>');
      botoesEstado.push('<button class="btn btn-secondary" type="button" data-estado="recusada">Recusar registo</button>');
    } else if (o.estado === 'aprovada') {
      botoesEstado.push('<button class="btn btn-secondary" type="button" data-estado="suspensa">Suspender conta</button>');
    } else {
      botoesEstado.push('<button class="btn btn-primary" type="button" data-estado="aprovada">Aprovar conta</button>');
    }

    var h = '<div class="detail-head"><h2>' + esc(o.nome) + '</h2>' + G.pill(o.estado) + '</div>';
    h += kv([
      ['NIF', esc(o.nif)],
      ['Responsável', esc(o.responsavel)],
      ['Email', esc(o.email)],
      ['Telefone', esc(o.telefone)],
      ['WhatsApp', esc(o.whatsapp || 'O mesmo do telefone')],
      ['Entrega preferida', esc(G.ENTREGAS[o.entrega] || o.entrega)],
      ['Registada', esc(G.data(o.criada_em))],
      ['Aprovada', esc(o.aprovada_em ? G.data(o.aprovada_em) : 'Ainda não')]
    ]);
    h += '<div class="actions">' + botoesEstado.join('') + '</div>';

    h += '<div class="stack"><h3>Saldo: ' + esc(G.tokens(r.saldo)) + '</h3>' +
      '<form class="inline-form" id="a-form-tokens">' +
      '<div class="field"><label for="a-tokens">Tokens</label><input id="a-tokens" name="tokens" type="number" step="1" required inputmode="numeric"></div>' +
      '<div class="field"><label for="a-ref">Fatura ou nota</label><input id="a-ref" name="referencia" maxlength="120" placeholder="ex.: FT 2026/120"></div>' +
      '<button class="btn btn-primary" type="submit">Carregar tokens</button></form>' +
      '<p class="hint">Para corrigir um carregamento, use um número negativo.</p></div>';

    if (r.movimentos.length) {
      h += '<div class="stack"><h3>Extrato</h3><div class="table-wrap"><table class="ledger"><thead><tr><th scope="col">Data</th>' +
        '<th scope="col">Movimento</th><th scope="col" class="num">Tokens</th></tr></thead><tbody>' +
        r.movimentos.map(function (m) {
          return '<tr><td>' + esc(G.data(m.criado_em)) + '</td><td>' + esc(G.movimentoTexto(m)) + '</td><td class="num' +
            (m.tokens > 0 ? ' pos' : '') + '">' + G.sinal(m.tokens) + '</td></tr>';
        }).join('') + '</tbody></table></div></div>';
    }
    if (r.pedidos.length) {
      h += '<div class="stack"><h3>Pedidos</h3><div class="list">' + r.pedidos.map(function (p) {
        return '<a class="list-item" href="#pedido-' + p.id + '"><span class="row"><strong>N.º ' + p.id + '</strong>' + G.pill(p.estado) + '</span>' +
          '<span class="row"><span>' + esc(viaturaTxt(p)) + ', ' + esc(p.ecu) + '</span><span>' + esc(G.tokens(p.tokens)) + '</span></span></a>';
      }).join('') + '</div></div>';
    }
    h += '<p class="status" role="status" aria-live="polite" hidden></p>';
    el.innerHTML = h;
    el.setAttribute('data-id', o.id);
    el.hidden = false;
  }

  var MSG_ESTADO = {
    aprovada: 'Conta aprovada. A oficina foi avisada por email.',
    recusada: 'Registo recusado.',
    suspensa: 'Conta suspensa. As sessões abertas da oficina foram terminadas.'
  };

  $('a-oficina').addEventListener('click', function (e) {
    var b = e.target.closest('[data-estado]');
    if (!b) return;
    var painel = this;
    var id = painel.getAttribute('data-id');
    var estado = b.getAttribute('data-estado');
    function executar() {
      b.disabled = true;
      G.api('/api/admin/oficinas/' + id + '/estado', { json: { estado: estado } }).then(function (r) {
        desenharOficina(r);
        G.status($('a-oficina').querySelector('.status'), 'ok', MSG_ESTADO[estado]);
        carregarOficinas();
        atualizarContagens();
      }).catch(function (err) {
        b.disabled = false;
        G.status(painel.querySelector('.status'), 'err', err.message);
      });
    }
    if (estado === 'aprovada') executar();
    else G.confirmar(b, estado === 'suspensa' ? 'Confirmar suspensão' : 'Confirmar recusa', executar);
  });

  $('a-oficina').addEventListener('submit', function (e) {
    if (e.target.id !== 'a-form-tokens') return;
    e.preventDefault();
    var f = e.target;
    var painel = this;
    if (!f.checkValidity()) { f.reportValidity(); return; }
    var id = painel.getAttribute('data-id');
    var btn = f.querySelector('button[type="submit"]');
    var n = Number(f.elements.tokens.value);
    btn.disabled = true;
    G.api('/api/admin/oficinas/' + id + '/tokens', { json: { tokens: n, referencia: f.elements.referencia.value } }).then(function (r) {
      desenharOficina(r);
      G.status($('a-oficina').querySelector('.status'), 'ok', n > 0
        ? 'Carregados ' + G.tokens(n) + '. Saldo: ' + G.tokens(r.saldo) + '. A oficina foi avisada por email.'
        : 'Acerto registado. Saldo: ' + G.tokens(r.saldo) + '.');
      carregarOficinas();
    }).catch(function (err) {
      btn.disabled = false;
      G.status(painel.querySelector('.status'), 'err', err.message);
    });
  });

  /* ---------------------------------------------------------------- Arranque */

  ligarFiltros('a-filtro-pedidos', 'filtroPedidos', carregarPedidos);
  ligarFiltros('a-filtro-oficinas', 'filtroOficinas', carregarOficinas);
  G.ligarEntrada(function (s) {
    if (!s.admin) { semAcesso(); return; }
    est.sessao = s;
    rota();
  });
  G.ligarSaida(function () {
    est.sessao = null;
    rota();
    location.hash = 'entrar';
  });
  window.addEventListener('hashchange', rota);
  G.api('/api/sessao').then(function (s) {
    if (!s || !s.email) { est.sessao = null; rota(); return; }
    if (!s.admin) { semAcesso(); return; }
    est.sessao = s;
    rota();
  }).catch(function () {
    est.sessao = null;
    rota();
  });
})();
