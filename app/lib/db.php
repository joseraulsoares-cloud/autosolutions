<?php
declare(strict_types=1);

function db(): PDO
{
    static $pdo = null;
    if ($pdo) {
        return $pdo;
    }
    $c = cfg('db');
    $dsn = sprintf('mysql:host=%s;dbname=%s;charset=utf8mb4', $c['host'] ?? 'localhost', $c['nome'] ?? '');
    if (!empty($c['porta'])) {
        $dsn .= ';port=' . (int) $c['porta'];
    }
    if (!empty($c['socket'])) {
        $dsn = sprintf('mysql:unix_socket=%s;dbname=%s;charset=utf8mb4', $c['socket'], $c['nome'] ?? '');
    }
    $pdo = new PDO($dsn, $c['utilizador'] ?? '', $c['palavra_passe'] ?? '', [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $pdo->exec("SET time_zone = '+00:00'");
    migrar($pdo);
    return $pdo;
}

// Aplica as migrações em app/migracoes que ainda não foram aplicadas.
function migrar(PDO $pdo): void
{
    $ficheiros = glob(GARC_APP . '/migracoes/*.sql') ?: [];
    sort($ficheiros);
    if (!$ficheiros) {
        return;
    }
    $ultima = basename(end($ficheiros));
    $marca = ficheiros_dir() . '/.migracao';
    if (is_file($marca) && trim((string) file_get_contents($marca)) === $ultima) {
        return;
    }
    $pdo->query("SELECT GET_LOCK('garc_migracao', 30)");
    try {
        $pdo->exec('CREATE TABLE IF NOT EXISTS migracoes (nome VARCHAR(100) NOT NULL PRIMARY KEY, aplicada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB');
        $feitas = $pdo->query('SELECT nome FROM migracoes')->fetchAll(PDO::FETCH_COLUMN);
        foreach ($ficheiros as $f) {
            $nome = basename($f);
            if (in_array($nome, $feitas, true)) {
                continue;
            }
            $sql = preg_replace('/^\s*--.*$/m', '', (string) file_get_contents($f));
            foreach (preg_split('/;\s*(\r?\n|$)/', $sql) as $instrucao) {
                if (trim($instrucao) !== '') {
                    $pdo->exec($instrucao);
                }
            }
            $pdo->prepare('INSERT INTO migracoes (nome) VALUES (?)')->execute([$nome]);
        }
        @file_put_contents($marca, $ultima);
    } finally {
        $pdo->query("SELECT RELEASE_LOCK('garc_migracao')");
    }
}

function um(string $sql, array $params = []): ?array
{
    $st = db()->prepare($sql);
    $st->execute($params);
    $r = $st->fetch();
    return $r === false ? null : $r;
}

function todos(string $sql, array $params = []): array
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st->fetchAll();
}

function valor(string $sql, array $params = [])
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st->fetchColumn();
}

function executar(string $sql, array $params = []): int
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st->rowCount();
}

function transacao(callable $f)
{
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $r = $f($pdo);
        $pdo->commit();
        return $r;
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        throw $e;
    }
}

function saldo(int $oficinaId): int
{
    return (int) valor('SELECT COALESCE(SUM(tokens), 0) FROM movimentos WHERE oficina_id = ?', [$oficinaId]);
}
