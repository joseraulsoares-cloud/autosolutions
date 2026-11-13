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
    a_aguardar_saldo: 'Não há pedidos à espera de saldo.',
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
    if (nome && p.ficheiros_apagados) info = esc(nome) + ' <span class="muted">(apagado)</span>';
    var botoes = nome && !p.ficheiros_apagados ? '<a class="btn btn-secondary btn-sm" data-download href="/api/pedidos/' + p.id + '/' + tipo + '">Descarregar</a>' : '';
    return '<div class="file-row"><div><strong>' + rotulo + '</strong><br>' + info + '</div><div class="actions">' + botoes + (extra || '') + '</div></div>';
  }

  function desenharPedido(p) {
    var el = $('a-pedido');
    var o = p.oficina || {};
    var podeCarregar = ['recebido', 'em_curso', 'a_aguardar_saldo', 'concluido'].indexOf(p.estado) >= 0 && !p.ficheiros_apagados;
    var podeConcluir = ['recebido', 'em_curso', 'concluido'].indexOf(p.estado) >= 0 && !!p.modificado_nome && !p.ficheiros_apagados;
    var podeRecusar = ['a_aguardar_ficheiro', 'recebido', 'em_curso', 'a_aguardar_saldo'].indexOf(p.estado) >= 0;
    var podeCusto = ['recebido', 'em_curso', 'a_aguardar_saldo'].indexOf(p.estado) >= 0;
    var pares = [
      ['Oficina', '<a href="#oficina-' + o.id + '">' + esc(o.nome) + '</a>'],
      ['Contacto', esc(o.email) + '<br>' + esc(o.telefone)],
      ['Viatura', esc(p.viatura) + (p.motor ? ', ' + esc(p.motor) : '') + (p.ano ? ', ' + esc(p.ano) : '')],
      ['Matrícula', esc(p.matricula || '—')],
      ['ECU', esc(p.ecu)],
      ['Ferramenta e método', esc([p.ferramenta, p.metodo].filter(Boolean).join(', ') || 'Não indicados')],
      ['Módulos', esc(p.modulos.map(G.nomeModulo).join(', '))],
      ['Custo', (p.custo_definido ? esc(G.tokens(p.tokens)) : esc(G.tokens(p.tokens)) + ' <span class="muted">(provisório: ainda não definiu o custo final)</span>') +
        '<br><span class="muted">Pagos: ' + esc(G.tokens(p.pagos)) + (p.falta ? ', faltam ' + esc(G.tokens(p.falta)) : '') +
        (p.devolvido ? ' (devolvidos)' : '') + '</span>'],
      ['Entrega', esc(G.ENTREGAS[p.entrega] || p.entrega) + (p.entrega === 'whatsapp' && p.whatsapp ? ', ' + esc(p.whatsapp) : '')],
      ['Enviado', esc(G.data(p.criado_em))]
    ];
    if (p.declaracao_emissoes) pares.push(['Declaração', 'Uso em competição ou fora da via pública, aceite no envio do pedido']);

    var carregar = podeCarregar
      ? '<label class="btn btn-primary btn-sm file-pick">' + (p.modificado_nome ? 'Substituir' : 'Carregar ficheiro') +
        '<input type="file" data-modificado aria-label="Carregar o ficheiro modificado"></label>'
      : '';

    var h = '<div class="detail-head"><h2>Pedido n.º ' + p.id + '</h2>' + G.pill(p.estado) + '</div>' + kv(pares);
    if (podeCusto) {
      h += '<div class="stack"><h3>Custo final</h3>' +
        '<p class="hint">Depois de analisar a ECU. A diferença para o que já foi pago é descontada do saldo da oficina; se o saldo não chegar, o pedido fica à espera e avança sozinho quando carregar tokens.</p>' +
        '<div class="inline-form"><div class="field"><label for="a-custo">Tokens</label>' +
        '<input id="a-custo" type="number" inputmode="numeric" min="' + (G.CAT.minimo || 5) + '" max="1000" step="1" value="' + p.tokens + '"></div>' +
        '<button class="btn btn-secondary" type="button" data-custo>Definir custo</button></div></div>';
    }
    if (p.ficheiros_apagados) h += '<p class="note">Os ficheiros deste pedido foram apagados automaticamente, um mês depois de o pedido ser fechado.</p>';
    if (p.personalizado) h += '<div class="stack"><h3>Pedido personalizado</h3><p class="note">' + esc(p.personalizado) + '</p></div>';
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
    if (p.estado === 'a_aguardar_saldo') h += '<p class="hint">Para concluir, a oficina tem de carregar a diferença do custo final.</p>';
    else if (podeCarregar && !p.modificado_nome) h += '<p class="hint">Para concluir, carregue primeiro o ficheiro modificado.</p>';
    h += '<p class="status" role="status" aria-live="polite" hidden></p>';

    el.innerHTML = h;
    el.setAttribute('data-id', p.id);
    el.hidden = false;
  }

  var MSG_ACAO = {
    em_curso: 'Pedido marcado como em curso.',
    recusar: 'Pedido recusado. Os tokens pagos voltaram ao saldo da oficina e a oficina foi avisada por email.'
  };

  $('a-pedido').addEventListener('click', function (e) {
    var bc = e.target.closest('[data-custo]');
    if (bc) {
      var painelC = this;
      var idC = painelC.getAttribute('data-id');
      var stC = painelC.querySelector('.status');
      var n = Number($('a-custo').value);
      var minimo = G.CAT.minimo || 5;
      if (!(n >= minimo && n <= 1000 && Math.floor(n) === n)) {
        G.status(stC, 'err', 'Indique um custo entre ' + G.tokens(minimo) + ' e 1000 tokens.');
        return;
      }
      bc.disabled = true;
      G.api('/api/admin/pedidos/' + idC + '/custo', { json: { tokens: n } }).then(function (r) {
        desenharPedido(r.pedido);
        var msg = r.pedido.estado === 'a_aguardar_saldo'
          ? 'Custo final de ' + G.tokens(r.pedido.tokens) + ' definido. O saldo da oficina não chega para a diferença: o pedido fica à espera e a oficina foi avisada por email.'
          : 'Custo final de ' + G.tokens(r.pedido.tokens) + ' definido e pago.';
        G.status($('a-pedido').querySelector('.status'), 'ok', msg);
        carregarPedidos();
        atualizarContagens();
      }).catch(function (err) {
        bc.disabled = false;
        if (err.status === 401) { est.sessao = null; rota(); return; }
        G.status(stC, 'err', err.message);
      });
      return;
    }
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

  // Mensagens da ficha da oficina (o formulário de edição tem a sua própria linha de estado).
  function estadoOficina() {
    return $('a-oficina').querySelector(':scope > .status');
  }

  function campoDados(id, nome, rotulo, valor, tipo, obrigatorio, extra) {
    return '<div class="field"><label for="' + id + '">' + rotulo + (obrigatorio ? ' <span class="req" aria-hidden="true">*</span>' : '') + '</label>' +
      '<input id="' + id + '" name="' + nome + '" type="' + tipo + '" value="' + esc(valor || '') + '"' +
      (obrigatorio ? ' required' : '') + (extra || '') + '></div>';
  }

  // Formulário para o administrador alterar os dados da oficina, a pedido dela.
  function formDados(o) {
    var entregas = Object.keys(G.ENTREGAS).map(function (k) {
      return '<div class="check"><input type="radio" id="a-d-entrega-' + k + '" name="entrega" value="' + k + '"' + (o.entrega === k ? ' checked' : '') + '>' +
        '<label for="a-d-entrega-' + k + '">' + esc(G.ENTREGAS[k]) + '</label></div>';
    }).join('');
    return '<form class="form" id="a-form-dados" hidden>' +
      '<h3>Editar dados</h3>' +
      '<div class="grid-2">' +
      campoDados('a-d-nome', 'nome', 'Oficina ou empresa', o.nome, 'text', true, ' maxlength="120"') +
      campoDados('a-d-nif', 'nif', 'NIF', o.nif, 'text', true, ' inputmode="numeric" maxlength="20"') +
      campoDados('a-d-responsavel', 'responsavel', 'Nome do responsável', o.responsavel, 'text', true, ' maxlength="120"') +
      campoDados('a-d-email', 'email', 'Email', o.email, 'email', true, ' maxlength="200"') +
      campoDados('a-d-telefone', 'telefone', 'Telefone', o.telefone, 'tel', true, ' maxlength="30"') +
      campoDados('a-d-whatsapp', 'whatsapp', 'WhatsApp, se for outro número', o.whatsapp, 'tel', false, ' maxlength="30"') +
      '</div>' +
      '<fieldset class="fieldset"><legend>Entrega preferida dos ficheiros</legend><div class="choices">' + entregas + '</div></fieldset>' +
      '<p class="hint">A oficina é avisada por email das alterações. Se mudar o email, as sessões abertas terminam e a oficina passa a entrar com o email novo.</p>' +
      '<div class="actions"><button class="btn btn-primary" type="submit">Guardar dados</button>' +
      '<button class="btn btn-secondary" type="button" data-cancelar-dados>Cancelar</button></div>' +
      '<p class="status" role="status" aria-live="polite" hidden></p>' +
      '</form>';
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
    botoesEstado.push('<button class="btn btn-secondary" type="button" data-editar aria-expanded="false" aria-controls="a-form-dados">Editar dados</button>');

    // Apagar a conta: só com o saldo a 0 e sem pedidos por fechar (o servidor confirma).
    var nPedidos = r.pedidos_total || 0;
    var pedidosTxt = nPedidos === 1 ? '1 pedido' : nPedidos + ' pedidos';
    var avisoApagar;
    if (r.saldo !== 0) {
      avisoApagar = 'Para apagar a conta, acerte primeiro o saldo para 0, com um carregamento de ' + (-r.saldo) + '.';
    } else if (r.pedidos_por_fechar) {
      avisoApagar = 'Para apagar a conta, conclua ou recuse primeiro ' +
        (r.pedidos_por_fechar === 1 ? 'o pedido por fechar.' : 'os ' + r.pedidos_por_fechar + ' pedidos por fechar.');
    } else if (nPedidos || r.movimentos.length) {
      avisoApagar = 'Apagar a conta apaga também ' + (nPedidos ? pedidosTxt + ', os ficheiros e ' : '') + 'o extrato, sem forma de recuperar.';
    } else {
      avisoApagar = 'Apagar a conta não tem volta.';
    }
    var bloqueada = r.saldo !== 0 || r.pedidos_por_fechar > 0;
    botoesEstado.push('<button class="btn btn-danger" type="button" data-apagar aria-describedby="a-aviso-apagar"' + (bloqueada ? ' disabled' : '') +
      ' data-texto-confirmar="' + (nPedidos || r.movimentos.length ? 'Confirmar: apagar tudo' : 'Confirmar: apagar conta') + '">Apagar conta</button>');

    h += '<div class="actions">' + botoesEstado.join('') + '</div>';
    h += '<p class="hint" id="a-aviso-apagar">' + esc(avisoApagar) + '</p>';
    h += formDados(o);

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
        G.status(estadoOficina(), 'ok', MSG_ESTADO[estado]);
        carregarOficinas();
        atualizarContagens();
      }).catch(function (err) {
        b.disabled = false;
        G.status(estadoOficina(), 'err', err.message);
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
      G.status(estadoOficina(), 'ok', n > 0
        ? 'Carregados ' + G.tokens(n) + '. Saldo: ' + G.tokens(r.saldo) + '. A oficina foi avisada por email.'
        : 'Acerto registado. Saldo: ' + G.tokens(r.saldo) + '.');
      carregarOficinas();
    }).catch(function (err) {
      btn.disabled = false;
      G.status(estadoOficina(), 'err', err.message);
    });
  });

  /* Editar dados da oficina */
  $('a-oficina').addEventListener('click', function (e) {
    var b = e.target.closest('[data-editar], [data-cancelar-dados]');
    if (!b) return;
    var f = $('a-form-dados');
    var botao = this.querySelector('[data-editar]');
    var abrir = b.hasAttribute('data-editar') && f.hidden;
    if (!abrir) f.reset();
    f.hidden = !abrir;
    G.status(f.querySelector('.status'), 'ok', '');
    botao.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    if (abrir) f.elements.nome.focus();
    else botao.focus();
  });

  $('a-oficina').addEventListener('submit', function (e) {
    if (e.target.id !== 'a-form-dados') return;
    e.preventDefault();
    var f = e.target;
    if (!f.checkValidity()) { f.reportValidity(); return; }
    var id = this.getAttribute('data-id');
    var btn = f.querySelector('button[type="submit"]');
    var entrega = f.querySelector('input[name="entrega"]:checked');
    var dados = {
      nome: f.elements.nome.value,
      nif: f.elements.nif.value,
      responsavel: f.elements.responsavel.value,
      email: f.elements.email.value,
      telefone: f.elements.telefone.value,
      whatsapp: f.elements.whatsapp.value,
      entrega: entrega ? entrega.value : ''
    };
    btn.disabled = true;
    G.api('/api/admin/oficinas/' + id + '/dados', { json: dados }).then(function (r) {
      var alterados = r.alterados || [];
      desenharOficina(r);
      G.status(estadoOficina(), 'ok', !alterados.length
        ? 'Não houve alterações.'
        : alterados.indexOf('email') >= 0
          ? 'Dados guardados. A oficina passa a entrar com o email novo: as sessões abertas terminaram e foi avisada no email antigo e no novo.'
          : 'Dados guardados. A oficina foi avisada por email.');
      carregarOficinas();
    }).catch(function (err) {
      btn.disabled = false;
      G.status(f.querySelector('.status'), 'err', err.message);
    });
  });

  /* Apagar a conta da oficina (dois cliques) */
  $('a-oficina').addEventListener('click', function (e) {
    var b = e.target.closest('[data-apagar]');
    if (!b || b.disabled) return;
    var painel = this;
    var id = painel.getAttribute('data-id');
    G.confirmar(b, b.getAttribute('data-texto-confirmar'), function () {
      b.disabled = true;
      G.api('/api/admin/oficinas/' + id + '/apagar', { json: {} }).then(function (r) {
        var a = r.apagada;
        var extra = a.pedidos
          ? ', com ' + (a.pedidos === 1 ? '1 pedido' : a.pedidos + ' pedidos') + ', os ficheiros e o extrato.'
          : a.movimentos ? ', com o extrato.' : '.';
        est.oficina = null;
        painel.removeAttribute('data-id');
        painel.innerHTML = '<p class="status" role="status" data-kind="ok">' + esc('Conta de ' + a.nome + ' apagada' + extra) + '</p>';
        // Sai da ficha apagada sem a voltar a pedir ao servidor.
        if (history.replaceState) history.replaceState(null, '', '#oficinas');
        carregarOficinas();
        atualizarContagens();
      }).catch(function (err) {
        b.disabled = false;
        G.status(estadoOficina(), 'err', err.message);
      });
    });
  });

  /* ---------------------------------------------------------------- Arranque */

  ligarFiltros('a-filtro-pedidos', 'filtroPedidos', carregarPedidos);
  ligarFiltros('a-filtro-oficinas', 'filtroOficinas', carregarOficinas);
  G.ligarEntrada(function (s) {
    if (!s.admin) { semAcesso(); return; }
    est.sessao = s;
    if (s.precos) G.CAT.minimo = s.precos.minimo;
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
    if (s.precos) G.CAT.minimo = s.precos.minimo;
    rota();
  }).catch(function () {
    est.sessao = null;
    rota();
  });
})();
