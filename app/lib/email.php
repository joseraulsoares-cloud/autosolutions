<?php
declare(strict_types=1);

// Emails enviados pelo próprio alojamento (função mail() do PHP, com a conta definida em email_de).

function remetente(): array
{
    $de = (string) cfg('email_de');
    if (preg_match('/^\s*(.*?)\s*<([^>]+)>\s*$/u', $de, $m)) {
        return [$m[1], $m[2]];
    }
    return ['', trim($de)];
}

function cabecalho_codificado(string $s): string
{
    $s = trim(preg_replace('/[\r\n]+/', ' ', $s));
    return preg_match('/[^\x20-\x7E]/', $s) ? '=?UTF-8?B?' . base64_encode($s) . '?=' : $s;
}

function html_de_texto(string $t): string
{
    $e = htmlspecialchars($t, ENT_QUOTES, 'UTF-8');
    $e = preg_replace('~(https?://[^\s<]+)~', '<a href="$1">$1</a>', $e);
    $paragrafos = array_map(
        fn($p) => '<p style="margin:0 0 14px">' . nl2br($p, false) . '</p>',
        preg_split('/\n{2,}/', $e)
    );
    return '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;color:#101C27">'
        . implode('', $paragrafos) . '</div>';
}

/**
 * @param array $anexos lista de ['nome' => ..., 'caminho' => ...]
 */
function enviar_email(string $para, string $assunto, string $texto, array $anexos = [], ?string $responderPara = null): void
{
    if (cfg('dev')) {
        $info = array_map(fn($a) => ['nome' => $a['nome'], 'tamanho' => @filesize($a['caminho']) ?: 0], $anexos);
        executar(
            'INSERT INTO emails_dev (para, assunto, texto, anexos) VALUES (?, ?, ?, ?)',
            [$para, $assunto, $texto, json_encode($info, JSON_UNESCAPED_UNICODE)]
        );
        return;
    }

    [$nome, $email] = remetente();
    if ($email === '') {
        throw new RuntimeException('Configuração: falta o email_de.');
    }
    $alt = '=_alt_' . bin2hex(random_bytes(12));
    $partesTexto = "--$alt\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n"
        . chunk_split(base64_encode($texto))
        . "--$alt\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n"
        . chunk_split(base64_encode(html_de_texto($texto)))
        . "--$alt--\r\n";

    $cab = [
        'From: ' . ($nome !== '' ? cabecalho_codificado($nome) . " <$email>" : $email),
        'MIME-Version: 1.0',
    ];
    if ($responderPara) {
        $cab[] = "Reply-To: $responderPara";
    }

    if ($anexos) {
        $mix = '=_mix_' . bin2hex(random_bytes(12));
        $cab[] = "Content-Type: multipart/mixed; boundary=\"$mix\"";
        $corpo = "--$mix\r\nContent-Type: multipart/alternative; boundary=\"$alt\"\r\n\r\n" . $partesTexto;
        foreach ($anexos as $a) {
            $n = addcslashes($a['nome'], "\"\\");
            $corpo .= "--$mix\r\nContent-Type: application/octet-stream; name=\"$n\"\r\n"
                . "Content-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename=\"$n\"\r\n\r\n"
                . chunk_split(base64_encode((string) file_get_contents($a['caminho'])));
        }
        $corpo .= "--$mix--\r\n";
    } else {
        $cab[] = "Content-Type: multipart/alternative; boundary=\"$alt\"";
        $corpo = $partesTexto;
    }

    if (!mail($para, cabecalho_codificado($assunto), $corpo, implode("\r\n", $cab), '-f' . $email)) {
        throw new RuntimeException('A função mail() recusou o envio.');
    }
}

// Envia depois de a resposta seguir; uma falha fica no registo de erros do PHP.
function notificar(string $para, string $assunto, string $texto, array $anexos = [], ?string $responderPara = null): void
{
    depois(fn() => enviar_email($para, $assunto, $texto, $anexos, $responderPara));
}

function notificar_admins(string $assunto, string $texto, array $anexos = []): void
{
    foreach (emails_admin() as $a) {
        notificar($a, $assunto, $texto, $anexos);
    }
}

function assinatura_email(): string
{
    return "\n\n" . nome_site() . "\n" . site_url();
}
