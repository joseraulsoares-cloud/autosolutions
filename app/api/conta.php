<?php
declare(strict_types=1);

// Sessão, entrada por código, registo, conta, saldo e formulário de contacto.

function api_sessao(): array
{
    $s = obter_sessao();
    if (!$s) {
        return ['email' => null, 'admin' => false, 'oficina' => null, 'saldo' => 0];
    }
    return resumo_sessao($s);
}

function api_sair(): array
{
    terminar_sessao();
    return ['ok' => true];
}

function limpar_registos_antigos(): void
{
    executar('DELETE FROM codigos WHERE criado_em < ?', [time() - 86400]);
    executar('DELETE FROM sessoes WHERE expira_em < ?', [time()]);
}

function api_entrar_codigo(): array
{
    $c = ler_json();
    $email = normalizar_email($c['email'] ?? '');
    limitar('codigo');
    $t = time();
    limpar_registos_antigos();
    $recentes = (int) valor('SELECT COUNT(*) FROM codigos WHERE email = ? AND criado_em > ?', [$email, $t - 900]);
    if ($recentes >= 3) {
        throw new ErroHttp(429, 'Pediu vários códigos seguidos. Aguarde alguns minutos e tente de novo.');
    }
    $o = oficina_por_email($email);
    $admin = e_admin($email);
    if ($admin || ($o && $o['estado'] === 'aprovada')) {
        $codigo = codigo_numerico();
        executar(
            'INSERT INTO codigos (email, hash, expira_em, criado_em) VALUES (?, ?, ?, ?)',
            [$email, hash_codigo($email, $codigo), $t + 600, $t]
        );
        $pagina = $admin ? 'admin' : 'area-cliente';
        $link = site_url() . "/$pagina?email=" . rawurlencode($email) . "&codigo=$codigo";
        try {
            enviar_email(
                $email,
                "Código de acesso: $codigo",
                "O seu código de acesso é $codigo.\n\nÉ válido durante 10 minutos. Também pode entrar diretamente por este link:\n$link\n\nSe não pediu este código, ignore este email." . assinatura_email()
            );
        } catch (Throwable $e) {
            error_log('GARC: falha no envio do código de acesso: ' . $e->getMessage());
            throw new ErroHttp(502, 'Não foi possível enviar o código. Tente de novo dentro de momentos.');
        }
    } elseif ($o && $o['estado'] === 'pendente') {
        // Conta para o limite de pedidos, mas nunca é válido.
        executar('INSERT INTO codigos (email, hash, expira_em, criado_em) VALUES (?, ?, 0, ?)', [$email, str_repeat('0', 64), $t]);
        notificar(
            $email,
            'A sua conta aguarda aprovação',
            "Recebemos o registo de {$o['nome']} e a conta ainda aguarda aprovação. Vai receber um email assim que for aprovada." . assinatura_email()
        );
    }
    return ['ok' => true];
}

function api_entrar_verificar(): array
{
    $c = ler_json();
    $email = normalizar_email($c['email'] ?? '');
    $codigo = trim((string) ($c['codigo'] ?? ''));
    if (!preg_match('/^\d{6}$/', $codigo)) {
        throw new ErroHttp(400, 'O código tem 6 dígitos.');
    }
    $linha = um('SELECT id, hash, tentativas FROM codigos WHERE email = ? AND expira_em > ? ORDER BY id DESC LIMIT 1', [$email, time()]);
    if (!$linha || (int) $linha['tentativas'] >= 5) {
        throw new ErroHttp(400, 'Código errado ou expirado. Peça um novo código.');
    }
    if (!hash_equals($linha['hash'], hash_codigo($email, $codigo))) {
        executar('UPDATE codigos SET tentativas = tentativas + 1 WHERE id = ?', [$linha['id']]);
        throw new ErroHttp(400, 'Código errado ou expirado. Confirme os dígitos ou peça um novo código.');
    }
    executar('DELETE FROM codigos WHERE email = ?', [$email]);
    $o = oficina_por_email($email);
    $admin = e_admin($email);
    if (!$admin && !($o && $o['estado'] === 'aprovada')) {
        throw new ErroHttp(403, 'A conta não está ativa. Contacte-nos.');
    }
    criar_sessao($email);
    return resumo_sessao(['email' => $email, 'admin' => $admin, 'oficina' => $o]);
}

function api_registo(): Resposta
{
    $c = ler_json();
    if (!empty($c['website'])) {
        return new Resposta(['ok' => true], 201); // campo-armadilha preenchido: robô
    }
    if (($c['termos'] ?? null) !== true) {
        throw new ErroHttp(400, 'Aceite os termos de utilização para criar a conta.');
    }
    $d = [
        'nome' => texto($c['nome'] ?? '', 'oficina ou empresa', 120, true),
        'nif' => validar_nif($c['nif'] ?? ''),
        'responsavel' => texto($c['responsavel'] ?? '', 'nome do responsável', 120, true),
        'email' => normalizar_email($c['email'] ?? ''),
        'telefone' => telefone($c['telefone'] ?? '', 'telefone', true),
        'whatsapp' => telefone($c['whatsapp'] ?? '', 'número de WhatsApp'),
        'entrega' => entrega($c['entrega'] ?? 'portal'),
    ];
    $existe = um('SELECT email, nif FROM oficinas WHERE email = ? OR nif = ?', [$d['email'], $d['nif']]);
    if ($existe) {
        throw new ErroHttp(409, $existe['email'] === $d['email']
            ? 'Já existe uma conta com este email. Entre na área de cliente.'
            : 'Já existe uma conta com este NIF. Contacte-nos se precisar de outro acesso.');
    }
    limitar('registo');
    try {
        executar(
            'INSERT INTO oficinas (nome, nif, responsavel, email, telefone, whatsapp, entrega) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [$d['nome'], $d['nif'], $d['responsavel'], $d['email'], $d['telefone'], $d['whatsapp'] ?: null, $d['entrega']]
        );
    } catch (PDOException $e) {
        if ((int) ($e->errorInfo[1] ?? 0) === 1062) {
            throw new ErroHttp(409, 'Já existe uma conta com este email ou NIF.');
        }
        throw $e;
    }
    notificar(
        $d['email'],
        'Recebemos o seu registo',
        "Olá {$d['responsavel']},\n\nRecebemos o registo de {$d['nome']} na área de cliente. Vamos analisar o pedido e enviamos um email quando a conta estiver aprovada." . assinatura_email()
    );
    notificar_admins(
        "Novo registo: {$d['nome']}",
        "Oficina: {$d['nome']}\nNIF: {$d['nif']}\nResponsável: {$d['responsavel']}\nEmail: {$d['email']}\nTelefone: {$d['telefone']}\n\nAprovar no painel:\n" . site_url() . '/admin#oficinas'
    );
    return new Resposta(['ok' => true], 201);
}

function api_conta(): array
{
    return ['oficina' => oficina_publica(exigir_cliente())];
}

function api_conta_guardar(): array
{
    $o = exigir_cliente();
    $c = ler_json();
    $tel = telefone($c['telefone'] ?? '', 'telefone', true);
    $wa = telefone($c['whatsapp'] ?? '', 'número de WhatsApp');
    $ent = entrega($c['entrega'] ?? $o['entrega']);
    executar('UPDATE oficinas SET telefone = ?, whatsapp = ?, entrega = ? WHERE id = ?', [$tel, $wa ?: null, $ent, $o['id']]);
    return ['oficina' => oficina_publica(um('SELECT * FROM oficinas WHERE id = ?', [$o['id']]))];
}

function movimento_publico(array $m): array
{
    return [
        'id' => (int) $m['id'],
        'tokens' => (int) $m['tokens'],
        'tipo' => $m['tipo'],
        'pedido_id' => $m['pedido_id'] !== null ? (int) $m['pedido_id'] : null,
        'referencia' => $m['referencia'],
        'criado_em' => $m['criado_em'],
    ];
}

function api_saldo(): array
{
    $o = exigir_cliente();
    $movs = todos('SELECT * FROM movimentos WHERE oficina_id = ? ORDER BY id DESC LIMIT 200', [$o['id']]);
    return ['saldo' => saldo((int) $o['id']), 'movimentos' => array_map('movimento_publico', $movs)];
}

function api_contacto(): array
{
    if (!empty($_POST['website'])) {
        return ['ok' => true]; // campo-armadilha preenchido: robô
    }
    if (($_POST['privacidade'] ?? '') !== 'sim') {
        throw new ErroHttp(400, 'Confirme que leu a política de privacidade.');
    }
    $nome = trim(texto($_POST['nome'] ?? '', 'nome', 80, true) . ' ' . texto($_POST['apelido'] ?? '', 'apelido', 80));
    $email = normalizar_email($_POST['email'] ?? '');
    $tel = telefone($_POST['telefone'] ?? '');
    $assunto = texto($_POST['assunto'] ?? '', 'assunto', 150);
    $msg = texto($_POST['mensagem'] ?? '', 'mensagem', 5000, true);
    $destino = (string) (cfg('email_contacto') ?: (emails_admin()[0] ?? ''));
    if ($destino === '') {
        throw new RuntimeException('Configuração: sem destino para o formulário de contacto.');
    }
    limitar('contacto');
    try {
        enviar_email(
            $destino,
            'Contacto do site: ' . ($assunto !== '' ? $assunto : $nome),
            "Nome: $nome\nEmail: $email\nTelefone: " . ($tel !== '' ? $tel : '-') . "\nAssunto: " . ($assunto !== '' ? $assunto : '-') . "\n\n$msg",
            [],
            $email
        );
    } catch (Throwable $e) {
        error_log('GARC: falha no envio do contacto: ' . $e->getMessage());
        throw new ErroHttp(502, 'Não foi possível enviar a mensagem. Tente de novo ou contacte-nos por telefone.');
    }
    return ['ok' => true];
}

function api_dev_emails(): array
{
    if (!cfg('dev')) {
        throw new ErroHttp(404, 'Endereço desconhecido.');
    }
    return ['emails' => todos('SELECT * FROM emails_dev ORDER BY id DESC LIMIT 50')];
}
