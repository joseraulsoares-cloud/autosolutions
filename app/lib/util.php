<?php
declare(strict_types=1);

// A API corre a partir do PHP 7.4 (o mais recente do alojamento enquanto não houver PHP 8 corrigido):
// sem match, sem promoção de propriedades no construtor e sem as funções novas do PHP 8.

final class ErroHttp extends Exception
{
    public int $status;
    public array $extra;

    public function __construct(int $status, string $mensagem, array $extra = [])
    {
        parent::__construct($mensagem);
        $this->status = $status;
        $this->extra = $extra;
    }
}

final class Resposta
{
    public array $dados;
    public int $status;

    public function __construct(array $dados, int $status = 200)
    {
        $this->dados = $dados;
        $this->status = $status;
    }
}

function responder_json(array $dados, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($dados, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

// Tarefas que correm depois de a resposta seguir (emails).
function depois(callable $tarefa): void
{
    $GLOBALS['garc_depois'][] = $tarefa;
}

function executar_depois(): void
{
    $fila = $GLOBALS['garc_depois'] ?? [];
    $GLOBALS['garc_depois'] = [];
    if (!$fila) {
        return;
    }
    ignore_user_abort(true);
    if (function_exists('fastcgi_finish_request')) {
        fastcgi_finish_request();
    } elseif (function_exists('litespeed_finish_request')) {
        litespeed_finish_request();
    }
    foreach ($fila as $tarefa) {
        try {
            $tarefa();
        } catch (Throwable $e) {
            error_log('GARC (tarefa depois da resposta): ' . $e->getMessage());
        }
    }
}

function ler_json(): array
{
    $tipo = $_SERVER['CONTENT_TYPE'] ?? '';
    if (stripos($tipo, 'application/json') === false) {
        throw new ErroHttp(415, 'Formato de pedido inválido.');
    }
    $txt = file_get_contents('php://input', false, null, 0, 20001);
    if ($txt === false || strlen($txt) > 20000) {
        throw new ErroHttp(413, 'Pedido demasiado grande.');
    }
    $d = json_decode($txt === '' ? '{}' : $txt, true);
    // o corpo tem de ser um objeto JSON, não uma lista
    if (!is_array($d) || ($d !== [] && array_keys($d) === range(0, count($d) - 1))) {
        throw new ErroHttp(400, 'Pedido inválido.');
    }
    return $d;
}

function comprimento(string $v): int
{
    return function_exists('mb_strlen') ? mb_strlen($v, 'UTF-8') : (int) preg_match_all('/./us', $v);
}

function texto($valor, string $nome, int $max = 200, bool $obrigatorio = false): string
{
    $v = is_scalar($valor) ? trim((string) $valor) : '';
    if ($obrigatorio && $v === '') {
        throw new ErroHttp(400, "Preencha o campo $nome.");
    }
    if (comprimento($v) > $max) {
        throw new ErroHttp(400, "O campo $nome tem mais de $max caracteres.");
    }
    return $v;
}

function normalizar_email($valor): string
{
    $v = strtolower(texto($valor, 'email', 200, true));
    if (!filter_var($v, FILTER_VALIDATE_EMAIL)) {
        throw new ErroHttp(400, 'Indique um email válido.');
    }
    return $v;
}

function validar_nif($valor): string
{
    $v = strtoupper(preg_replace('/[\s.\-]/', '', texto($valor, 'NIF', 20, true)));
    if (preg_match('/^\d{9}$/', $v)) {
        $soma = 0;
        for ($i = 0; $i < 8; $i++) {
            $soma += (int) $v[$i] * (9 - $i);
        }
        $resto = $soma % 11;
        $controlo = $resto < 2 ? 0 : 11 - $resto;
        if ($controlo !== (int) $v[8]) {
            throw new ErroHttp(400, 'O NIF não é válido. Confirme os 9 dígitos.');
        }
        return $v;
    }
    // Número de IVA de outro país da UE, com o prefixo do país (ex.: ESB12345678)
    if (preg_match('/^[A-Z]{2}[A-Z0-9]{2,13}$/', $v)) {
        return $v;
    }
    throw new ErroHttp(400, 'O NIF não é válido. Confirme os 9 dígitos.');
}

function telefone($valor, string $nome = 'telefone', bool $obrigatorio = false): string
{
    $v = texto($valor, $nome, 30, $obrigatorio);
    if ($v !== '' && !preg_match('/^\+?[\d\s()\-]{6,25}$/', $v)) {
        throw new ErroHttp(400, "Indique um $nome válido.");
    }
    return $v;
}

const ENTREGAS = ['portal', 'email', 'whatsapp'];

function entrega($valor): string
{
    if (!is_string($valor) || !in_array($valor, ENTREGAS, true)) {
        throw new ErroHttp(400, 'Escolha como quer receber o ficheiro.');
    }
    return $valor;
}

function inteiro($valor): int
{
    if (is_int($valor)) {
        return $valor;
    }
    if (is_string($valor) && preg_match('/^\s*-?\d{1,9}\s*$/', $valor)) {
        return (int) $valor;
    }
    if (is_float($valor) && floor($valor) == $valor && abs($valor) < 1e9) {
        return (int) $valor;
    }
    throw new ErroHttp(400, 'Indique um número inteiro.');
}

function aleatorio(int $bytes = 32): string
{
    return bin2hex(random_bytes($bytes));
}

function codigo_numerico(): string
{
    return str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
}

function segredo(): string
{
    $s = (string) cfg('segredo');
    if (strlen($s) >= 32) {
        return $s;
    }
    if (cfg('dev')) {
        return 'segredo-de-desenvolvimento-apenas-para-testes-locais';
    }
    throw new RuntimeException('Configuração: o segredo tem de ter 32 caracteres ou mais.');
}

function nome_ficheiro(?string $valor): string
{
    $n = (string) $valor;
    $n = basename(str_replace('\\', '/', $n));
    $n = preg_replace('/[^\w.\-()+ ]/', '_', $n);
    $n = trim(substr($n, 0, 120), " .");
    return $n === '' ? 'ficheiro.bin' : $n;
}

function numero_whatsapp(?string $valor): string
{
    $d = preg_replace('/\D/', '', (string) $valor);
    if (strncmp($d, '00', 2) === 0) {
        $d = substr($d, 2);
    }
    if (strlen($d) === 9) {
        $d = '351' . $d;
    }
    return $d;
}

function tokens_txt(int $n): string
{
    return abs($n) === 1 ? "$n token" : "$n tokens";
}

function e_https(): bool
{
    return (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || strtolower($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https'
        || (string) ($_SERVER['SERVER_PORT'] ?? '') === '443';
}

function origem_pedido(): string
{
    return (e_https() ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? '');
}

function site_url(): string
{
    $u = (string) cfg('site_url');
    return $u !== '' ? rtrim($u, '/') : origem_pedido();
}

function nome_site(): string
{
    return (string) (cfg('nome') ?: 'GARC – Soluções Técnicas');
}

// Pedidos POST só são aceites a partir de páginas do próprio site.
function verificar_origem(): void
{
    $origem = $_SERVER['HTTP_ORIGIN'] ?? '';
    if ($origem === '' || !hash_equals(origem_pedido(), $origem)) {
        throw new ErroHttp(403, 'Pedido recusado: origem inválida.');
    }
}
