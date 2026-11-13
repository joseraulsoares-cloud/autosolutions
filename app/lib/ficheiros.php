<?php
declare(strict_types=1);

// Ficheiros das oficinas, guardados fora de public_html.

function ficheiros_dir(): string
{
    $d = rtrim((string) cfg('ficheiros_dir'), '/');
    if ($d === '') {
        throw new RuntimeException('Configuração: falta a pasta ficheiros_dir.');
    }
    if (!is_dir($d) && !@mkdir($d, 0750, true) && !is_dir($d)) {
        throw new RuntimeException("Não foi possível criar a pasta $d.");
    }
    return $d;
}

function caminho_ficheiro(string $chave): string
{
    if ($chave === '' || strpos($chave, '..') !== false || $chave[0] === '/') {
        throw new ErroHttp(400, 'Ficheiro inválido.');
    }
    return ficheiros_dir() . '/' . $chave;
}

function bytes_ini(string $valor): int
{
    $valor = trim($valor);
    if ($valor === '') {
        return 0;
    }
    $multiplicador = ['g' => 1024 * 1024 * 1024, 'm' => 1024 * 1024, 'k' => 1024];
    return (int) $valor * ($multiplicador[strtolower(substr($valor, -1))] ?? 1);
}

function max_mb(): int
{
    return (int) catalogo()['max_mb'];
}

/**
 * Guarda o ficheiro enviado no campo $campo em $base/<nome>. Devolve chave, nome e tamanho.
 */
function guardar_upload(string $campo, string $base): array
{
    $max = max_mb() * 1024 * 1024;
    $enviado = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
    $limitePost = bytes_ini((string) ini_get('post_max_size'));
    if (empty($_FILES) && $limitePost > 0 && $enviado > $limitePost) {
        throw new ErroHttp(413, 'O ficheiro é maior do que o limite do servidor (' . ini_get('post_max_size') . '). Comprima-o em .zip ou contacte-nos.');
    }
    $f = $_FILES[$campo] ?? null;
    if (!is_array($f) || is_array($f['error'] ?? null)) {
        throw new ErroHttp(400, 'Escolha o ficheiro a enviar.');
    }
    switch ($f['error']) {
        case UPLOAD_ERR_OK:
            break;
        case UPLOAD_ERR_INI_SIZE:
        case UPLOAD_ERR_FORM_SIZE:
            throw new ErroHttp(413, 'O ficheiro é maior do que o limite do servidor (' . ini_get('upload_max_filesize') . '). Comprima-o em .zip ou contacte-nos.');
        case UPLOAD_ERR_NO_FILE:
            throw new ErroHttp(400, 'Escolha o ficheiro a enviar.');
        default:
            throw new ErroHttp(500, 'O envio do ficheiro falhou. Tente de novo.');
    }
    if ((int) $f['size'] <= 0) {
        throw new ErroHttp(400, 'O ficheiro está vazio.');
    }
    if ((int) $f['size'] > $max) {
        throw new ErroHttp(413, 'O ficheiro tem mais de ' . max_mb() . ' MB. Comprima-o em .zip ou contacte-nos.');
    }
    $nome = nome_ficheiro($f['name'] ?? '');
    $chave = $base . '/' . $nome;
    $destino = caminho_ficheiro($chave);
    if (!is_dir(dirname($destino)) && !@mkdir(dirname($destino), 0750, true) && !is_dir(dirname($destino))) {
        throw new RuntimeException('Não foi possível criar a pasta do pedido.');
    }
    $ok = is_uploaded_file($f['tmp_name']) ? move_uploaded_file($f['tmp_name'], $destino) : false;
    if (!$ok) {
        throw new ErroHttp(500, 'Não foi possível guardar o ficheiro. Tente de novo.');
    }
    @chmod($destino, 0640);
    return ['chave' => $chave, 'nome' => $nome, 'tamanho' => (int) $f['size']];
}

function servir_ficheiro(string $chave, string $nome): void
{
    $p = caminho_ficheiro($chave);
    if (!is_file($p)) {
        throw new ErroHttp(404, 'O ficheiro já não está disponível. Contacte-nos.');
    }
    while (ob_get_level()) {
        ob_end_clean();
    }
    header('Content-Type: application/octet-stream');
    header('Content-Length: ' . filesize($p));
    header('Content-Disposition: attachment; filename="' . addcslashes($nome, "\"\\") . '"');
    header('Cache-Control: private, no-store');
    header('X-Content-Type-Options: nosniff');
    readfile($p);
}

function apagar_ficheiro(?string $chave): void
{
    if ($chave) {
        $p = caminho_ficheiro($chave);
        if (is_file($p)) {
            @unlink($p);
        }
    }
}

// Anexo para email, se o ficheiro existir e não passar do limite de anexo_max_mb.
function anexo_se_couber(?string $chave, ?string $nome): ?array
{
    if (!$chave || !$nome) {
        return null;
    }
    $p = caminho_ficheiro($chave);
    $limite = (int) (cfg('anexo_max_mb') ?: 15) * 1024 * 1024;
    if (!is_file($p) || filesize($p) > $limite) {
        return null;
    }
    return ['nome' => $nome, 'caminho' => $p];
}
