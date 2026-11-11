<?php
declare(strict_types=1);

// Conteúdos que o Raul altera no cPanel, sem mexer no código:
//   garc-conteudos/dados.txt       preços, prazo de entrega, horário e pagamentos ("chave: valor")
//   garc-conteudos/noticias/*.txt  uma notícia por ficheiro (os nomes começados por _ não aparecem)
// A pasta garc-conteudos fica ao lado de public_html e de autosolutions-app, e as atualizações do site
// nunca a substituem. Se não existir, é criada com os valores de conteudos-iniciais/.
// Este ficheiro não usa a base de dados: as páginas públicas funcionam mesmo sem a área de cliente.
// Funciona a partir do PHP 7.1 (o alojamento pode ainda não ter o PHP 8 que a área de cliente pede).

if (!function_exists('garc_dados')) {

    function garc_conteudos_dir(): string
    {
        return rtrim(getenv('GARC_CONTEUDOS') ?: dirname(__DIR__) . '/garc-conteudos', '/');
    }

    function garc_conteudos_preparar(): void
    {
        static $feito = false;
        if ($feito) {
            return;
        }
        $feito = true;
        $dir = garc_conteudos_dir();
        $origem = __DIR__ . '/conteudos-iniciais';
        if (!is_dir($dir) && !@mkdir($dir, 0755, true)) {
            return;
        }
        if (!is_file("$dir/dados.txt")) {
            @copy("$origem/dados.txt", "$dir/dados.txt");
        }
        if (!is_dir("$dir/noticias") && @mkdir("$dir/noticias", 0755)) {
            foreach (garc_txts("$origem/noticias") as $f) {
                @copy($f, "$dir/noticias/" . basename($f));
            }
        }
    }

    function garc_contem(string $texto, string $parte): bool
    {
        return strpos($texto, $parte) !== false;
    }

    /** Ficheiros .txt de uma pasta, por ordem do nome. */
    function garc_txts(string $pasta): array
    {
        $nomes = is_dir($pasta) ? (@scandir($pasta) ?: []) : [];
        $lista = [];
        foreach ($nomes as $n) {
            if (substr(strtolower($n), -4) === '.txt' && is_file("$pasta/$n")) {
                $lista[] = "$pasta/$n";
            }
        }
        return $lista;
    }

    /** Lê linhas "chave: valor"; ignora linhas vazias e notas (#). */
    function garc_ler_dados(string $texto): array
    {
        $dados = [];
        $texto = preg_replace('/^\xEF\xBB\xBF/', '', $texto);
        foreach (preg_split('/\R/u', $texto) as $linha) {
            $linha = trim($linha);
            if ($linha === '' || $linha[0] === '#' || !garc_contem($linha, ':')) {
                continue;
            }
            [$chave, $valor] = explode(':', $linha, 2);
            $chave = strtolower(trim($chave));
            if (preg_match('/^[a-z_]+$/', $chave)) {
                $dados[$chave] = trim($valor);
            }
        }
        return $dados;
    }

    function garc_numero(string $texto): ?float
    {
        $t = str_replace(['€', ' ', "\u{a0}"], '', $texto);
        if (garc_contem($t, ',')) {
            $t = str_replace(['.', ','], ['', '.'], $t);
        }
        return is_numeric($t) && (float) $t > 0 ? (float) $t : null;
    }

    function garc_inteiro(string $texto): ?int
    {
        return preg_match('/^\s*(\d+)/', $texto, $m) && (int) $m[1] > 0 ? (int) $m[1] : null;
    }

    function garc_eur(float $valor): string
    {
        return number_format($valor, 2, ',', ' ') . ' €';
    }

    function garc_tokens_txt(int $n): string
    {
        return $n . ($n === 1 ? ' token' : ' tokens');
    }

    function garc_lista_txt(array $itens): string
    {
        if (count($itens) <= 1) {
            return (string) ($itens[0] ?? '');
        }
        return implode(', ', array_slice($itens, 0, -1)) . ' ou ' . end($itens);
    }

    /** Valores em vigor: os do ficheiro do servidor, e os de origem para o que faltar ou não for válido. */
    function garc_dados(): array
    {
        static $d = null;
        if ($d !== null) {
            return $d;
        }
        garc_conteudos_preparar();
        $origem = garc_ler_dados((string) @file_get_contents(__DIR__ . '/conteudos-iniciais/dados.txt'));
        $ficheiro = garc_conteudos_dir() . '/dados.txt';
        $vivo = is_file($ficheiro) ? garc_ler_dados((string) @file_get_contents($ficheiro)) : [];
        $v = $vivo + $origem;
        $texto = static function (string $k) use ($v, $origem): string {
            return ($v[$k] ?? '') !== '' ? $v[$k] : ($origem[$k] ?? '');
        };
        $inteiros = static function (string $lista): array {
            $r = [];
            foreach (explode(',', $lista) as $x) {
                $n = garc_inteiro($x);
                if ($n !== null) {
                    $r[] = $n;
                }
            }
            return $r;
        };

        $token = garc_numero($v['token'] ?? '') ?? garc_numero($origem['token'] ?? '') ?? 1.0;
        $minimo = garc_inteiro($v['minimo'] ?? '') ?? garc_inteiro($origem['minimo'] ?? '') ?? 1;
        $exemplos = $inteiros($v['exemplos'] ?? '');
        if (!$exemplos) {
            $exemplos = $inteiros($origem['exemplos'] ?? '');
        }
        $paypal = trim(preg_replace('#^(https?://)?(www\.)?paypal\.me/#i', '', $v['paypal'] ?? ''), " /@");
        $cartao = trim($v['cartao'] ?? '');
        if ($cartao !== '' && !preg_match('#^https://#i', $cartao)) {
            $cartao = '';
        }
        $mbway = trim($v['mbway'] ?? '');
        $meios = [];
        if ($mbway !== '') {
            $meios[] = 'MB WAY';
        }
        if ($cartao !== '') {
            $meios[] = 'cartão';
        }
        if ($paypal !== '') {
            $meios[] = 'PayPal';
        }
        return $d = [
            'token' => $token,
            'token_txt' => garc_eur($token),
            'minimo' => $minimo,
            'minimo_txt' => garc_tokens_txt($minimo),
            'exemplos' => $exemplos,
            'iva' => $texto('iva'),
            'validade' => $texto('validade'),
            'sob_consulta' => $texto('sob_consulta'),
            'entrega' => $texto('entrega'),
            'horario' => $texto('horario'),
            'mbway' => $mbway,
            'paypal' => $paypal,
            'paypal_url' => $paypal !== '' ? 'https://paypal.me/' . rawurlencode($paypal) : '',
            'cartao' => $cartao,
            'meios' => $meios,
            'meios_txt' => garc_lista_txt($meios),
        ];
    }

    /** Texto pronto a pôr numa página (escapado). */
    function garc_txt(string $chave, string $padrao = ''): string
    {
        $v = garc_dados()[$chave] ?? '';
        $v = is_scalar($v) ? (string) $v : '';
        return htmlspecialchars($v !== '' ? $v : $padrao, ENT_QUOTES, 'UTF-8');
    }

    /** Preços para a área de cliente (só são enviados a contas aprovadas e ao administrador). */
    function garc_precos(): array
    {
        $d = garc_dados();
        $pagamentos = [];
        if ($d['mbway'] !== '') {
            $pagamentos[] = ['tipo' => 'mbway', 'nome' => 'MB WAY', 'valor' => $d['mbway']];
        }
        if ($d['cartao'] !== '') {
            $pagamentos[] = ['tipo' => 'cartao', 'nome' => 'Cartão', 'url' => $d['cartao']];
        }
        if ($d['paypal'] !== '') {
            $pagamentos[] = ['tipo' => 'paypal', 'nome' => 'PayPal', 'url' => $d['paypal_url'],
                'valor' => preg_replace('#^https://#', '', $d['paypal_url'])];
        }
        return [
            'token' => $d['token'],
            'token_txt' => $d['token_txt'],
            'minimo' => $d['minimo'],
            'minimo_txt' => $d['minimo_txt'],
            'tabela' => array_map(static function (int $n) use ($d): array {
                return [
                    'tokens' => $n,
                    'tokens_txt' => garc_tokens_txt($n),
                    'preco_txt' => garc_eur($n * $d['token']),
                ];
            }, $d['exemplos']),
            'iva' => $d['iva'],
            'validade' => $d['validade'],
            'sob_consulta' => $d['sob_consulta'],
            'entrega' => $d['entrega'],
            'meios_txt' => $d['meios_txt'],
            'pagamentos' => $pagamentos,
        ];
    }

    // ------------------------------------------------------------------------------- notícias

    function garc_data_noticia(string $texto): ?string
    {
        $t = trim($texto);
        if (preg_match('#^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$#', $t, $m) && checkdate((int) $m[2], (int) $m[1], (int) $m[3])) {
            return sprintf('%04d-%02d-%02d', $m[3], $m[2], $m[1]);
        }
        if (preg_match('#^(\d{4})-(\d{1,2})-(\d{1,2})$#', $t, $m) && checkdate((int) $m[2], (int) $m[3], (int) $m[1])) {
            return sprintf('%04d-%02d-%02d', $m[1], $m[2], $m[3]);
        }
        return null;
    }

    function garc_data_extenso(string $iso): string
    {
        $meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
            'setembro', 'outubro', 'novembro', 'dezembro'];
        [$a, $m, $dia] = array_map('intval', explode('-', $iso));
        return "$dia de {$meses[$m - 1]} de $a";
    }

    function garc_ancora(string $titulo): string
    {
        $t = strtr($titulo, [
            'á' => 'a', 'à' => 'a', 'â' => 'a', 'ã' => 'a', 'ä' => 'a', 'é' => 'e', 'è' => 'e', 'ê' => 'e', 'ë' => 'e',
            'í' => 'i', 'ì' => 'i', 'î' => 'i', 'ï' => 'i', 'ó' => 'o', 'ò' => 'o', 'ô' => 'o', 'õ' => 'o', 'ö' => 'o',
            'ú' => 'u', 'ù' => 'u', 'û' => 'u', 'ü' => 'u', 'ç' => 'c', 'ñ' => 'n',
            'Á' => 'A', 'À' => 'A', 'Â' => 'A', 'Ã' => 'A', 'Ä' => 'A', 'É' => 'E', 'È' => 'E', 'Ê' => 'E', 'Ë' => 'E',
            'Í' => 'I', 'Ì' => 'I', 'Î' => 'I', 'Ï' => 'I', 'Ó' => 'O', 'Ò' => 'O', 'Ô' => 'O', 'Õ' => 'O', 'Ö' => 'O',
            'Ú' => 'U', 'Ù' => 'U', 'Û' => 'U', 'Ü' => 'U', 'Ç' => 'C', 'Ñ' => 'N',
        ]);
        $t = strtolower(preg_replace('/[^A-Za-z0-9]+/', '-', $t));
        return trim($t, '-') ?: 'noticia';
    }

    /** Lê uma notícia: cabeçalho (Título, Data) até à primeira linha vazia, depois o texto. */
    function garc_ler_noticia(string $texto, string $nome, int $alterado): ?array
    {
        $texto = preg_replace('/^\xEF\xBB\xBF/', '', $texto);
        $linhas = preg_split('/\R/u', $texto);
        $titulo = '';
        $data = null;
        while ($linhas && trim($linhas[0]) !== '') {
            $l = array_shift($linhas);
            if (preg_match('/^\s*t[ií]tulo\s*:(.*)$/iu', $l, $m)) {
                $titulo = trim($m[1]);
            } elseif (preg_match('/^\s*data\s*:(.*)$/iu', $l, $m)) {
                $data = garc_data_noticia($m[1]);
            } else {
                array_unshift($linhas, $l);
                break;
            }
        }
        if ($titulo === '') {
            // sem a linha "Título:", o título é a primeira linha com texto
            while ($linhas && trim($linhas[0]) === '') {
                array_shift($linhas);
            }
            $titulo = trim((string) array_shift($linhas));
            if ($titulo === '') {
                return null;
            }
        }
        $blocos = [];
        foreach (preg_split('/\n\s*\n/u', trim(implode("\n", $linhas))) as $b) {
            $b = trim($b);
            if ($b === '') {
                continue;
            }
            $ls = array_map('trim', explode("\n", $b));
            $itens = [];
            foreach ($ls as $x) {
                if (preg_match('/^[-*•]\s+/u', $x)) {
                    $itens[] = trim(preg_replace('/^[-*•]\s+/u', '', $x));
                }
            }
            $blocos[] = count($itens) === count($ls) ? ['lista' => $itens] : ['paragrafo' => $ls];
        }
        return [
            'titulo' => $titulo,
            'data' => $data ?? date('Y-m-d', $alterado),
            'ficheiro' => $nome,
            'blocos' => $blocos,
        ];
    }

    function garc_noticias(): array
    {
        garc_conteudos_preparar();
        $lista = [];
        foreach (garc_txts(garc_conteudos_dir() . '/noticias') as $f) {
            $nome = basename($f);
            if ($nome[0] === '_' || !is_file($f)) {
                continue;
            }
            $n = garc_ler_noticia((string) @file_get_contents($f), $nome, (int) @filemtime($f));
            if ($n) {
                $lista[] = $n;
            }
        }
        usort($lista, static function (array $a, array $b): int {
            return [$b['data'], $a['ficheiro']] <=> [$a['data'], $b['ficheiro']];
        });
        return $lista;
    }

    function garc_texto_noticia(string $s): string
    {
        $s = htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
        return preg_replace_callback('#https?://[^\s<>"\']+#u', static function ($m) {
            $url = rtrim($m[0], '.,;:!?)');
            $resto = substr($m[0], strlen($url));
            return '<a href="' . $url . '" target="_blank" rel="noopener">' . $url . '</a>' . $resto;
        }, $s);
    }

    function garc_noticias_html(): string
    {
        $noticias = garc_noticias();
        if (!$noticias) {
            return '<p class="muted">Ainda não há notícias.</p>';
        }
        $usadas = [];
        $html = '';
        foreach ($noticias as $n) {
            $id = garc_ancora($n['titulo']);
            $base = $id;
            for ($i = 2; isset($usadas[$id]); $i++) {
                $id = "$base-$i";
            }
            $usadas[$id] = true;
            $corpo = '';
            foreach ($n['blocos'] as $b) {
                if (isset($b['lista'])) {
                    $corpo .= "\n        <ul>";
                    foreach ($b['lista'] as $x) {
                        $corpo .= "\n          <li>" . garc_texto_noticia($x) . '</li>';
                    }
                    $corpo .= "\n        </ul>";
                } else {
                    $corpo .= "\n        <p>" . implode('<br>', array_map('garc_texto_noticia', $b['paragrafo'])) . '</p>';
                }
            }
            $html .= "\n      <article class=\"article\" id=\"$id\">"
                . "\n        <time datetime=\"{$n['data']}\">" . garc_data_extenso($n['data']) . '</time>'
                . "\n        <h2>" . htmlspecialchars($n['titulo'], ENT_QUOTES, 'UTF-8') . '</h2>'
                . $corpo
                . "\n      </article>";
        }
        return '<div class="articles">' . $html . "\n    </div>";
    }
}
