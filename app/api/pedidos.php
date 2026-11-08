<?php
declare(strict_types=1);

// Pedidos de ficheiro das oficinas.

const CAMPOS_PEDIDO = [
    'id', 'estado', 'viatura', 'motor', 'ano', 'ecu', 'ferramenta', 'metodo', 'tokens', 'observacoes',
    'entrega', 'whatsapp', 'original_nome', 'original_tamanho', 'modificado_nome', 'modificado_tamanho',
    'nota', 'criado_em', 'recebido_em', 'concluido_em',
];

const METODOS = ['OBD', 'Bancada', 'Boot', 'Outro'];

function pedido_publico(array $p): array
{
    $r = [];
    foreach (CAMPOS_PEDIDO as $k) {
        $r[$k] = $p[$k] ?? null;
    }
    $r['id'] = (int) $p['id'];
    $r['tokens'] = (int) $p['tokens'];
    foreach (['original_tamanho', 'modificado_tamanho'] as $k) {
        $r[$k] = $p[$k] !== null ? (int) $p[$k] : null;
    }
    $r['modulos'] = json_decode((string) $p['modulos'], true) ?: [];
    $r['declaracao_emissoes'] = (bool) $p['declaracao_emissoes'];
    return $r;
}

function nome_entrega(string $e): string
{
    return ['portal' => 'Área de cliente', 'email' => 'Email com anexo', 'whatsapp' => 'WhatsApp'][$e] ?? $e;
}

function nomes_modulos(array $p): string
{
    $cat = catalogo()['modulos'];
    $chaves = json_decode((string) $p['modulos'], true) ?: [];
    return implode(', ', array_map(fn($k) => $cat[$k]['nome'] ?? $k, $chaves));
}

function pedido_da_oficina(int $id, int $oficinaId, bool $bloquear = false): array
{
    $p = um('SELECT * FROM pedidos WHERE id = ? AND oficina_id = ?' . ($bloquear ? ' FOR UPDATE' : ''), [$id, $oficinaId]);
    if (!$p) {
        throw new ErroHttp(404, 'Pedido não encontrado.');
    }
    return $p;
}

// Devolve os tokens de um pedido uma única vez. Chamar dentro de uma transação.
function devolver_tokens(array $p, string $referencia): bool
{
    if (executar('UPDATE pedidos SET devolvido = 1 WHERE id = ? AND devolvido = 0', [$p['id']]) !== 1) {
        return false;
    }
    executar(
        "INSERT INTO movimentos (oficina_id, tokens, tipo, pedido_id, referencia) VALUES (?, ?, 'devolucao', ?, ?)",
        [$p['oficina_id'], (int) $p['tokens'], $p['id'], $referencia]
    );
    return true;
}

function api_pedidos(): array
{
    $o = exigir_cliente();
    $linhas = todos('SELECT * FROM pedidos WHERE oficina_id = ? ORDER BY id DESC LIMIT 200', [$o['id']]);
    return ['pedidos' => array_map('pedido_publico', $linhas)];
}

function api_pedido(string $id): array
{
    $o = exigir_cliente();
    return ['pedido' => pedido_publico(pedido_da_oficina((int) $id, (int) $o['id']))];
}

function api_pedido_criar(): Resposta
{
    $o = exigir_cliente();
    $c = ler_json();

    $mods = is_array($c['modulos'] ?? null) ? $c['modulos'] : [];
    $mods = array_values(array_unique(array_filter($mods, 'is_string')));
    if (!$mods) {
        throw new ErroHttp(400, 'Escolha pelo menos um módulo.');
    }
    $cat = catalogo()['modulos'];
    $custo = 0;
    $emissoes = false;
    foreach ($mods as $k) {
        if (!isset($cat[$k])) {
            throw new ErroHttp(400, 'Módulo desconhecido.');
        }
        if ($cat[$k]['tokens'] === null) {
            throw new ErroHttp(400, "O módulo {$cat[$k]['nome']} ainda não tem preço. Contacte-nos.");
        }
        $custo += (int) $cat[$k]['tokens'];
        $emissoes = $emissoes || $cat[$k]['emissoes'];
    }
    if ($emissoes && ($c['declaracao'] ?? null) !== true) {
        throw new ErroHttp(400, 'Confirme a declaração de uso dos módulos de sistemas de emissões.');
    }

    $p = [
        'viatura' => texto($c['viatura'] ?? '', 'marca e modelo', 120, true),
        'motor' => texto($c['motor'] ?? '', 'motor', 80),
        'ano' => texto($c['ano'] ?? '', 'ano', 4),
        'ecu' => texto($c['ecu'] ?? '', 'ECU', 80, true),
        'ferramenta' => texto($c['ferramenta'] ?? '', 'ferramenta', 80),
        'metodo' => texto($c['metodo'] ?? '', 'método de leitura', 20),
        'observacoes' => texto($c['observacoes'] ?? '', 'observações', 2000),
        'entrega' => entrega($c['entrega'] ?? $o['entrega']),
        'whatsapp' => telefone($c['whatsapp'] ?? '', 'número de WhatsApp'),
    ];
    if ($p['ano'] !== '' && !preg_match('/^\d{4}$/', $p['ano'])) {
        throw new ErroHttp(400, 'Indique o ano com 4 dígitos.');
    }
    if ($p['metodo'] !== '' && !in_array($p['metodo'], METODOS, true)) {
        throw new ErroHttp(400, 'Escolha o método de leitura da lista.');
    }
    $p['whatsapp'] = $p['entrega'] === 'whatsapp' ? ($p['whatsapp'] ?: ($o['whatsapp'] ?: $o['telefone'])) : '';
    if ((int) ($c['tamanho'] ?? 0) > max_mb() * 1024 * 1024) {
        throw new ErroHttp(413, 'O ficheiro tem mais de ' . max_mb() . ' MB. Comprima-o em .zip ou contacte-nos.');
    }

    $oid = (int) $o['id'];
    [$id, $saldo] = transacao(function () use ($oid, $custo, $mods, $emissoes, $p) {
        // Bloqueia a oficina para que dois pedidos em simultâneo não gastem o mesmo saldo.
        um('SELECT id FROM oficinas WHERE id = ? FOR UPDATE', [$oid]);
        $saldo = saldo($oid);
        if ($saldo < $custo) {
            throw new ErroHttp(
                402,
                'Saldo insuficiente: o pedido custa ' . tokens_txt($custo) . ' e o saldo é de ' . tokens_txt($saldo) . '.',
                ['saldo' => $saldo, 'custo' => $custo]
            );
        }
        executar(
            'INSERT INTO pedidos (oficina_id, viatura, motor, ano, ecu, ferramenta, metodo, modulos, tokens, declaracao_emissoes, observacoes, entrega, whatsapp)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                $oid, $p['viatura'], $p['motor'] ?: null, $p['ano'] ?: null, $p['ecu'], $p['ferramenta'] ?: null,
                $p['metodo'] ?: null, json_encode($mods, JSON_UNESCAPED_UNICODE), $custo, $emissoes ? 1 : 0,
                $p['observacoes'] ?: null, $p['entrega'], $p['whatsapp'] ?: null,
            ]
        );
        $id = (int) db()->lastInsertId();
        executar("INSERT INTO movimentos (oficina_id, tokens, tipo, pedido_id) VALUES (?, ?, 'pedido', ?)", [$oid, -$custo, $id]);
        return [$id, $saldo - $custo];
    });

    return new Resposta(['pedido' => pedido_publico(um('SELECT * FROM pedidos WHERE id = ?', [$id])), 'saldo' => $saldo], 201);
}

function api_pedido_cancelar(string $id): array
{
    $o = exigir_cliente();
    $saldo = transacao(function () use ($id, $o) {
        $p = pedido_da_oficina((int) $id, (int) $o['id'], true);
        if ($p['estado'] !== 'a_aguardar_ficheiro') {
            throw new ErroHttp(409, 'Só pode cancelar um pedido antes de enviar o ficheiro. Para outros casos, contacte-nos.');
        }
        executar("UPDATE pedidos SET estado = 'cancelado' WHERE id = ?", [$p['id']]);
        devolver_tokens($p, 'Pedido cancelado pelo cliente');
        return saldo((int) $o['id']);
    });
    return ['pedido' => pedido_publico(um('SELECT * FROM pedidos WHERE id = ?', [(int) $id])), 'saldo' => $saldo];
}

function api_pedido_original_enviar(string $id): array
{
    $o = exigir_cliente();
    $p = pedido_da_oficina((int) $id, (int) $o['id']);
    if ($p['estado'] !== 'a_aguardar_ficheiro') {
        throw new ErroHttp(409, 'Este pedido já tem ficheiro.');
    }
    $f = guardar_upload('ficheiro', "pedidos/{$p['id']}/original");
    $n = executar(
        "UPDATE pedidos SET estado = 'recebido', original_chave = ?, original_nome = ?, original_tamanho = ?, recebido_em = UTC_TIMESTAMP()
         WHERE id = ? AND estado = 'a_aguardar_ficheiro'",
        [$f['chave'], $f['nome'], $f['tamanho'], $p['id']]
    );
    if ($n !== 1) {
        apagar_ficheiro($f['chave']);
        throw new ErroHttp(409, 'Este pedido já tem ficheiro.');
    }
    $p = um('SELECT * FROM pedidos WHERE id = ?', [$p['id']]);
    $anexo = anexo_se_couber($p['original_chave'], $p['original_nome']);
    notificar_admins(
        "Novo pedido n.º {$p['id']}: {$p['viatura']}",
        "Oficina: {$o['nome']}\nViatura: {$p['viatura']}" . ($p['motor'] ? " ({$p['motor']})" : '')
        . "\nECU: {$p['ecu']}\nMódulos: " . nomes_modulos($p) . "\nTokens: {$p['tokens']}\nEntrega: " . nome_entrega($p['entrega'])
        . ($p['observacoes'] ? "\n\nObservações:\n{$p['observacoes']}" : '')
        . "\n\nAbrir no painel:\n" . site_url() . "/admin#pedido-{$p['id']}"
        . ($anexo ? '' : "\n\nO ficheiro original está no painel (grande demais para seguir em anexo)."),
        $anexo ? [$anexo] : []
    );
    return ['pedido' => pedido_publico($p)];
}

function api_pedido_ficheiro(string $id, string $tipo): ?array
{
    $s = obter_sessao();
    if (!$s) {
        throw new ErroHttp(401, 'A sessão terminou. Entre de novo na área de cliente.');
    }
    $p = um('SELECT * FROM pedidos WHERE id = ?', [(int) $id]);
    $dono = $p && $s['oficina'] && $s['oficina']['estado'] === 'aprovada' && (int) $s['oficina']['id'] === (int) $p['oficina_id'];
    if (!$p || (!$s['admin'] && !$dono)) {
        throw new ErroHttp(404, 'Pedido não encontrado.');
    }
    if ($tipo === 'modificado' && !$s['admin'] && $p['estado'] !== 'concluido') {
        throw new ErroHttp(409, 'O ficheiro ainda não está pronto.');
    }
    if (!$p[$tipo . '_chave']) {
        throw new ErroHttp(404, 'Ficheiro não encontrado.');
    }
    servir_ficheiro($p[$tipo . '_chave'], $p[$tipo . '_nome']);
    return null;
}
