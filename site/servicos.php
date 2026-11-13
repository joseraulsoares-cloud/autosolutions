<?php
// Gerado por build.py. Não editar à mão.
$garc_dados = array();
$garc_noticias = null;
try {
    $garc_app = getenv('GARC_APP');
    if (!$garc_app) {
        $garc_app = dirname(__DIR__) . '/autosolutions-app';
    }
    if (PHP_VERSION_ID >= 70100 && @is_file($garc_app . '/conteudos.php')) {
        require_once $garc_app . '/conteudos.php';
        $garc_dados = garc_dados();
    }
} catch (Exception $e) {
    error_log('GARC conteúdos: ' . $e->getMessage());
} catch (Throwable $e) {
    error_log('GARC conteúdos: ' . $e->getMessage());
}
function garc_v($chave, $padrao)
{
    global $garc_dados;
    $v = isset($garc_dados[$chave]) && is_scalar($garc_dados[$chave]) ? (string) $garc_dados[$chave] : '';
    return htmlspecialchars($v !== '' ? $v : $padrao, ENT_QUOTES, 'UTF-8');
}
?>
<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Serviços | GARC – Soluções Técnicas</title>
<meta name="description" content="Chiptuning, admissão e escape, correções, sistemas de emissões e diagnóstico avançado para oficinas.">
<meta property="og:title" content="Serviços | GARC – Soluções Técnicas">
<meta property="og:description" content="Chiptuning, admissão e escape, correções, sistemas de emissões e diagnóstico avançado para oficinas.">
<meta property="og:locale" content="pt_PT">
<link rel="icon" href="/assets/favicon.ico" sizes="32x32">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/barlow-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/barlow-condensed-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/styles.css">
<script src="/assets/main.js" defer></script>
</head>
<body>
<a class="skip" href="#conteudo">Saltar para o conteúdo</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/" aria-label="GARC – AutoSolutions &amp; Consulting, página inicial">
      <svg class="brand-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs><g id="lg-marca"><path style="fill:var(--logo-prata)" transform="translate(842 1253) scale(1 -1)" d="M597 513 c-2 -3 -4 -9 -7 -16 -7 -16 -39 -81 -50 -101 -7 -12 -12 -20 -33 -52 -13 -20 -38 -54 -53 -71 -4 -5 -10 -11 -12 -15 -6 -7 -51 -52 -63 -62 -7 -6 -21 -18 -34 -28 -47 -39 -149 -101 -179 -110 -1 0 -6 -2 -10 -4 -4 -2 -12 -5 -18 -7 -5 -2 -16 -6 -25 -9 -26 -10 -29 -11 -39 -14 -6 -1 -13 -3 -16 -4 -4 -1 -11 -3 -16 -4 -6 -1 -13 -3 -15 -3 -3 -1 -9 -2 -13 -3 -11 -2 -15 -4 -10 -7 3 -1 80 -1 90 0 4 1 13 2 20 2 27 4 76 14 94 20 2 0 9 3 17 5 7 2 16 6 21 7 5 2 13 5 18 7 27 10 90 44 110 61 3 2 9 7 13 10 32 24 74 70 100 108 24 36 29 44 50 87 16 33 25 53 38 94 9 25 11 33 13 44 1 2 2 7 3 11 1 4 2 8 2 9 0 2 1 5 2 8 1 3 2 7 2 11 0 3 1 8 1 12 3 9 2 18 -1 14z"/><path style="fill:var(--logo-cinza)" transform="translate(672 1212) scale(1 -1)" d="M206 642 c-4 -4 -10 -10 -12 -14 -9 -12 -28 -35 -53 -66 -3 -3 -7 -8 -9 -11 -3 -3 -7 -9 -11 -13 -4 -4 -9 -11 -13 -16 -4 -5 -8 -10 -10 -12 -9 -10 -27 -35 -27 -37 0 -4 -6 -3 210 -4 124 0 208 -1 209 -1 4 -2 2 -6 -21 -48 -113 -204 -284 -358 -456 -409 -19 -6 -14 -8 18 -8 36 0 87 5 114 11 2 1 6 2 8 2 10 2 27 7 43 11 21 6 58 19 77 27 6 2 14 5 17 6 48 20 105 52 152 85 41 29 100 82 129 116 39 46 59 72 84 114 38 61 72 136 88 195 5 16 12 44 12 46 0 1 1 5 2 8 3 10 4 22 1 24 -1 1 -47 1 -273 1 l-272 0 -7 -7z"/><path style="fill:var(--logo-azul)" transform="translate(0 1181) scale(1 -1)" d="M784 1178 c-8 0 -15 -1 -17 -2 -3 0 -9 -1 -15 -2 -6 0 -14 -1 -18 -2 -4 -1 -9 -2 -11 -2 -3 0 -8 -1 -11 -2 -4 -1 -9 -2 -11 -2 -1 0 -5 -1 -8 -2 -4 -1 -7 -2 -9 -2 -1 0 -5 -1 -8 -2 -4 -1 -10 -3 -14 -4 -18 -5 -32 -9 -41 -13 -19 -7 -29 -11 -37 -14 -4 -2 -11 -5 -15 -7 -69 -31 -134 -77 -191 -135 -10 -10 -21 -22 -25 -26 -3 -5 -10 -13 -15 -19 -30 -37 -58 -84 -79 -129 -13 -29 -28 -71 -33 -91 0 -3 -2 -11 -4 -17 -6 -24 -10 -47 -14 -79 -4 -32 -3 -98 1 -121 1 -5 2 -10 2 -12 0 -7 6 -37 11 -59 2 -7 4 -16 5 -20 3 -15 5 -15 14 -7 27 24 77 52 118 66 4 1 9 3 11 3 10 4 47 13 57 14 14 2 16 5 14 14 -1 3 -2 9 -2 13 0 3 -1 11 -2 16 -2 12 -2 53 0 61 1 3 2 12 2 20 0 7 2 16 2 18 1 3 2 7 2 9 0 2 1 6 2 10 1 4 2 9 3 11 1 4 2 8 6 23 23 74 77 148 146 195 34 25 77 45 116 55 4 1 12 3 17 4 6 2 11 3 13 3 1 0 7 1 12 2 5 1 12 2 15 2 3 0 9 1 14 2 12 2 54 2 65 -1 5 0 11 -1 14 -1 6 0 20 -2 38 -6 70 -16 137 -54 189 -106 20 -20 18 -20 31 -7 4 5 14 14 20 20 7 6 18 16 26 24 13 12 28 26 72 65 29 27 40 38 40 41 0 4 -28 33 -50 52 -5 4 -12 10 -14 12 -31 27 -89 64 -137 86 -17 7 -26 11 -27 11 0 0 -5 2 -11 4 -19 7 -22 8 -43 14 -18 5 -21 6 -30 8 -5 1 -14 3 -19 4 -14 3 -32 6 -44 7 -6 1 -13 2 -16 2 -7 1 -91 2 -107 1z M566 482 c-13 0 -26 -1 -28 -2 -3 0 -10 -1 -17 -2 -7 -1 -15 -2 -18 -2 -3 -1 -7 -2 -10 -2 -2 0 -6 0 -8 -1 -3 -1 -12 -3 -26 -6 -14 -3 -39 -12 -65 -22 -43 -17 -96 -52 -135 -89 -13 -12 -17 -14 -22 -14 -2 0 -7 -1 -12 -2 -5 -1 -11 -2 -13 -2 -5 0 -24 -4 -54 -10 -65 -15 -109 -39 -138 -78 -10 -13 -8 -15 4 -6 47 35 100 56 176 68 7 1 16 3 21 4 5 0 14 1 21 2 7 1 15 1 18 2 8 1 30 3 44 3 5 1 17 1 27 2 22 1 153 1 200 0 53 -1 50 -2 59 1 11 5 40 14 50 17 5 2 12 4 16 5 4 1 8 2 9 2 1 0 6 1 10 2 20 4 28 6 31 6 2 0 6 1 9 2 3 0 11 2 18 2 6 0 15 2 20 2 5 1 14 2 20 2 30 0 52 3 59 9 9 7 -1 9 -47 11 -31 1 -122 1 -134 -1 -4 0 -11 -1 -17 -2 -7 -1 -16 -2 -20 -3 -5 -1 -11 -2 -12 -2 -12 0 -47 -15 -86 -38 -12 -7 -15 -7 -43 -4 -15 2 -17 2 -22 1 -10 -4 -28 -3 -34 1 l-6 3 -34 1 c-19 1 -46 1 -60 1 -36 0 -36 0 -9 23 29 24 59 43 95 58 14 6 51 18 55 18 1 0 6 1 10 2 7 2 15 3 41 8 5 0 14 2 21 2 6 1 13 1 15 2 6 1 84 3 97 3 19 -2 76 -1 78 0 2 2 9 11 9 13 0 4 -6 5 -24 6 -10 1 -21 1 -24 2 -15 2 -78 3 -115 2z M481 268 c-3 -1 -7 -2 -8 -2 -8 0 -32 -11 -47 -20 -33 -22 -63 -67 -67 -101 0 -4 -1 -11 -2 -16 -3 -19 5 -28 10 -12 3 12 8 18 11 15 2 -1 16 -12 22 -18 5 -4 29 -23 43 -32 42 -30 106 -64 146 -77 10 -4 11 -4 18 -1 4 1 11 3 17 5 36 11 79 27 110 41 62 30 113 61 167 104 19 15 19 16 -2 16 -9 0 -22 -1 -31 -2 -20 -3 -69 -2 -84 0 -5 1 -13 2 -19 2 -7 0 -13 1 -17 2 -4 1 -10 2 -13 2 -2 0 -8 1 -11 2 -3 1 -8 2 -9 2 -2 0 -6 1 -9 2 -4 1 -7 2 -8 2 -3 0 -34 10 -40 12 -2 1 -9 4 -14 6 -30 11 -76 37 -105 59 -14 11 -13 11 -35 11 -15 0 -19 0 -23 -2z M319 241 c-3 -1 -23 -5 -44 -9 -7 -1 -14 -3 -17 -4 -4 -1 -9 -2 -12 -2 -9 -1 -14 -3 -17 -6 -3 -2 -4 -2 -16 -2 -8 0 -15 -1 -21 -2 -27 -6 -35 -8 -45 -9 -4 -1 -10 -2 -13 -3 -4 0 -12 -1 -17 -2 -12 -1 -25 -4 -26 -6 -1 -3 83 -3 96 0 5 1 13 3 18 4 5 1 10 2 11 2 1 0 4 1 7 1 3 1 11 3 19 5 16 3 30 6 38 8 17 4 17 0 2 -16 -10 -10 -11 -12 -5 -16 6 -5 16 -3 25 6 12 12 33 42 33 47 0 4 -8 6 -16 4z M8 179 c-7 -3 -8 -8 -1 -29 5 -17 9 -19 26 -20 6 -1 23 -2 38 -2 14 -1 37 -2 50 -3 64 -3 63 -3 75 -10 4 -3 12 -7 16 -9 l7 -4 28 0 c46 0 48 1 16 10 -13 3 -18 7 -46 30 -2 2 -5 4 -7 5 -5 1 -67 2 -71 1 -3 -1 -12 -1 -43 -2 -5 -1 -20 -1 -32 -1 l-23 -1 -4 4 c-4 4 -11 14 -16 24 -5 8 -7 9 -13 7z"/></g><g id="lg-palavra"><path style="fill:var(--logo-azul)" transform="translate(0 354) scale(1 -1)" d="M185 351 c-7 0 -16 -1 -19 -2 -3 -1 -7 -2 -8 -2 -7 0 -38 -10 -53 -18 -54 -25 -88 -66 -100 -120 -4 -15 -4 -49 -1 -62 1 -5 2 -9 2 -10 0 -13 19 -49 36 -68 31 -37 87 -63 130 -62 14 0 58 0 84 0 11 0 37 7 56 16 57 27 89 76 90 139 0 14 0 17 -1 19 l-2 3 -84 0 c-92 1 -101 1 -104 -2 -2 -4 -2 -42 1 -45 l3 -2 59 0 c71 0 65 1 60 -13 -18 -55 -105 -84 -181 -58 -30 10 -54 27 -70 51 -4 7 -13 24 -13 26 0 1 -1 5 -2 8 -2 6 -2 9 -2 28 l0 22 3 11 c11 34 30 54 66 72 8 5 33 13 37 13 1 0 5 1 9 2 11 3 50 3 63 0 5 -1 10 -2 11 -2 8 0 43 -15 57 -23 8 -5 8 -5 27 14 17 18 19 20 17 24 -3 6 -42 25 -61 31 -4 1 -11 3 -15 4 -3 1 -8 2 -10 2 -1 0 -6 1 -10 2 -9 2 -52 3 -75 2z M1829 351 c-9 0 -17 -1 -18 -2 -2 0 -6 -1 -11 -2 -4 -1 -10 -2 -12 -2 -3 -1 -10 -3 -15 -5 -53 -15 -99 -51 -120 -94 -4 -10 -11 -28 -11 -31 0 -1 -1 -5 -2 -9 -2 -5 -2 -10 -2 -28 -1 -91 64 -156 172 -173 16 -2 76 -3 88 -1 2 0 8 1 12 2 36 6 72 20 98 39 14 10 14 10 -10 27 -25 18 -23 17 -37 9 -32 -19 -62 -26 -105 -26 -29 0 -30 0 -54 6 -111 28 -138 152 -46 212 15 9 47 22 57 22 1 0 6 1 11 2 11 3 52 3 65 0 5 -1 10 -2 12 -2 10 0 44 -14 60 -25 14 -9 11 -11 41 12 19 14 19 15 6 25 -29 22 -57 34 -101 42 -12 2 -53 3 -78 2z M743 346 c-2 -1 -5 -6 -9 -12 -4 -7 -8 -15 -11 -19 -2 -4 -8 -15 -13 -23 -5 -9 -10 -19 -12 -23 -9 -17 -12 -22 -22 -39 -6 -11 -19 -34 -28 -51 -10 -18 -22 -39 -26 -47 -5 -8 -14 -23 -19 -34 -6 -11 -15 -25 -19 -32 -4 -7 -9 -17 -12 -22 -2 -5 -7 -13 -9 -17 -12 -19 -12 -18 26 -18 36 0 32 -1 41 16 4 7 9 16 12 20 2 4 5 11 7 15 3 4 5 9 6 10 1 1 4 7 8 14 3 6 11 20 17 32 12 20 18 32 35 63 4 7 10 17 13 23 3 6 8 14 10 19 3 5 10 16 15 26 14 27 12 28 30 -7 7 -13 15 -28 19 -34 8 -15 28 -53 34 -64 2 -5 7 -14 11 -21 4 -7 10 -19 15 -28 5 -9 12 -22 16 -30 4 -8 8 -14 8 -15 0 0 3 -5 6 -10 3 -6 7 -13 9 -16 1 -3 4 -8 5 -9 l3 -3 26 -1 c45 -1 44 -1 33 19 -3 5 -6 10 -6 10 0 1 -13 24 -27 51 -4 6 -8 13 -9 16 -1 2 -6 11 -11 19 -4 8 -11 21 -16 30 -5 9 -11 21 -15 28 -4 6 -10 18 -14 25 -4 7 -9 16 -11 20 -2 4 -8 14 -12 23 -5 8 -12 21 -15 28 -4 7 -10 18 -14 25 -19 34 -22 41 -25 43 -3 3 -45 3 -50 0z M1129 345 l-2 -3 0 -164 0 -164 2 -3 3 -2 26 0 c21 0 26 0 28 1 1 2 2 5 2 142 l1 140 2 2 c2 2 4 2 89 2 l87 -1 8 -2 c24 -8 37 -18 46 -35 l5 -10 0 -14 c1 -32 -19 -54 -57 -64 l-12 -3 -51 0 c-50 0 -54 0 -54 -3 0 -2 151 -152 154 -154 3 -2 79 -1 81 0 4 3 2 5 -23 30 -59 57 -81 79 -81 81 0 2 4 4 10 5 56 13 89 46 95 96 4 40 -12 77 -45 99 -14 9 -47 22 -57 22 -2 0 -8 1 -13 2 -10 2 -14 2 -126 2 l-115 0 -3 -2z"/></g><g id="lg-lema"><path style="fill:var(--logo-cinza)" transform="translate(1152 115) scale(1 -1)" d="M32 110 c-10 -6 -15 -16 -12 -27 3 -6 2 -7 -6 -15 -15 -14 -16 -30 -2 -37 7 -4 22 -3 30 1 7 3 9 4 11 1 4 -4 12 -5 14 -2 2 2 2 2 -1 8 -4 6 -4 7 2 16 3 4 5 8 6 10 2 9 -9 11 -13 1 -4 -9 -7 -10 -13 -2 -4 7 -4 7 5 16 20 19 4 43 -21 30z m16 -11 c3 -4 3 -8 -1 -12 -7 -6 -13 -5 -13 4 -1 8 8 13 14 8z m-16 -36 c2 -1 10 -13 10 -16 0 -7 -21 -9 -24 -1 -4 8 7 22 14 17z M144 111 c-18 -4 -25 -14 -31 -45 -4 -18 -1 -28 8 -33 7 -5 29 -5 37 -1 8 4 18 15 18 21 0 4 -10 6 -13 2 -1 -1 -4 -5 -6 -7 -10 -11 -28 -9 -31 3 0 5 4 30 7 35 8 17 26 19 34 4 6 -10 15 -9 15 2 0 16 -18 25 -38 19z M533 111 c-4 -5 -2 -11 5 -11 5 0 8 3 8 7 0 6 -8 8 -13 4z M460 110 c-3 -2 -8 -23 -15 -65 -3 -14 -2 -17 5 -16 5 1 6 3 7 9 1 3 2 9 3 14 1 5 3 13 4 19 1 5 3 13 4 18 4 19 1 28 -8 21z M493 109 c-2 -2 -3 -4 -3 -8 -1 -5 -5 -11 -7 -11 -7 0 -9 -9 -3 -12 3 -2 5 -5 3 -9 -1 -2 -1 -5 -1 -7 0 -2 -1 -7 -2 -11 -4 -14 2 -22 17 -22 6 0 7 0 10 2 4 5 2 10 -5 10 -8 0 -10 8 -6 24 3 10 4 12 9 12 11 0 15 11 5 13 -7 1 -8 3 -6 12 2 8 -6 12 -11 7z M288 90 c-1 0 -5 -1 -7 -2 -4 -1 -5 -1 -8 0 -3 1 -8 1 -11 0 -2 -1 -3 -3 -6 -17 -7 -33 -8 -38 -5 -40 7 -5 11 -1 13 12 6 30 10 36 22 35 7 -1 10 -4 9 -10 0 -7 -2 -19 -3 -23 -4 -9 -1 -17 5 -16 5 1 7 4 8 12 1 3 2 8 3 12 7 24 -2 40 -20 37z M341 89 c-3 0 -6 -2 -7 -2 -18 -13 -13 -29 10 -34 9 -2 11 -8 3 -13 -5 -3 -10 -3 -15 1 -8 6 -16 5 -15 -2 3 -14 37 -14 47 0 7 11 2 21 -14 26 -10 2 -13 6 -9 12 3 4 8 5 15 1 9 -5 13 -4 13 2 0 8 -15 13 -28 9z M580 89 c-8 -2 -9 -2 -13 -1 -10 4 -12 1 -17 -26 0 -5 -2 -12 -2 -15 -4 -14 -3 -18 3 -18 5 0 7 3 9 13 4 15 6 24 7 27 8 14 28 11 24 -5 0 -2 -1 -5 -1 -7 0 -1 -1 -6 -2 -9 -3 -10 -2 -17 1 -18 7 -3 11 2 12 12 1 3 2 9 3 13 7 26 -2 40 -24 34z M641 90 c-14 -3 -20 -10 -24 -26 -6 -24 2 -37 20 -35 12 2 12 2 13 -1 1 -5 -7 -14 -13 -14 -5 -1 -7 0 -12 5 -12 10 -22 1 -11 -10 17 -17 48 -3 52 23 0 3 2 8 2 10 1 3 2 7 2 9 0 3 1 8 2 11 1 3 2 8 2 9 0 2 1 6 2 9 2 8 -2 12 -10 9 -4 -2 -6 -2 -13 0 -6 2 -7 2 -12 1z m12 -13 c4 -2 5 -6 5 -13 -2 -23 -28 -32 -28 -10 0 17 11 29 23 23z M204 87 c-20 -11 -26 -46 -9 -56 6 -3 22 -4 29 0 21 11 26 49 8 57 -8 3 -20 3 -28 -1z m21 -11 c10 -8 0 -36 -14 -35 -13 0 -15 12 -7 29 4 8 15 11 21 6z M388 89 c-2 -1 -5 -8 -6 -17 -1 -3 -2 -8 -2 -10 -2 -6 -2 -21 -1 -25 3 -7 6 -8 17 -8 11 1 17 1 25 1 6 -1 7 1 10 19 2 8 4 18 5 23 3 13 3 17 -3 17 -6 0 -8 -2 -10 -14 -6 -28 -10 -34 -20 -34 -12 0 -13 5 -7 29 4 16 1 23 -8 19z M531 89 c-3 -2 -3 -2 -7 -20 -1 -6 -3 -14 -4 -18 -4 -17 -4 -22 3 -22 5 0 8 3 9 12 1 4 3 12 4 17 6 27 6 28 3 30 -3 2 -4 2 -8 1z M720 70 c-1 -2 -2 -4 -2 -5 0 -1 1 -3 2 -5 l3 -2 97 0 c77 0 98 0 99 1 3 3 4 8 1 10 l-3 3 -97 0 -97 0 -3 -2z"/><path style="fill:var(--logo-azul)" transform="translate(0 89) scale(1 -1)" d="M624 85 c-16 -7 -24 -22 -17 -35 2 -4 13 -11 18 -11 12 0 23 -11 17 -18 -8 -8 -20 -8 -30 1 -12 10 -23 4 -15 -8 9 -15 44 -16 57 -1 15 16 10 29 -12 37 -20 6 -24 10 -17 18 6 8 16 7 24 -1 10 -9 21 -3 15 8 -7 11 -26 16 -40 10z M757 85 c-3 -3 -4 -7 -13 -52 -1 -6 -3 -13 -4 -17 -1 -9 -1 -11 1 -12 3 -1 8 -1 10 0 2 2 7 18 7 23 0 1 1 5 2 9 2 7 5 20 6 30 1 3 2 8 2 10 3 10 -4 15 -11 9z M912 86 c-4 -1 -6 -9 -2 -11 3 -2 10 -1 12 2 5 6 -1 12 -10 9z M362 85 c-2 -2 -3 -3 -28 -46 -18 -32 -19 -32 -16 -34 4 -5 13 -1 18 7 3 6 5 7 20 7 16 0 17 -1 20 -9 4 -10 18 -10 17 -1 -1 2 -2 8 -2 14 -1 6 -3 13 -3 17 -1 3 -2 7 -2 10 0 2 -1 8 -2 13 -1 5 -2 11 -2 13 0 4 -2 9 -5 9 -4 1 -12 1 -15 0z m7 -23 c1 0 1 -3 1 -6 0 -2 1 -7 1 -11 3 -10 0 -12 -11 -11 -11 0 -11 2 -4 15 8 15 12 18 13 13z M501 85 c-4 -2 -5 -4 -6 -10 -2 -9 -2 -10 -7 -11 -9 -2 -12 -9 -4 -12 5 -3 5 -4 4 -12 -3 -10 -3 -26 -1 -30 5 -10 28 -10 28 0 0 3 -3 5 -6 5 -2 0 -4 1 -6 3 l-3 3 1 11 c2 11 4 16 7 19 3 4 4 30 1 33 -2 2 -6 2 -8 1z M867 85 c-3 -2 -5 -6 -5 -11 -1 -7 -2 -9 -7 -10 -9 -3 -12 -10 -5 -13 6 -2 6 -9 1 -28 -2 -7 2 -16 9 -19 5 -2 18 -1 20 1 4 4 1 10 -4 10 -7 0 -11 6 -8 14 0 3 1 8 2 11 0 3 2 8 3 10 1 2 2 5 2 6 0 1 0 3 1 4 2 4 2 22 0 24 -2 2 -6 3 -9 1z M553 64 c-23 -7 -35 -44 -18 -57 5 -5 25 -6 32 -2 19 8 28 40 15 53 -6 6 -19 8 -29 6z m12 -12 c7 -3 8 -6 5 -21 -3 -17 -27 -23 -27 -6 0 17 12 31 22 27z M697 63 c-25 -6 -36 -46 -16 -57 11 -7 33 -3 41 7 9 10 10 19 4 36 -5 15 -12 19 -29 14z m13 -11 c5 -3 7 -8 5 -16 -3 -16 -7 -20 -17 -20 -10 0 -13 5 -10 16 0 2 1 5 2 8 3 10 11 15 20 12z M951 63 c-16 -4 -26 -19 -25 -39 1 -16 6 -21 26 -21 17 0 25 7 31 24 10 26 -6 43 -32 36z m13 -11 c9 -4 6 -29 -3 -35 -9 -6 -18 -1 -19 9 -1 18 10 31 22 26z M1028 63 l-7 -3 -5 2 c-9 4 -12 2 -15 -15 -2 -7 -4 -16 -5 -21 -4 -18 -4 -23 3 -23 7 0 9 3 11 13 4 25 8 34 18 36 11 2 16 -6 12 -18 -1 -4 -2 -8 -2 -9 0 -2 -1 -6 -1 -9 -3 -10 -2 -13 5 -13 6 0 12 11 12 21 0 2 1 6 2 10 8 21 -7 36 -28 29z M1091 64 c-15 -5 -23 -19 -16 -28 3 -3 16 -9 20 -9 8 0 8 -11 -1 -13 -5 -1 -6 -1 -13 2 -11 5 -19 1 -13 -6 9 -12 38 -10 46 3 9 12 3 22 -15 26 -12 3 -14 11 -3 15 3 1 4 1 10 -2 8 -4 10 -5 13 -2 10 7 -13 18 -28 14z M416 63 c-2 -1 -5 -7 -6 -14 0 -2 -1 -8 -2 -12 -4 -18 -3 -26 5 -32 4 -3 17 -3 24 0 5 1 5 1 8 0 10 -5 17 3 17 17 0 1 1 5 2 9 1 3 2 7 2 10 0 2 1 7 2 10 3 9 2 13 -5 13 -7 0 -10 -6 -13 -23 -3 -18 -9 -26 -19 -26 -7 0 -11 9 -8 20 7 24 5 33 -7 28z M825 62 c-3 -2 -5 -7 -8 -22 -4 -20 -11 -28 -22 -24 -7 2 -7 9 -1 33 2 12 1 14 -6 14 -6 0 -9 -2 -10 -9 0 -2 -1 -8 -2 -12 -5 -19 -4 -33 4 -37 5 -2 17 -3 24 -1 3 2 5 2 8 0 10 -3 13 -1 16 11 3 13 7 31 9 43 1 5 -7 8 -12 4z M909 63 c-4 -1 -6 -4 -7 -12 -10 -47 -10 -48 -1 -48 6 0 8 3 11 21 1 6 3 15 4 20 3 13 3 15 2 17 -2 2 -7 3 -9 2z M4 44 c-3 -3 -2 -9 1 -11 2 -2 268 -2 271 0 2 2 2 10 0 12 -2 1 -23 1 -136 1 l-134 0 -2 -2z"/></g></defs></svg><svg class="brand-logo brand-logo-largo" viewBox="0 0 2841.42 586.88" aria-hidden="true" focusable="false"><use href="#lg-marca" transform="translate(0 0) scale(0.47)"/><use href="#lg-palavra" transform="translate(765.42 31.44)"/><use href="#lg-lema" transform="translate(765.42 440.44)"/></svg><svg class="brand-logo brand-logo-curto" viewBox="0 0 2744.38 548.7" aria-hidden="true" focusable="false"><use href="#lg-marca" transform="translate(0 0) scale(0.44)"/><use href="#lg-palavra" transform="translate(724.38 97.35)"/></svg>
    </a>
    <nav class="nav" aria-label="Principal" data-open="false">
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-list"><span class="nav-toggle-bars" aria-hidden="true"><span></span><span></span><span></span></span>Menu</button>
      <ul class="nav-list" id="nav-list">
        <li><a href="/">Início</a></li>
        <li><a href="/servicos" aria-current="page">Serviços</a></li>
        <li><a href="/noticias">Notícias</a></li>
        <li><a href="/sobre">Sobre</a></li>
        <li><a href="/contacto">Contacto</a></li>
        <li class="nav-account"><a href="/area-cliente">Área de cliente</a></li>
      </ul>
    </nav>
  </div>
</header>
<main id="conteudo">

<section class="page-head">
  <div class="wrap">
    <h1>Serviços</h1>
    <p class="lead">Ficheiros por módulo, preparados para a viatura e a ECU de cada pedido, e diagnóstico avançado para oficinas.</p>
    <p class="horario">Horário de atendimento: <strong><?= garc_v('horario', '8h30–17h00') ?></strong></p>
    <nav class="subnav" aria-label="Secções desta página"><a href="#chiptuning">Chiptuning</a><a href="#admissao-escape">Admissão e escape</a><a href="#correcoes">Correções</a><a href="#emissoes">Sistemas de emissões</a><a href="#verificacao">Verificação de ficheiros</a><a href="#diagnostico">Diagnóstico avançado</a></nav>
  </div>
</section>

<section class="section svc-section" id="chiptuning">
  <div class="wrap">
    <div class="section-head"><h2>Chiptuning</h2><p class="muted">Recalibração do software do motor e da caixa automática.</p></div>
    <dl class="mod-list">
        <div><dt>Stage 1/2</dt><dd>Stage 1: recalibração do software com o motor de série (binário, pressão do turbo, injeção e limitadores). Stage 2: calibração feita para alterações físicas já montadas, como admissão, intercooler ou escape.</dd></div>
        <div><dt>TCU Stage 1</dt><dd>Recalibração da caixa automática: limites de binário, pontos de passagem e pressões, de acordo com o novo binário do motor.</dd></div>
        <div><dt>Pop &amp; bangs</dt><dd>Estalos no escape em desaceleração, com intensidade e regime configuráveis. Para motores a gasolina.</dd></div>
        <div><dt>Torque monitoring</dt><dd>Ajuste da monitorização de binário, para que a centralina não entre em modo de emergência depois da reprogramação.</dd></div>
        <div><dt>Sport display</dt><dd>Calibração das leituras do ecrã desportivo (potência, binário e pressão do turbo) para os valores depois da reprogramação.</dd></div>
    </dl>
  </div>
</section>

<section class="section svc-section" id="admissao-escape">
  <div class="wrap">
    <div class="section-head"><h2>Admissão e escape</h2><p class="muted">Gestão de componentes de admissão e escape na centralina.</p></div>
    <dl class="mod-list">
        <div><dt>Flaps off</dt><dd>Desativação das borboletas de turbulência (swirl flaps) do coletor de admissão, sem erros na centralina.</dd></div>
        <div><dt>Exhaust flap off</dt><dd>Desativação ou controlo da válvula de escape.</dd></div>
        <div><dt>TVA off</dt><dd>Desativação do atuador da borboleta de admissão (TVA) em motores diesel.</dd></div>
        <div><dt>MAF off</dt><dd>Funcionamento sem o medidor de massa de ar, com o ar admitido calculado por modelo.</dd></div>
    </dl>
  </div>
</section>

<section class="section svc-section" id="correcoes">
  <div class="wrap">
    <div class="section-head"><h2>Correções</h2><p class="muted">Correções de calibração para problemas conhecidos.</p></div>
    <dl class="mod-list">
        <div><dt>Oil pressure fix</dt><dd>Correção de erros relacionados com o controlo da pressão de óleo.</dd></div>
        <div><dt>Hot start fix</dt><dd>Correção da calibração de arranque em motores com dificuldade em pegar a quente.</dd></div>
        <div><dt>Start-stop off</dt><dd>Desativação permanente do sistema Start &amp; Stop.</dd></div>
    </dl>
  </div>
</section>

<section class="section svc-section" id="emissoes">
  <div class="wrap">
    <div class="section-head"><h2>Sistemas de emissões</h2></div>
    <div class="notice" role="note"><strong>Uso exclusivo em competição ou fora da via pública.</strong><p>Os módulos de desativação de sistemas de emissões destinam-se a veículos de competição ou a uso fora da via pública. Ao pedir um destes módulos, o cliente declara essa finalidade e assume a responsabilidade pela utilização do ficheiro.</p></div>
    <dl class="mod-list">
        <div><dt>DPF off</dt><dd>Desativação do filtro de partículas (DPF/FAP) na gestão do motor.</dd></div>
        <div><dt>EGR off</dt><dd>Desativação da recirculação dos gases de escape (EGR).</dd></div>
        <div><dt>AdBlue/SCR off</dt><dd>Desativação do sistema de redução catalítica seletiva (SCR/AdBlue).</dd></div>
        <div><dt>Lambda/O2 off</dt><dd>Desativação da monitorização das sondas lambda (O2).</dd></div>
    </dl>
  </div>
</section>

<section class="section svc-section" id="verificacao">
  <div class="wrap">
    <div class="section-head"><h2>Verificação de ficheiros</h2><p class="muted">Para ficheiros já modificados pela oficina ou por outro preparador, com custo à parte.</p></div>
    <dl class="mod-list">
        <div><dt>Correção de checksum</dt><dd>Correção do checksum de um ficheiro já modificado, para que a centralina o aceite na escrita.</dd></div>
        <div><dt>Revisão de mapa</dt><dd>Revisão de um ficheiro já modificado, por outro preparador ou pela oficina, à procura de erros nos mapas alterados.</dd></div>
    </dl>
  </div>
</section>

<section class="section svc-section" id="diagnostico">
  <div class="wrap stack">
    <div class="section-head"><h2>Diagnóstico avançado</h2><p class="lead">Para as avarias que pedem mais do que uma leitura de erros.</p></div>
    <ul class="checklist">
      <li>Avarias intermitentes e falhas de comunicação entre módulos</li>
      <li>Sistemas de pós-tratamento: EGR, DPF e SCR</li>
      <li>Sensores e atuadores, com análise de valores reais</li>
      <li>Apoio técnico à oficina durante a reparação</li>
    </ul>
    <div class="actions">
      <a class="btn btn-primary" href="/contacto?assunto=Diagn%C3%B3stico%20avan%C3%A7ado">Pedir diagnóstico</a>
      <a class="btn btn-secondary" href="/area-cliente#novo">Enviar ficheiro</a>
    </div>
  </div>
</section>
</main>
<footer class="site-footer">
  <div class="footer-legal">
    <div class="wrap">
      <p>GARC – Soluções Técnicas, Unipessoal Lda. Sede: Rua do Morangal, n.º 205, Traseiras, Fração S, 4410-385 Vila Nova de Gaia. Matriculada na Conservatória do Registo Comercial de Vila Nova de Gaia com o número único de matrícula e de pessoa coletiva 505743973.</p>
      <ul class="legal-links">
        <li><a class="lre" href="https://www.livroreclamacoes.pt/" target="_blank" rel="noopener">Livro de Reclamações Eletrónico</a></li>
        <li><a href="/privacidade">Política de privacidade</a></li>
        <li><a href="/termos">Termos de utilização</a></li>
      </ul>
      <p>© 2026 GARC – Soluções Técnicas</p>
    </div>
  </div>
</footer>
<a class="wa-float" href="https://wa.me/351913027543?text=Ol%C3%A1%21%20Tenho%20uma%20quest%C3%A3o%20sobre%20os%20servi%C3%A7os%20da%20GARC." target="_blank" rel="noopener" aria-label="Falar connosco pelo WhatsApp"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-4.6 3.7a.6.6 0 0 1-1-.47V16H6.5A2.5 2.5 0 0 1 4 13.5z"/></svg><span>WhatsApp</span></a>
</body>
</html>
