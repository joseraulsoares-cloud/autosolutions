<?php
declare(strict_types=1);

// Limites por endereço IP nos formulários que enviam emails, para que um robô não esgote
// o envio de emails do alojamento nem use o site para enviar mensagens a terceiros.

const LIMITES = [
    'registo' => [5, 3600, 'Fez vários registos seguidos. Tente de novo dentro de uma hora ou contacte-nos.'],
    'contacto' => [5, 3600, 'Enviou várias mensagens seguidas. Tente de novo mais tarde ou contacte-nos por telefone.'],
    'codigo' => [10, 900, 'Pediu vários códigos seguidos. Aguarde alguns minutos e tente de novo.'],
];

function ip_cliente(): string
{
    if (cfg('dev')) {
        // Nos testes locais, só há limite quando o teste indica um IP.
        return (string) ($_SERVER['HTTP_X_TESTE_IP'] ?? '');
    }
    return (string) ($_SERVER['REMOTE_ADDR'] ?? '');
}

function limitar(string $acao): void
{
    [$max, $janela, $mensagem] = LIMITES[$acao];
    $ip = ip_cliente();
    if ($ip === '') {
        return;
    }
    $chave = substr(hash_hmac('sha256', $ip, segredo()), 0, 32);
    $agora = time();
    executar('DELETE FROM limites WHERE criado_em < ?', [$agora - 86400]);
    $n = (int) valor('SELECT COUNT(*) FROM limites WHERE acao = ? AND chave = ? AND criado_em > ?', [$acao, $chave, $agora - $janela]);
    if ($n >= $max) {
        throw new ErroHttp(429, $mensagem);
    }
    executar('INSERT INTO limites (acao, chave, criado_em) VALUES (?, ?, ?)', [$acao, $chave, $agora]);
}
