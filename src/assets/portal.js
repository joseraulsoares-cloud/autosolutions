/* Área de cliente: pedidos, novo pedido, saldo e conta. */
(function () {
  'use strict';

  var G = window.GARC;
  if (!G) return;
  var esc = G.esc;

  function $(id) { return document.getElementById(id); }

  var est = { sessao: null, saldo: 0, voltar: 'pedidos', pedidos: [] };
  var PAINEIS = ['pedidos', 'novo', 'saldo', 'conta'];
  var vistas = { carregar: $('p-carregar'), entrar: $('v-entrar'), registo: $('v-registo'), painel: $('v-painel') };
  var form = $('form-pedido');

  function mostrar(nome) {
    Object.keys(vistas).forEach(function (k) { if (vistas[k]) vistas[k].hidden = k !== nome; });
  }

  function definirSaldo(n) {
    est.saldo = Number(n) || 0;
    $('p-saldo').textContent = est.saldo;
    atualizarResumo();
  }

  function aplicarSessao(s) {
    est.sessao = s;
    $('p-sub').textContent = s.oficina.nome;
    $('p-saldo-box').hidden = false;
    definirSaldo(s.saldo);
    prepararNovo();
  }

  function sessaoTerminada() {
    est.sessao = null;
    est.pedidos = [];
    $('p-saldo-box').hidden = true;
    $('p-sub').textContent = 'Envie ficheiros, acompanhe os pedidos e consulte o saldo de tokens.';
    rota();
  }

  function tratarErro(el) {
    return function (err) {
      if (err.status === 401) { sessaoTerminada(); return; }
      if (el) el.innerHTML = '<p class="status" data-kind="err">' + esc(err.message) + '</p>';
    };
  }

  function rota() {
    var h = (location.hash || '').slice(1);
    if (!est.sessao) {
      if (h === 'registo') { mostrar('registo'); return; }
      if (PAINEIS.indexOf(h) >= 0) est.voltar = h;
      mostrar('entrar');
      return;
    }
    var tab = PAINEIS.indexOf(h) >= 0 ? h : 'pedidos';
    mostrar('painel');
    G.mostrarSeparador(tab);
    if (tab === 'pedidos') carregarPedidos();
    else if (tab === 'saldo') carregarSaldo();
    else if (tab === 'novo') atualizarResumo();
    else if (tab === 'conta') preencherConta();
  }

  function semAcesso(s) {
    mostrar('carregar');
    if (s && s.admin) {
      vistas.carregar.innerHTML = 'Entrou como administrador. <a href="' + esc(G.CAT.urls.admin || '/admin') + '">Abrir o painel de administração</a>.';
    } else {
      vistas.carregar.textContent = 'A conta não está ativa. Contacte-nos.';
    }
  }

  function aoEntrar(s) {
    if (!s.oficina || s.oficina.estado !== 'aprovada') { semAcesso(s); return; }
    aplicarSessao(s);
    var alvo = est.voltar || 'pedidos';
    if (location.hash.slice(1) === alvo) rota();
    else location.hash = alvo;
  }

  /* ---------------------------------------------------------------- Pedidos */

  function linhaPedido(p) {
    var acoes = [];
    if (p.estado === 'concluido' && p.modificado_nome && !p.ficheiros_apagados) {
      acoes.push('<a class="btn btn-primary btn-sm" data-download href="/api/pedidos/' + p.id + '/modificado">Descarregar ficheiro</a>');
    }
    if (p.estado === 'a_aguardar_saldo') {
      acoes.push('<a class="btn btn-primary btn-sm" href="#saldo">Carregar saldo</a>');
    }
    if (p.estado === 'a_aguardar_ficheiro') {
      acoes.push('<label class="btn btn-primary btn-sm file-pick">Enviar ficheiro<input type="file" data-reenviar="' + p.id +
        '" aria-label="Escolher o ficheiro do pedido n.º ' + p.id + '"></label>');
      acoes.push('<button class="btn btn-secondary btn-sm" type="button" data-cancelar="' + p.id + '">Cancelar pedido</button>');
    }
    var custo = p.custo_definido
      ? esc(G.tokens(p.tokens)) + (p.falta ? ' <span class="muted">(pagos ' + esc(G.tokens(p.pagos)) + ')</span>' : '')
      : esc(G.tokens(p.pagos)) + ' descontados <span class="muted">(custo final por confirmar)</span>';
    var kv = [
      ['Matrícula', esc(p.matricula || '—')],
      ['ECU', esc(p.ecu)],
      ['Custo', custo],
      ['Módulos', esc(p.modulos.map(G.nomeModulo).join(', '))],
      ['Enviado', esc(G.data(p.criado_em))],
      ['Entrega', esc(G.ENTREGAS[p.entrega] || p.entrega)]
    ];
    if (p.original_nome) kv.push(['Ficheiro enviado', esc(p.original_nome) + ' <span class="muted">(' + G.tamanho(p.original_tamanho) + ')</span>']);
    if (p.concluido_em) kv.push(['Concluído', esc(G.data(p.concluido_em))]);
    var notas = '';
    if (p.estado === 'a_aguardar_ficheiro') {
      notas += '<p class="note">O pedido está criado, mas o ficheiro ainda não chegou. Envie-o, ou cancele o pedido para recuperar os tokens.</p>';
    }
    if (p.estado === 'a_aguardar_saldo') {
      notas += '<p class="note">O custo final é de ' + esc(G.tokens(p.tokens)) + '. Faltam ' + esc(G.tokens(p.falta)) +
        ': carregue o saldo e a diferença é descontada automaticamente para o pedido avançar.</p>';
    }
    if (p.ficheiros_apagados) notas += '<p class="note">Os ficheiros deste pedido já foram apagados. Ficam guardados durante um mês depois de o pedido ser fechado.</p>';
    if (p.nota) notas += '<p class="note">' + esc(p.nota) + '</p>';
    var titulo = esc(p.viatura) + (p.motor ? ' <span class="muted">' + esc(p.motor) + '</span>' : '') +
      (p.ano ? ' <span class="muted">' + esc(p.ano) + '</span>' : '');
    return '<article class="order" data-pedido="' + p.id + '">' +
      '<div class="order-top"><span class="order-id">N.º ' + p.id + '</span>' + G.pill(p.estado) +
      '<span class="order-cost">' + esc(G.tokens(p.tokens)) + (p.custo_definido ? '' : ' (provisório)') + '</span></div>' +
      '<h3>' + titulo + '</h3>' +
      '<dl class="kv">' + kv.map(function (x) { return '<div><dt>' + x[0] + '</dt><dd>' + x[1] + '</dd></div>'; }).join('') + '</dl>' +
      notas +
      (acoes.length ? '<div class="actions">' + acoes.join('') + '</div>' : '') +
      '<p class="status" role="status" aria-live="polite" hidden></p>' +
      '</article>';
  }

  function carregarPedidos() {
    var lista = $('p-pedidos');
    if (!est.pedidos.length) lista.innerHTML = '<p class="muted">A carregar os pedidos…</p>';
    G.api('/api/pedidos').then(function (r) {
      est.pedidos = r.pedidos;
      lista.innerHTML = r.pedidos.length
        ? r.pedidos.map(linhaPedido).join('')
        : '<div class="empty"><p>Ainda não enviou pedidos. Os pedidos enviados aparecem aqui, com o estado de cada um.</p>' +
          '<p><a class="btn btn-primary" href="#novo">Enviar o primeiro pedido</a></p></div>';
    }).catch(tratarErro(lista));
  }

  $('p-pedidos').addEventListener('click', function (e) {
    var b = e.target.closest('[data-cancelar]');
    if (!b) return;
    var id = b.getAttribute('data-cancelar');
    var st = b.closest('.order').querySelector('.status');
    G.confirmar(b, 'Confirmar cancelamento', function () {
      b.disabled = true;
      G.api('/api/pedidos/' + id + '/cancelar', { json: {} }).then(function (r) {
        definirSaldo(r.saldo);
        G.status($('p-aviso'), 'ok', 'Pedido n.º ' + id + ' cancelado. Os tokens voltaram ao saldo.');
        carregarPedidos();
      }).catch(function (err) {
        b.disabled = false;
        if (err.status === 401) { sessaoTerminada(); return; }
        G.status(st, 'err', err.message);
      });
    });
  });

  $('p-pedidos').addEventListener('change', function (e) {
    var input = e.target.closest('[data-reenviar]');
    if (!input || !input.files[0]) return;
    var id = input.getAttribute('data-reenviar');
    var st = input.closest('.order').querySelector('.status');
    var f = input.files[0];
    if (f.size > G.CAT.maxMb * 1048576) {
      G.status(st, 'err', 'O ficheiro tem mais de ' + G.CAT.maxMb + ' MB. Comprima-o em .zip ou contacte-nos.');
      return;
    }
    G.status(st, 'info', 'A enviar o ficheiro…');
    G.upload('/api/pedidos/' + id + '/original', f, function (x) {
      G.status(st, 'info', 'A enviar o ficheiro: ' + Math.round(x * 100) + '%');
    }).then(function () {
      G.status($('p-aviso'), 'ok', 'Ficheiro do pedido n.º ' + id + ' recebido.');
      carregarPedidos();
    }).catch(function (err) {
      if (err.status === 401) { sessaoTerminada(); return; }
      G.status(st, 'err', err.message);
    });
  });

  /* ---------------------------------------------------------------- Novo pedido */

  function marcados() {
    return Array.prototype.slice.call(form.querySelectorAll('input[name="modulos"]:checked'));
  }

  // No envio desconta-se sempre o mínimo; o custo final depende da ECU e é confirmado depois.
  function custoAtual() {
    return G.CAT.minimo || 5;
  }

  function entregaEscolhida(f) {
    var r = (f || form).querySelector('input[name="entrega"]:checked');
    return r ? r.value : 'portal';
  }

  function atualizarResumo() {
    if (!form) return;
    var custo = custoAtual();
    var saldo = est.saldo;
    var resumo = $('f-resumo');
    var msg = $('f-resumo-msg');
    var btn = $('f-enviar');
    $('f-total').textContent = G.tokens(custo);
    $('f-saldo-atual').textContent = est.sessao ? G.tokens(saldo) : '–';
    if (est.sessao && custo > saldo) {
      resumo.setAttribute('data-estado', 'falta');
      msg.innerHTML = 'Para enviar um pedido precisa de pelo menos ' + esc(G.tokens(custo)) + '. Faltam ' +
        esc(G.tokens(custo - saldo)) + '. <a href="#saldo">Carregar saldo</a>';
      btn.textContent = 'Enviar pedido';
      btn.disabled = true;
    } else if (!marcados().length) {
      resumo.setAttribute('data-estado', 'vazio');
      msg.textContent = 'Escolha os módulos pretendidos.';
      btn.textContent = 'Enviar pedido';
      btn.disabled = false;
    } else {
      resumo.setAttribute('data-estado', 'ok');
      msg.textContent = 'No envio, o saldo fica em ' + G.tokens(saldo - custo) + '.';
      btn.textContent = 'Enviar pedido (' + G.tokens(custo) + ')';
      btn.disabled = false;
    }
    var emissoes = !!form.querySelector('input[data-emissions]:checked');
    $('decl-wrap').hidden = !emissoes;
    $('f-declaracao').required = emissoes;
    if (!emissoes) $('f-declaracao').checked = false;
    var wa = entregaEscolhida() === 'whatsapp';
    $('f-whatsapp-wrap').hidden = !wa;
    $('f-whatsapp').required = wa;
  }

  // Entrega e WhatsApp com as preferências da conta.
  function prepararNovo() {
    if (!form) return;
    var o = est.sessao && est.sessao.oficina;
    if (o) {
      var r = form.querySelector('input[name="entrega"][value="' + o.entrega + '"]');
      if (r) r.checked = true;
      if (!$('f-whatsapp').value) $('f-whatsapp').value = o.whatsapp || o.telefone || '';
    }
    atualizarResumo();
  }

  function enviarOriginal(id, ficheiro) {
    var prog = $('f-progresso');
    var barra = $('f-progresso-barra');
    var txt = $('f-progresso-txt');
    prog.hidden = false;
    barra.style.width = '0%';
    txt.textContent = 'A enviar o ficheiro…';
    return G.upload('/api/pedidos/' + id + '/original', ficheiro, function (x) {
      var pct = Math.round(x * 100);
      barra.style.width = pct + '%';
      txt.textContent = 'A enviar o ficheiro: ' + pct + '%';
    }).then(function (r) { prog.hidden = true; return r; }, function (err) { prog.hidden = true; throw err; });
  }

  if (form) {
    form.addEventListener('change', atualizarResumo);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var st = form.querySelector('.status');
      G.status(st, 'info', '');
      if (!marcados().length) { G.status(st, 'err', 'Escolha pelo menos um módulo.'); return; }
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var ficheiro = $('f-ficheiro').files[0];
      if (!ficheiro) { G.status(st, 'err', 'Escolha o ficheiro original.'); return; }
      if (ficheiro.size > G.CAT.maxMb * 1048576) {
        G.status(st, 'err', 'O ficheiro tem mais de ' + G.CAT.maxMb + ' MB. Comprima-o em .zip ou contacte-nos.');
        return;
      }
      var el = form.elements;
      var ent = entregaEscolhida();
      var corpo = {
        viatura: el.viatura.value, matricula: el.matricula.value, motor: el.motor.value, ano: el.ano.value, ecu: el.ecu.value,
        ferramenta: el.ferramenta.value, metodo: el.metodo.value,
        modulos: marcados().map(function (i) { return i.value; }),
        observacoes: el.observacoes.value,
        entrega: ent,
        whatsapp: ent === 'whatsapp' ? $('f-whatsapp').value : '',
        declaracao: $('f-declaracao').checked,
        tamanho: ficheiro.size
      };
      var btn = $('f-enviar');
      btn.disabled = true;
      G.status(st, 'info', 'A criar o pedido…');
      var idCriado = null;
      G.api('/api/pedidos', { json: corpo }).then(function (r) {
        idCriado = r.pedido.id;
        definirSaldo(r.saldo);
        G.status(st, 'info', '');
        return enviarOriginal(idCriado, ficheiro);
      }).then(function () {
        form.reset();
        prepararNovo();
        G.status($('p-aviso'), 'ok', 'Pedido n.º ' + idCriado + ' enviado. Foram descontados ' + G.tokens(custoAtual()) +
          '; depois de analisarmos a ECU confirmamos o custo final, e avisamos quando o ficheiro estiver pronto.');
        location.hash = 'pedidos';
      }).catch(function (err) {
        if (err.status === 401) { sessaoTerminada(); return; }
        if (err.body && typeof err.body.saldo === 'number') definirSaldo(err.body.saldo);
        if (idCriado) {
          // O pedido existe: o ficheiro volta a enviar-se a partir da lista, sem criar outro pedido.
          form.reset();
          prepararNovo();
          G.status($('p-aviso'), 'err', 'O pedido n.º ' + idCriado + ' foi criado, mas o ficheiro não chegou: ' + err.message + ' Envie-o de novo abaixo.');
          location.hash = 'pedidos';
          return;
        }
        G.status(st, 'err', err.message);
      }).then(atualizarResumo);
    });
  }

  /* ---------------------------------------------------------------- Saldo */

  function carregarSaldo() {
    var el = $('p-extrato');
    el.innerHTML = '<p class="muted">A carregar o extrato…</p>';
    G.api('/api/saldo').then(function (r) {
      definirSaldo(r.saldo);
      if (!r.movimentos.length) {
        el.innerHTML = '<div class="empty"><p>Ainda não há movimentos. O primeiro carregamento de tokens aparece aqui.</p></div>';
        return;
      }
      el.innerHTML = '<div class="table-wrap"><table class="ledger"><thead><tr><th scope="col">Data</th><th scope="col">Movimento</th>' +
        '<th scope="col" class="num">Tokens</th></tr></thead><tbody>' +
        r.movimentos.map(function (m) {
          return '<tr><td>' + esc(G.data(m.criado_em)) + '</td><td>' + esc(G.movimentoTexto(m)) + '</td><td class="num' +
            (m.tokens > 0 ? ' pos' : '') + '">' + G.sinal(m.tokens) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    }).catch(tratarErro(el));
  }

  /* ---------------------------------------------------------------- Conta */

  function preencherConta() {
    var o = est.sessao.oficina;
    $('p-conta-dados').innerHTML = [
      ['Oficina', o.nome], ['NIF', o.nif], ['Responsável', o.responsavel], ['Email', o.email], ['Conta criada', G.data(o.criada_em)]
    ].map(function (x) { return '<div><dt>' + x[0] + '</dt><dd>' + esc(x[1]) + '</dd></div>'; }).join('');
    var f = $('f-conta');
    f.elements.telefone.value = o.telefone || '';
    f.elements.whatsapp.value = o.whatsapp || '';
    var r = f.querySelector('input[name="entrega"][value="' + o.entrega + '"]');
    if (r) r.checked = true;
  }

  $('f-conta').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.currentTarget;
    var st = f.querySelector('.status');
    if (!f.checkValidity()) { f.reportValidity(); return; }
    var btn = f.querySelector('button[type="submit"]');
    btn.disabled = true;
    G.api('/api/conta', { json: { telefone: f.elements.telefone.value, whatsapp: f.elements.whatsapp.value, entrega: entregaEscolhida(f) } })
      .then(function (r) {
        est.sessao.oficina = r.oficina;
        $('f-whatsapp').value = '';
        prepararNovo();
        G.status(st, 'ok', 'Alterações guardadas.');
      })
      .catch(function (err) {
        if (err.status === 401) { sessaoTerminada(); return; }
        G.status(st, 'err', err.message);
      })
      .then(function () { btn.disabled = false; });
  });

  /* ---------------------------------------------------------------- Registo */

  $('f-registo').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.currentTarget;
    var st = f.querySelector('.status');
    if (!f.checkValidity()) { f.reportValidity(); return; }
    var btn = f.querySelector('button[type="submit"]');
    btn.disabled = true;
    var el = f.elements;
    G.api('/api/registo', {
      json: {
        nome: el.nome.value, nif: el.nif.value, responsavel: el.responsavel.value, email: el.email.value,
        telefone: el.telefone.value, whatsapp: el.whatsapp.value, entrega: entregaEscolhida(f),
        website: el.website.value, termos: el.termos.checked
      }
    }).then(function () {
      f.innerHTML = '<p class="status" data-kind="ok">Registo recebido. Vai receber um email quando a conta for aprovada.</p>' +
        '<div class="actions"><a class="btn btn-secondary" href="#entrar">Voltar a Entrar</a></div>';
    }).catch(function (err) {
      G.status(st, 'err', err.message);
      btn.disabled = false;
    });
  });

  /* ---------------------------------------------------------------- Arranque */

  G.ligarEntrada(aoEntrar);
  G.ligarSaida(function () {
    est.voltar = 'pedidos';
    sessaoTerminada();
    location.hash = 'entrar';
  });
  window.addEventListener('hashchange', rota);
  G.api('/api/sessao').then(function (s) {
    if (!s || !s.email) { est.sessao = null; rota(); return; }
    if (!s.oficina || s.oficina.estado !== 'aprovada') { semAcesso(s); return; }
    aplicarSessao(s);
    rota();
  }).catch(function () {
    est.sessao = null;
    rota();
  });
})();
