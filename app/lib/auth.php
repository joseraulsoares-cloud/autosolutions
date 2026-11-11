<?php
declare(strict_types=1);

const COOKIE_SESSAO = 'garc_sessao';
const DURACAO_SESSAO = 30 * 24 * 3600;

function emails_admin(): array
{
    $lista = array_map(fn($e) => strtolower(trim($e)), explode(',', (string) cfg('admin_emails')));
    return array_values(array_filter($lista));
}

function e_admin(string $email): bool
{
    return in_array($email, emails_admin(), true);
}

function definir_cookie(string $valor, int $duracao): void
{
    setcookie(COOKIE_SESSAO, $valor, [
        'expires' => $duracao > 0 ? time() + $duracao : time() - 3600,
        'path' => '/',
        'secure' => e_https(),
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

function oficina_por_email(string $email): ?array
{
    return um('SELECT * FROM oficinas WHERE email = ?', [$email]);
}

function obter_sessao(): ?array
{
    static $cache = false;
    if ($cache !== false) {
        return $cache;
    }
    $id = $_COOKIE[COOKIE_SESSAO] ?? '';
    if (!is_string($id) || !preg_match('/^[0-9a-f]{64}$/', $id)) {
        return $cache = null;
    }
    $email = valor('SELECT email FROM sessoes WHERE hash = ? AND expira_em > ?', [hash('sha256', $id), time()]);
    if (!$email) {
        return $cache = null;
    }
    return $cache = ['email' => $email, 'admin' => e_admin($email), 'oficina' => oficina_por_email($email)];
}

function criar_sessao(string $email): void
{
    $id = aleatorio(32);
    executar('INSERT INTO sessoes (hash, email, expira_em) VALUES (?, ?, ?)', [hash('sha256', $id), $email, time() + DURACAO_SESSAO]);
    definir_cookie($id, DURACAO_SESSAO);
}

function terminar_sessao(): void
{
    $id = $_COOKIE[COOKIE_SESSAO] ?? '';
    if (is_string($id) && preg_match('/^[0-9a-f]{64}$/', $id)) {
        executar('DELETE FROM sessoes WHERE hash = ?', [hash('sha256', $id)]);
    }
    definir_cookie('', 0);
}

function exigir_cliente(): array
{
    $s = obter_sessao();
    if (!$s) {
        throw new ErroHttp(401, 'A sessão terminou. Entre de novo na área de cliente.');
    }
    if (!$s['oficina'] || $s['oficina']['estado'] !== 'aprovada') {
        throw new ErroHttp(403, 'A conta não está ativa. Contacte-nos.');
    }
    return $s['oficina'];
}

function exigir_admin(): array
{
    $s = obter_sessao();
    if (!$s) {
        throw new ErroHttp(401, 'A sessão terminou. Entre de novo.');
    }
    if (!$s['admin']) {
        throw new ErroHttp(403, 'Sem acesso a esta área.');
    }
    return $s;
}

function hash_codigo(string $email, string $codigo): string
{
    return hash_hmac('sha256', "$email:$codigo", segredo());
}

function oficina_publica(?array $o): ?array
{
    if (!$o) {
        return null;
    }
    return [
        'id' => (int) $o['id'],
        'nome' => $o['nome'],
        'nif' => $o['nif'],
        'responsavel' => $o['responsavel'],
        'email' => $o['email'],
        'telefone' => $o['telefone'],
        'whatsapp' => $o['whatsapp'],
        'entrega' => $o['entrega'],
        'estado' => $o['estado'],
        'criada_em' => $o['criada_em'],
        'aprovada_em' => $o['aprovada_em'],
    ];
}

function resumo_sessao(array $s): array
{
    $r = [
        'email' => $s['email'],
        'admin' => $s['admin'],
        'oficina' => oficina_publica($s['oficina']),
        'saldo' => $s['oficina'] ? saldo((int) $s['oficina']['id']) : 0,
    ];
    // Os preços só seguem para o administrador e para contas aprovadas (não estão no HTML público).
    if ($s['admin'] || ($s['oficina']['estado'] ?? '') === 'aprovada') {
        $r['precos'] = garc_precos();
    }
    return $r;
}
