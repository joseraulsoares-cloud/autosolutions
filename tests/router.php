<?php
// Imita o .htaccess do alojamento no servidor embutido do PHP (a partir do PHP 7.4, como a API).
$root = getenv('SITE_ROOT');
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
if ($path === '/api' || strncmp($path, '/api/', 5) === 0) {
    chdir($root . '/api');
    require $root . '/api/index.php';
    return true;
}
// Os preços passaram para a área de cliente
if (preg_match('#^/precos(\.html)?/?$#', $path)) {
    header('Location: /area-cliente#precos', true, 301);
    return true;
}
// Páginas em PHP: o .html antigo leva ao endereço limpo; o endereço limpo mostra o .php
if (preg_match('#^/(.+)\.html$#', $path, $m) && is_file($root . '/' . $m[1] . '.php')) {
    header('Location: /' . $m[1], true, 301);
    return true;
}
$limpo = rtrim($path, '/');
if ($limpo !== '' && !is_file($root . $path) && is_file($root . $limpo . '.php')) {
    chdir($root);
    require $root . $limpo . '.php';
    return true;
}
if ($path === '/' || is_file($root . $path)) {
    return false;
}
if (is_file($root . $path . '.html')) {
    header('Content-Type: text/html; charset=utf-8');
    readfile($root . $path . '.html');
    return true;
}
http_response_code(404);
header('Content-Type: text/html; charset=utf-8');
readfile($root . '/404.html');
return true;
