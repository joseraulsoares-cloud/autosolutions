<?php
declare(strict_types=1);

// Arranque da API da área de cliente. Este código fica fora de public_html.

const GARC_APP = __DIR__;

require __DIR__ . '/lib/util.php';
require __DIR__ . '/lib/db.php';
require __DIR__ . '/lib/auth.php';
require __DIR__ . '/lib/email.php';
require __DIR__ . '/lib/ficheiros.php';
require __DIR__ . '/lib/limites.php';
require __DIR__ . '/api/conta.php';
require __DIR__ . '/api/pedidos.php';
require __DIR__ . '/api/admin.php';
require __DIR__ . '/api/rotas.php';

function cfg(?string $chave = null)
{
    static $c = null;
    if ($c === null) {
        $f = getenv('GARC_CONFIG') ?: __DIR__ . '/config.php';
        if (!is_file($f)) {
            throw new ErroHttp(503, 'A área de cliente ainda não está configurada.');
        }
        $c = require $f;
    }
    return $chave === null ? $c : ($c[$chave] ?? null);
}

function catalogo(): array
{
    static $c = null;
    return $c ??= require __DIR__ . '/catalogo.php';
}
