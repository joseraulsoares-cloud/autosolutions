<?php
declare(strict_types=1);

// Ponto de entrada da API da área de cliente (public_html/api).
// O código fica fora de public_html, na pasta autosolutions-app ao lado de public_html.

// A área de cliente precisa de PHP 7.4 ou mais recente. Com uma versão mais antiga, responde com uma
// mensagem clara em vez de um erro interno (o formulário de contacto mostra então o email da empresa).
if (PHP_VERSION_ID < 70400) {
    http_response_code(503);
    header('Content-Type: application/json; charset=utf-8');
    echo '{"erro":"A área de cliente está temporariamente indisponível. Tente mais tarde."}';
    exit;
}

$app = getenv('GARC_APP') ?: dirname(__DIR__, 2) . '/autosolutions-app';
if (!is_file($app . '/bootstrap.php')) {
    http_response_code(503);
    header('Content-Type: application/json; charset=utf-8');
    echo '{"erro":"A área de cliente ainda não está instalada."}';
    exit;
}
require $app . '/bootstrap.php';
garc_api_executar();
