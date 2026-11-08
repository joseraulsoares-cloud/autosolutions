<?php
declare(strict_types=1);

// Painel de administração: oficinas, tokens e pedidos.

function pedido_admin(array $p): array
{
    $r = pedido_publico($p);
    $r['oficina'] = oficina_publica(um('SELECT * FROM oficinas WHERE id = ?', [$p['oficina_id']]));
    $r['devolvido'] = (bool) $p['devolvido'];
    $r['whatsapp_url'] = link_whatsapp($p);
    return $r;
}

function link_whatsapp(array $p): ?string
{
    if ($p['entrega'] !== 'whatsapp' || !$p['whatsapp']) {
        return null;
    }
    $msg = "Olá! O ficheiro do pedido n.º {$p['id']} (" . viatura_txt($p) . ") está pronto. Segue em anexo.";
    return 'https://wa.me/' . numero_whatsapp($p['whatsapp']) . '?text=' . rawurlencode($msg);
}

function api_admin_resumo(): array
{
    exigir_admin();
    limpar_pedidos_antigos();
    return [
        'pedidos_por_tratar' => (int) valor("SELECT COUNT(*) FROM pedidos WHERE estado IN ('recebido', 'em_curso')"),
        'oficinas_pendentes' => (int) valor("SELECT COUNT(*) FROM oficinas WHERE estado = 'pendente'"),
    ];
}

function api_admin_pedidos(): array
{
    exigir_admin();
    $filtro = (string) ($_GET['filtro'] ?? 'tratar');
    $onde = match ($filtro) {
        'tratar' => "p.estado IN ('recebido', 'em_curso')",
        'a_aguardar_ficheiro' => "p.estado = 'a_aguardar_ficheiro'",
        'a_aguardar_saldo' => "p.estado = 'a_aguardar_saldo'",
        'concluido' => "p.estado = 'concluido'",
        'fechado' => "p.estado IN ('recusado', 'cancelado')",
        'todos' => '1 = 1',
        default => throw new ErroHttp(400, 'Filtro inválido.'),
    };
    $ordem = $filtro === 'tratar' ? 'p.id ASC' : 'p.id DESC';
    $linhas = todos("SELECT p.*, o.nome AS oficina_nome FROM pedidos p JOIN oficinas o ON o.id = p.oficina_id WHERE $onde ORDER BY $ordem LIMIT 300");
    return ['pedidos' => array_map(
        fn($p) => pedido_publico($p) + ['oficina_id' => (int) $p['oficina_id'], 'oficina_nome' => $p['oficina_nome']],
        $linhas
    )];
}

function api_admin_pedido(string $id): array
{
    exigir_admin();
    $p = um('SELECT * FROM pedidos WHERE id = ?', [(int) $id]);
    if (!$p) {
        throw new ErroHttp(404, 'Pedido não encontrado.');
    }
    return ['pedido' => pedido_admin($p)];
}

function api_admin_pedido_estado(string $id): array
{
    exigir_admin();
    $c = ler_json();
    $acao = (string) ($c['acao'] ?? '');
    $nota = texto($c['nota'] ?? '', 'mensagem para o cliente', 2000);

    $p = transacao(function () use ($id, $acao, $nota) {
        $p = um('SELECT * FROM pedidos WHERE id = ? FOR UPDATE', [(int) $id]);
        if (!$p) {
            throw new ErroHttp(404, 'Pedido não encontrado.');
        }
        switch ($acao) {
            case 'em_curso':
                if ($p['estado'] !== 'recebido') {
                    throw new ErroHttp(409, 'Só um pedido recebido pode passar a em curso.');
                }
                executar("UPDATE pedidos SET estado = 'em_curso' WHERE id = ?", [$p['id']]);
                break;
            case 'concluir':
                if ($p['estado'] === 'a_aguardar_saldo') {
                    throw new ErroHttp(409, 'A oficina ainda não pagou o custo final: faltam '
                        . tokens_txt((int) $p['tokens'] - (int) $p['pagos']) . '. O pedido avança quando carregar o saldo.');
                }
                if (!in_array($p['estado'], ['recebido', 'em_curso', 'concluido'], true)) {
                    throw new ErroHttp(409, 'Este pedido não pode ser concluído.');
                }
                if (!$p['modificado_chave']) {
                    throw new ErroHttp(409, 'Carregue primeiro o ficheiro modificado.');
                }
                // Concluir sem definir o custo final aceita como final o que já foi pago.
                executar(
                    "UPDATE pedidos SET estado = 'concluido', concluido_em = UTC_TIMESTAMP(), fechado_em = UTC_TIMESTAMP(),
                     custo_definido = 1, nota = ? WHERE id = ?",
                    [$nota !== '' ? $nota : $p['nota'], $p['id']]
                );
                break;
            case 'recusar':
                if (!in_array($p['estado'], ['a_aguardar_ficheiro', 'recebido', 'em_curso', 'a_aguardar_saldo'], true)) {
                    throw new ErroHttp(409, 'Este pedido já não pode ser recusado.');
                }
                if ($nota === '') {
                    throw new ErroHttp(400, 'Escreva o motivo da recusa para o cliente.');
                }
                executar("UPDATE pedidos SET estado = 'recusado', fechado_em = UTC_TIMESTAMP(), nota = ? WHERE id = ?", [$nota, $p['id']]);
                devolver_tokens($p, 'Pedido recusado');
                break;
            default:
                throw new ErroHttp(400, 'Ação desconhecida.');
        }
        return um('SELECT * FROM pedidos WHERE id = ?', [$p['id']]);
    });

    $o = um('SELECT * FROM oficinas WHERE id = ?', [$p['oficina_id']]);
    $area = site_url() . '/area-cliente#pedidos';
    if ($acao === 'concluir') {
        $anexo = $p['entrega'] === 'email' ? anexo_se_couber($p['modificado_chave'], $p['modificado_nome']) : null;
        $texto = "O ficheiro do pedido n.º {$p['id']} (" . viatura_txt($p) . ") está pronto.\n\n"
            . ($anexo ? "Segue em anexo e fica também disponível na área de cliente:\n$area" : "Pode descarregá-lo na área de cliente:\n$area")
            . ($p['nota'] ? "\n\nNota:\n{$p['nota']}" : '')
            . assinatura_email();
        notificar($o['email'], "Ficheiro pronto: pedido n.º {$p['id']}", $texto, $anexo ? [$anexo] : []);
    } elseif ($acao === 'recusar') {
        $devolvidos = (int) $p['tokens'] === 1
            ? 'O token do pedido voltou ao saldo.'
            : 'Os ' . tokens_txt((int) $p['tokens']) . ' do pedido voltaram ao saldo.';
        notificar(
            $o['email'],
            "Pedido n.º {$p['id']} recusado",
            "Não foi possível tratar o pedido n.º {$p['id']} (" . viatura_txt($p) . ").\n\nMotivo:\n{$p['nota']}\n\n$devolvidos\n$area" . assinatura_email()
        );
    }
    return ['pedido' => pedido_admin($p)];
}

/**
 * Define o custo final de um pedido depois de analisada a ECU. A diferença para o que já foi pago é descontada
 * do saldo; se o saldo não chegar, o pedido fica à espera de saldo e avança sozinho quando a oficina carregar.
 * Baixar o custo devolve a diferença ao saldo. O custo nunca fica abaixo dos tokens mínimos do envio.
 */
function api_admin_pedido_custo(string $id): array
{
    exigir_admin();
    $c = ler_json();
    $novo = inteiro($c['tokens'] ?? null);
    $minimo = tokens_minimo();
    if ($novo < $minimo || $novo > 1000) {
        throw new ErroHttp(400, 'Indique um custo entre ' . tokens_txt($minimo) . ' e 1000 tokens.');
    }
    $base = um('SELECT id, oficina_id FROM pedidos WHERE id = ?', [(int) $id]);
    if (!$base) {
        throw new ErroHttp(404, 'Pedido não encontrado.');
    }
    [$p, $cobrado, $devolvido] = transacao(function () use ($base, $novo) {
        // Mesma ordem de bloqueio que nos carregamentos: primeiro a oficina, depois o pedido.
        um('SELECT id FROM oficinas WHERE id = ? FOR UPDATE', [$base['oficina_id']]);
        $p = um('SELECT * FROM pedidos WHERE id = ? FOR UPDATE', [$base['id']]);
        if (!in_array($p['estado'], ['recebido', 'em_curso', 'a_aguardar_saldo'], true)) {
            throw new ErroHttp(409, 'Só pode definir o custo de um pedido recebido, em curso ou à espera de saldo.');
        }
        $pagos = (int) $p['pagos'];
        $devolvido = 0;
        if ($novo < $pagos) {
            $devolvido = $pagos - $novo;
            executar(
                "INSERT INTO movimentos (oficina_id, tokens, tipo, pedido_id, referencia) VALUES (?, ?, 'devolucao', ?, 'Acerto do custo final')",
                [$p['oficina_id'], $devolvido, $p['id']]
            );
            $pagos = $novo;
        }
        executar('UPDATE pedidos SET tokens = ?, pagos = ?, custo_definido = 1 WHERE id = ?', [$novo, $pagos, $p['id']]);
        $p = um('SELECT * FROM pedidos WHERE id = ?', [$p['id']]);
        $cobrado = cobrar_diferenca($p);
        if ($cobrado === null) {
            executar("UPDATE pedidos SET estado = 'a_aguardar_saldo' WHERE id = ?", [$p['id']]);
        } elseif ($p['estado'] === 'a_aguardar_saldo') {
            executar("UPDATE pedidos SET estado = 'em_curso' WHERE id = ?", [$p['id']]);
        }
        return [um('SELECT * FROM pedidos WHERE id = ?', [$p['id']]), $cobrado, $devolvido];
    });

    $o = um('SELECT * FROM oficinas WHERE id = ?', [$p['oficina_id']]);
    $pedido = "pedido n.º {$p['id']} (" . viatura_txt($p) . ')';
    $custo = tokens_txt((int) $p['tokens']);
    if ($cobrado === null) {
        $falta = (int) $p['tokens'] - (int) $p['pagos'];
        $saldo = saldo((int) $o['id']);
        notificar(
            $o['email'],
            "Pedido n.º {$p['id']}: falta saldo",
            "Analisámos a ECU do $pedido. O custo final é de $custo e já foram descontados " . tokens_txt((int) $p['pagos']) . ".\n\n"
            . 'Faltam ' . tokens_txt($falta) . ' e o saldo atual é de ' . tokens_txt($saldo) . '. Carregue pelo menos '
            . tokens_txt($falta - $saldo) . " para o pedido avançar. A diferença é descontada automaticamente.\n"
            . site_url() . '/area-cliente#saldo' . assinatura_email()
        );
    } elseif ($cobrado > 0 || $devolvido > 0) {
        $mov = $cobrado > 0
            ? 'Foram descontados mais ' . tokens_txt($cobrado) . ' do saldo.'
            : 'Voltaram ao saldo ' . tokens_txt($devolvido) . '.';
        notificar(
            $o['email'],
            "Pedido n.º {$p['id']}: custo final",
            "Analisámos a ECU do $pedido. O custo final é de $custo. $mov\n" . site_url() . '/area-cliente#pedidos' . assinatura_email()
        );
    }
    return ['pedido' => pedido_admin($p)];
}

function api_admin_pedido_modificado(string $id): array
{
    exigir_admin();
    $p = um('SELECT * FROM pedidos WHERE id = ?', [(int) $id]);
    if (!$p) {
        throw new ErroHttp(404, 'Pedido não encontrado.');
    }
    if (!in_array($p['estado'], ['recebido', 'em_curso', 'a_aguardar_saldo', 'concluido'], true)) {
        throw new ErroHttp(409, 'Só pode carregar o ficheiro modificado de um pedido recebido, em curso, à espera de saldo ou concluído.');
    }
    $f = guardar_upload('ficheiro', "pedidos/{$p['id']}/modificado");
    if ($p['modificado_chave'] && $p['modificado_chave'] !== $f['chave']) {
        apagar_ficheiro($p['modificado_chave']);
    }
    executar(
        'UPDATE pedidos SET modificado_chave = ?, modificado_nome = ?, modificado_tamanho = ? WHERE id = ?',
        [$f['chave'], $f['nome'], $f['tamanho'], $p['id']]
    );
    return ['pedido' => pedido_admin(um('SELECT * FROM pedidos WHERE id = ?', [$p['id']]))];
}

function api_admin_oficinas(): array
{
    exigir_admin();
    $filtro = (string) ($_GET['filtro'] ?? 'pendente');
    $onde = match ($filtro) {
        'pendente' => "o.estado = 'pendente'",
        'aprovada' => "o.estado = 'aprovada'",
        'todas' => '1 = 1',
        default => throw new ErroHttp(400, 'Filtro inválido.'),
    };
    $linhas = todos(
        "SELECT o.*, COALESCE((SELECT SUM(m.tokens) FROM movimentos m WHERE m.oficina_id = o.id), 0) AS saldo
         FROM oficinas o WHERE $onde ORDER BY o.nome LIMIT 500"
    );
    return ['oficinas' => array_map(fn($o) => oficina_publica($o) + ['saldo' => (int) $o['saldo']], $linhas)];
}

function api_admin_oficina(string $id): array
{
    exigir_admin();
    $o = um('SELECT * FROM oficinas WHERE id = ?', [(int) $id]);
    if (!$o) {
        throw new ErroHttp(404, 'Oficina não encontrada.');
    }
    return [
        'oficina' => oficina_publica($o),
        'saldo' => saldo((int) $o['id']),
        'movimentos' => array_map('movimento_publico', todos('SELECT * FROM movimentos WHERE oficina_id = ? ORDER BY id DESC LIMIT 100', [$o['id']])),
        'pedidos' => array_map('pedido_publico', todos('SELECT * FROM pedidos WHERE oficina_id = ? ORDER BY id DESC LIMIT 50', [$o['id']])),
    ];
}

function api_admin_oficina_estado(string $id): array
{
    exigir_admin();
    $c = ler_json();
    $estado = (string) ($c['estado'] ?? '');
    if (!in_array($estado, ['aprovada', 'recusada', 'suspensa'], true)) {
        throw new ErroHttp(400, 'Estado inválido.');
    }
    $o = um('SELECT * FROM oficinas WHERE id = ?', [(int) $id]);
    if (!$o) {
        throw new ErroHttp(404, 'Oficina não encontrada.');
    }
    if ($o['estado'] !== $estado) {
        executar(
            "UPDATE oficinas SET estado = ?, aprovada_em = IF(? = 'aprovada' AND aprovada_em IS NULL, UTC_TIMESTAMP(), aprovada_em) WHERE id = ?",
            [$estado, $estado, $o['id']]
        );
        if ($estado === 'aprovada') {
            $primeira = $o['aprovada_em'] === null;
            notificar(
                $o['email'],
                $primeira ? 'A sua conta foi aprovada' : 'A sua conta foi reativada',
                "Olá {$o['responsavel']},\n\nA conta de {$o['nome']} na área de cliente está ativa. Para entrar, indique o email {$o['email']} e o código que lhe enviamos nesse momento:\n"
                . site_url() . "/area-cliente\n\nPara enviar pedidos precisa de saldo de tokens. Os dados de pagamento estão na área de cliente, em Saldo." . assinatura_email()
            );
        } else {
            executar('DELETE FROM sessoes WHERE email = ?', [$o['email']]);
        }
    }
    return api_admin_oficina($id);
}

function api_admin_oficina_tokens(string $id): array
{
    exigir_admin();
    $c = ler_json();
    $tokens = inteiro($c['tokens'] ?? null);
    if ($tokens === 0 || abs($tokens) > 100000) {
        throw new ErroHttp(400, 'Indique uma quantidade de tokens diferente de zero.');
    }
    $ref = texto($c['referencia'] ?? '', 'referência', 120);
    $o = um('SELECT * FROM oficinas WHERE id = ?', [(int) $id]);
    if (!$o) {
        throw new ErroHttp(404, 'Oficina não encontrada.');
    }
    [$saldo, $liquidados] = transacao(function () use ($o, $tokens, $ref) {
        um('SELECT id FROM oficinas WHERE id = ? FOR UPDATE', [$o['id']]);
        $atual = saldo((int) $o['id']);
        if ($atual + $tokens < 0) {
            throw new ErroHttp(409, 'O acerto deixaria o saldo negativo. Saldo atual: ' . tokens_txt($atual) . '.');
        }
        executar(
            'INSERT INTO movimentos (oficina_id, tokens, tipo, referencia) VALUES (?, ?, ?, ?)',
            [$o['id'], $tokens, $tokens > 0 ? 'carregamento' : 'acerto', $ref !== '' ? $ref : null]
        );
        // Pedidos à espera de saldo avançam por ordem de chegada, enquanto o saldo chegar.
        $liquidados = [];
        if ($tokens > 0) {
            $espera = todos("SELECT * FROM pedidos WHERE oficina_id = ? AND estado = 'a_aguardar_saldo' ORDER BY id FOR UPDATE", [$o['id']]);
            foreach ($espera as $p) {
                $cobrado = cobrar_diferenca($p);
                if ($cobrado === null) {
                    break;
                }
                executar("UPDATE pedidos SET estado = 'em_curso' WHERE id = ?", [$p['id']]);
                $liquidados[] = "Pedido n.º {$p['id']} (" . viatura_txt($p) . '): descontados ' . tokens_txt($cobrado) . ' do custo final; o pedido avançou.';
            }
        }
        return [saldo((int) $o['id']), $liquidados];
    });
    if ($tokens > 0) {
        notificar(
            $o['email'],
            'Saldo carregado: ' . tokens_txt($tokens),
            'Foram carregados ' . tokens_txt($tokens) . " na conta de {$o['nome']}" . ($ref !== '' ? " (referência: $ref)" : '')
            . ".\n\n" . ($liquidados ? implode("\n", $liquidados) . "\n\n" : '')
            . 'Saldo atual: ' . tokens_txt($saldo) . ".\n" . site_url() . '/area-cliente#saldo' . assinatura_email()
        );
    }
    return api_admin_oficina($id);
}
