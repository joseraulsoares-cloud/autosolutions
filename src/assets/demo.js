/* Demonstração da área de cliente e do painel, só na pré-visualização. Os dados são de exemplo e nada é gravado. */
(function () {
  'use strict';

  var ADMIN = /admin/.test(location.pathname);

  function haMinutos(min) {
    return new Date(Date.now() - min * 60000).toISOString().slice(0, 19).replace('T', ' ');
  }
  var DIA = 24 * 60;

  function catalogo() {
    try { return JSON.parse(document.getElementById('catalogo').textContent); } catch (e) { return { modulos: {} }; }
  }

  var oficinas = [
    { id: 1, nome: 'Oficina Exemplo, Lda', nif: '500000000', responsavel: 'João Exemplo', email: 'oficina@exemplo.pt',
      telefone: '912 345 678', whatsapp: '912 345 678', entrega: 'portal', estado: 'aprovada',
      criada_em: haMinutos(40 * DIA), aprovada_em: haMinutos(39 * DIA) },
    { id: 2, nome: 'Auto Teste, Unipessoal Lda', nif: '510000000', responsavel: 'Ana Teste', email: 'ana@exemplo.pt',
      telefone: '923 456 789', whatsapp: null, entrega: 'whatsapp', estado: 'aprovada',
      criada_em: haMinutos(25 * DIA), aprovada_em: haMinutos(25 * DIA) },
    { id: 3, nome: 'Garagem Modelo', nif: '520000000', responsavel: 'Rui Modelo', email: 'rui@exemplo.pt',
      telefone: '934 567 890', whatsapp: null, entrega: 'email', estado: 'pendente',
      criada_em: haMinutos(95), aprovada_em: null }
  ];

  var movimentos = [
    { id: 1, oficina_id: 1, tokens: 25, tipo: 'carregamento', pedido_id: null, referencia: 'FT 2026/112', criado_em: haMinutos(30 * DIA) },
    { id: 2, oficina_id: 1, tokens: -5, tipo: 'pedido', pedido_id: 1043, referencia: null, criado_em: haMinutos(20 * DIA) },
    { id: 3, oficina_id: 2, tokens: 10, tipo: 'carregamento', pedido_id: null, referencia: 'FT 2026/118', criado_em: haMinutos(24 * DIA) },
    { id: 4, oficina_id: 1, tokens: -5, tipo: 'pedido', pedido_id: 1051, referencia: null, criado_em: haMinutos(300) },
    { id: 5, oficina_id: 1, tokens: -5, tipo: 'pedido', pedido_id: 1051, referencia: 'Custo final', criado_em: haMinutos(280) },
    { id: 6, oficina_id: 2, tokens: -5, tipo: 'pedido', pedido_id: 1052, referencia: null, criado_em: haMinutos(80) },
    { id: 7, oficina_id: 1, tokens: -5, tipo: 'pedido', pedido_id: 1055, referencia: null, criado_em: haMinutos(70) }
  ];

  function base(extra) {
    var p = {
      matricula: null, motor: null, ano: null, ferramenta: null, metodo: null, observacoes: null, whatsapp: null,
      original_nome: null, original_tamanho: null, modificado_nome: null, modificado_tamanho: null,
      nota: null, recebido_em: null, concluido_em: null, devolvido: false, declaracao_emissoes: false
    };
    Object.keys(extra).forEach(function (k) { p[k] = extra[k]; });
    if (p.pagos === undefined) p.pagos = p.tokens;
    if (p.custo_definido === undefined) p.custo_definido = true;
    return faltas(p);
  }

  function faltas(p) {
    p.falta = Math.max(0, p.tokens - p.pagos);
    return p;
  }

  var pedidos = [
    base({ id: 1043, oficina_id: 1, estado: 'concluido', viatura: 'Volkswagen Golf VII', matricula: 'AA-00-AA', motor: '2.0 TDI 150 cv', ano: '2017',
      ecu: 'Bosch EDC17C64', ferramenta: 'KESS3', metodo: 'OBD', modulos: ['STAGE 1/2', 'EGR OFF'], tokens: 5,
      declaracao_emissoes: true, entrega: 'portal', original_nome: 'golf7_edc17c64_original.bin', original_tamanho: 4194304,
      modificado_nome: 'golf7_edc17c64_stage1.bin', modificado_tamanho: 4194304,
      criado_em: haMinutos(20 * DIA), recebido_em: haMinutos(20 * DIA), concluido_em: haMinutos(20 * DIA - 150) }),
    base({ id: 1051, oficina_id: 1, estado: 'em_curso', viatura: 'BMW 320d F30', matricula: '00-AA-00', motor: '2.0d 184 cv', ano: '2015',
      ecu: 'Bosch EDC17C50', ferramenta: 'Autotuner', metodo: 'Bancada', modulos: ['STAGE 1/2'], tokens: 10,
      entrega: 'portal', original_nome: '320d_f30_edc17c50.bin', original_tamanho: 2097152,
      criado_em: haMinutos(300), recebido_em: haMinutos(299) }),
    base({ id: 1052, oficina_id: 2, estado: 'recebido', viatura: 'Renault Clio IV', matricula: '00-00-AA', motor: '1.5 dCi 90 cv', ano: '2018',
      ecu: 'Continental SID310', ferramenta: 'Flex', metodo: 'OBD', modulos: ['DPF OFF', 'START STOP OFF'], tokens: 5, custo_definido: false,
      declaracao_emissoes: true, entrega: 'whatsapp', whatsapp: '923 456 789',
      observacoes: 'Filtro de partículas retirado; luz de avaria acesa com P2002.',
      original_nome: 'clio4_sid310.bin', original_tamanho: 1048576, criado_em: haMinutos(80), recebido_em: haMinutos(79) }),
    base({ id: 1055, oficina_id: 1, estado: 'a_aguardar_saldo', viatura: 'Mercedes-Benz C 220 d', matricula: 'AA-11-BB', motor: '2.1 CDI 170 cv', ano: '2016',
      ecu: 'Bosch EDC17C66', ferramenta: 'KESS3', metodo: 'Boot', modulos: ['STAGE 1/2', 'TCU STAGE 1'], tokens: 12, pagos: 5,
      entrega: 'email', original_nome: 'c220d_edc17c66.bin', original_tamanho: 4194304, criado_em: haMinutos(70), recebido_em: haMinutos(69) })
  ];

  var ativa = true;
  var proximoPedido = 1060;
  var proximoMov = 10;

  function copia(x) { return JSON.parse(JSON.stringify(x)); }

  function ok(dados) {
    return new Promise(function (resolve) { setTimeout(function () { resolve(copia(dados)); }, 160); });
  }

  function falha(status, msg, extra) {
    return new Promise(function (resolve, reject) {
      setTimeout(function () {
        var e = new Error(msg);
        e.status = status;
        e.body = { erro: msg };
        Object.keys(extra || {}).forEach(function (k) { e.body[k] = extra[k]; });
        reject(e);
      }, 160);
    });
  }

  function tokensTxt(n) { return n + (Math.abs(n) === 1 ? ' token' : ' tokens'); }
  function oficina(id) { return oficinas.filter(function (o) { return o.id === Number(id); })[0]; }
  function pedido(id) { return pedidos.filter(function (p) { return p.id === Number(id); })[0]; }
  function saldo(oid) {
    return movimentos.filter(function (m) { return m.oficina_id === oid; }).reduce(function (s, m) { return s + m.tokens; }, 0);
  }
  function movimentosDe(oid) {
    return movimentos.filter(function (m) { return m.oficina_id === oid; }).sort(function (a, b) { return b.id - a.id; });
  }
  function pedidosDe(oid) {
    return pedidos.filter(function (p) { return p.oficina_id === oid; }).sort(function (a, b) { return b.id - a.id; });
  }
  function mov(oid, tokens, tipo, pedidoId, ref) {
    movimentos.push({ id: proximoMov++, oficina_id: oid, tokens: tokens, tipo: tipo, pedido_id: pedidoId || null, referencia: ref || null, criado_em: haMinutos(0) });
  }
  function devolver(p, ref) {
    if (p.devolvido) return;
    p.devolvido = true;
    if (p.pagos > 0) mov(p.oficina_id, p.pagos, 'devolucao', p.id, ref);
  }
  // Desconta a diferença do custo final se o saldo chegar. Devolve false se não chegar.
  function cobrar(p) {
    var falta = p.tokens - p.pagos;
    if (falta <= 0) return true;
    if (saldo(p.oficina_id) < falta) return false;
    mov(p.oficina_id, -falta, 'pedido', p.id, 'Custo final');
    p.pagos = p.tokens;
    faltas(p);
    return true;
  }
  function pedidoAdmin(p) {
    var r = copia(p);
    r.oficina = oficina(p.oficina_id);
    r.whatsapp_url = p.entrega === 'whatsapp' && p.whatsapp
      ? 'https://wa.me/351' + p.whatsapp.replace(/\D/g, '') + '?text=' + encodeURIComponent('Olá! O ficheiro do pedido n.º ' + p.id + ' (' + p.viatura + (p.matricula ? ', ' + p.matricula : '') + ') está pronto. Segue em anexo.')
      : null;
    return r;
  }
  function detalheOficina(o) {
    return { oficina: o, saldo: saldo(o.id), movimentos: movimentosDe(o.id), pedidos: pedidosDe(o.id) };
  }
  // Preços de exemplo (os de origem); no site, chegam pela API com a sessão.
  function precos() { return catalogo().precosDemo || { minimo: 5, tabela: [], pagamentos: [] }; }
  function sessao() {
    return ADMIN
      ? { email: 'admin@exemplo.pt', admin: true, oficina: null, saldo: 0, precos: precos() }
      : { email: oficinas[0].email, admin: false, oficina: oficinas[0], saldo: saldo(1), precos: precos() };
  }

  window.GARC_DEMO = function (caminho, opcoes) {
    var metodo = opcoes.json !== undefined ? 'POST' : (opcoes.method || 'GET');
    var corpo = opcoes.json || {};
    var url = new URL(caminho, location.href);
    var c = url.pathname.replace(/^.*\/api/, '');
    var m;

    if (c === '/sessao') return ok(ativa ? sessao() : { email: null, admin: false, oficina: null, saldo: 0 });
    if (c === '/sessao/sair') { ativa = false; return ok({ ok: true }); }
    if (c === '/entrar/codigo') return ok({ ok: true });
    if (c === '/entrar/verificar') {
      if (!/^\d{6}$/.test(corpo.codigo || '')) return falha(400, 'O código tem 6 dígitos.');
      ativa = true;
      return ok(sessao());
    }
    if (c === '/registo') return ok({ ok: true });

    if (c === '/conta' && metodo === 'GET') return ok({ oficina: oficinas[0] });
    if (c === '/conta') {
      oficinas[0].telefone = corpo.telefone;
      oficinas[0].whatsapp = corpo.whatsapp || null;
      oficinas[0].entrega = corpo.entrega;
      return ok({ oficina: oficinas[0] });
    }
    if (c === '/saldo') return ok({ saldo: saldo(1), movimentos: movimentosDe(1) });
    if (c === '/pedidos' && metodo === 'GET') return ok({ pedidos: pedidosDe(1) });
    if (c === '/pedidos') {
      var cat = catalogo().modulos;
      var custo = precos().minimo || 5;
      var emissoes = false;
      (corpo.modulos || []).forEach(function (k) {
        if (cat[k]) emissoes = emissoes || cat[k].emissoes;
      });
      var s = saldo(1);
      if (s < custo) {
        return falha(402, 'Saldo insuficiente: para enviar um pedido precisa de pelo menos ' + tokensTxt(custo) + ' e o saldo é de ' + tokensTxt(s) + '.', { saldo: s, custo: custo });
      }
      var novo = base({
        id: proximoPedido++, oficina_id: 1, estado: 'a_aguardar_ficheiro', viatura: corpo.viatura,
        matricula: (corpo.matricula || '').trim().toUpperCase() || null, motor: corpo.motor || null,
        ano: corpo.ano || null, ecu: corpo.ecu, ferramenta: corpo.ferramenta || null, metodo: corpo.metodo || null,
        modulos: corpo.modulos, tokens: custo, pagos: custo, custo_definido: false, declaracao_emissoes: emissoes, observacoes: corpo.observacoes || null,
        entrega: corpo.entrega, whatsapp: corpo.entrega === 'whatsapp' ? corpo.whatsapp : null, criado_em: haMinutos(0)
      });
      pedidos.push(novo);
      mov(1, -custo, 'pedido', novo.id);
      return ok({ pedido: novo, saldo: saldo(1) });
    }
    if ((m = /^\/pedidos\/(\d+)\/cancelar$/.exec(c))) {
      var pc = pedido(m[1]);
      if (!pc || pc.estado !== 'a_aguardar_ficheiro') return falha(409, 'Só pode cancelar um pedido antes de enviar o ficheiro.');
      pc.estado = 'cancelado';
      devolver(pc, 'Pedido cancelado pelo cliente');
      return ok({ pedido: pc, saldo: saldo(1) });
    }

    if (c === '/admin/resumo') {
      return ok({
        pedidos_por_tratar: pedidos.filter(function (p) { return p.estado === 'recebido' || p.estado === 'em_curso'; }).length,
        oficinas_pendentes: oficinas.filter(function (o) { return o.estado === 'pendente'; }).length
      });
    }
    if (c === '/admin/pedidos') {
      var f = url.searchParams.get('filtro') || 'tratar';
      var lista = pedidos.filter(function (p) {
        if (f === 'tratar') return p.estado === 'recebido' || p.estado === 'em_curso';
        if (f === 'fechado') return p.estado === 'recusado' || p.estado === 'cancelado';
        if (f === 'todos') return true;
        return p.estado === f;
      }).sort(function (a, b) { return f === 'tratar' ? a.id - b.id : b.id - a.id; });
      return ok({ pedidos: lista.map(function (p) { var r = copia(p); r.oficina_nome = oficina(p.oficina_id).nome; return r; }) });
    }
    if ((m = /^\/admin\/pedidos\/(\d+)$/.exec(c))) {
      var pa = pedido(m[1]);
      return pa ? ok({ pedido: pedidoAdmin(pa) }) : falha(404, 'Pedido não encontrado.');
    }
    if ((m = /^\/admin\/pedidos\/(\d+)\/custo$/.exec(c))) {
      var pk = pedido(m[1]);
      var minimo = precos().minimo || 5;
      var n = Number(corpo.tokens);
      if (!(n >= minimo && n <= 1000)) return falha(400, 'Indique um custo entre ' + tokensTxt(minimo) + ' e 1000 tokens.');
      if (['recebido', 'em_curso', 'a_aguardar_saldo'].indexOf(pk.estado) < 0) return falha(409, 'Só pode definir o custo de um pedido recebido, em curso ou à espera de saldo.');
      if (n < pk.pagos) { mov(pk.oficina_id, pk.pagos - n, 'devolucao', pk.id, 'Acerto do custo final'); pk.pagos = n; }
      pk.tokens = n;
      pk.custo_definido = true;
      if (!cobrar(pk)) pk.estado = 'a_aguardar_saldo';
      else if (pk.estado === 'a_aguardar_saldo') pk.estado = 'em_curso';
      faltas(pk);
      return ok({ pedido: pedidoAdmin(pk) });
    }
    if ((m = /^\/admin\/pedidos\/(\d+)\/estado$/.exec(c))) {
      var pe = pedido(m[1]);
      if (!pe) return falha(404, 'Pedido não encontrado.');
      if (corpo.acao === 'em_curso') pe.estado = 'em_curso';
      else if (corpo.acao === 'concluir') {
        if (pe.estado === 'a_aguardar_saldo') return falha(409, 'A oficina ainda não pagou o custo final: faltam ' + tokensTxt(pe.falta) + '.');
        if (!pe.modificado_nome) return falha(409, 'Carregue primeiro o ficheiro modificado.');
        pe.custo_definido = true;
        pe.estado = 'concluido';
        pe.concluido_em = haMinutos(0);
        if (corpo.nota) pe.nota = corpo.nota;
      } else if (corpo.acao === 'recusar') {
        if (!corpo.nota) return falha(400, 'Escreva o motivo da recusa para o cliente.');
        pe.estado = 'recusado';
        pe.nota = corpo.nota;
        devolver(pe, 'Pedido recusado');
      }
      return ok({ pedido: pedidoAdmin(pe) });
    }
    if (c === '/admin/oficinas') {
      var fo = url.searchParams.get('filtro') || 'pendente';
      var os = oficinas.filter(function (o) { return fo === 'todas' || o.estado === fo; });
      return ok({ oficinas: os.map(function (o) { var r = copia(o); r.saldo = saldo(o.id); return r; }) });
    }
    if ((m = /^\/admin\/oficinas\/(\d+)$/.exec(c))) {
      var od = oficina(m[1]);
      return od ? ok(detalheOficina(od)) : falha(404, 'Oficina não encontrada.');
    }
    if ((m = /^\/admin\/oficinas\/(\d+)\/estado$/.exec(c))) {
      var oe = oficina(m[1]);
      oe.estado = corpo.estado;
      if (corpo.estado === 'aprovada' && !oe.aprovada_em) oe.aprovada_em = haMinutos(0);
      return ok(detalheOficina(oe));
    }
    if ((m = /^\/admin\/oficinas\/(\d+)\/tokens$/.exec(c))) {
      var ot = oficina(m[1]);
      var n = Number(corpo.tokens);
      if (!n) return falha(400, 'Indique uma quantidade de tokens diferente de zero.');
      if (saldo(ot.id) + n < 0) return falha(409, 'O acerto deixaria o saldo negativo.');
      mov(ot.id, n, n > 0 ? 'carregamento' : 'acerto', null, corpo.referencia);
      if (n > 0) {
        pedidosDe(ot.id).filter(function (p) { return p.estado === 'a_aguardar_saldo'; })
          .sort(function (a, b) { return a.id - b.id; })
          .every(function (p) { if (!cobrar(p)) return false; p.estado = 'em_curso'; return true; });
      }
      return ok(detalheOficina(ot));
    }
    return falha(404, 'Endereço desconhecido na demonstração.');
  };

  window.GARC_DEMO_UPLOAD = function (caminho, ficheiro, progresso) {
    return new Promise(function (resolve, reject) {
      var pct = 0;
      var t = setInterval(function () {
        pct = Math.min(1, pct + 0.25);
        if (progresso) progresso(pct);
        if (pct < 1) return;
        clearInterval(t);
        var c = caminho.replace(/^.*\/api/, '');
        var m;
        if ((m = /^\/pedidos\/(\d+)\/original$/.exec(c))) {
          var p = pedido(m[1]);
          p.estado = 'recebido';
          p.original_nome = ficheiro.name;
          p.original_tamanho = ficheiro.size;
          p.recebido_em = haMinutos(0);
          resolve({ pedido: copia(p) });
        } else if ((m = /^\/admin\/pedidos\/(\d+)\/modificado$/.exec(c))) {
          var pm = pedido(m[1]);
          pm.modificado_nome = ficheiro.name;
          pm.modificado_tamanho = ficheiro.size;
          resolve({ pedido: pedidoAdmin(pm) });
        } else {
          reject(new Error('Endereço desconhecido na demonstração.'));
        }
      }, 150);
    });
  };
})();
