<?php
// Imita o .htaccess do alojamento no servidor embutido do PHP.
$root = getenv('SITE_ROOT');
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
if ($path === '/api' || str_starts_with($path, '/api/')) {
    chdir($root . '/api');
    require $root . '/api/index.php';
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
