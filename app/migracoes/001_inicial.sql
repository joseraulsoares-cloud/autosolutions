-- Área de cliente: oficinas, saldo de tokens, pedidos, códigos de acesso e sessões (MySQL / MariaDB).

CREATE TABLE oficinas (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  nif VARCHAR(20) NOT NULL,
  responsavel VARCHAR(120) NOT NULL,
  email VARCHAR(200) NOT NULL,
  telefone VARCHAR(30) NOT NULL,
  whatsapp VARCHAR(30) NULL,
  entrega ENUM('portal', 'email', 'whatsapp') NOT NULL DEFAULT 'portal',
  estado ENUM('pendente', 'aprovada', 'recusada', 'suspensa') NOT NULL DEFAULT 'pendente',
  criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  aprovada_em DATETIME NULL,
  UNIQUE KEY oficinas_nif (nif),
  UNIQUE KEY oficinas_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pedidos (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  oficina_id INT UNSIGNED NOT NULL,
  estado ENUM('a_aguardar_ficheiro', 'recebido', 'em_curso', 'concluido', 'recusado', 'cancelado') NOT NULL DEFAULT 'a_aguardar_ficheiro',
  viatura VARCHAR(120) NOT NULL,
  motor VARCHAR(80) NULL,
  ano CHAR(4) NULL,
  ecu VARCHAR(80) NOT NULL,
  ferramenta VARCHAR(80) NULL,
  metodo VARCHAR(20) NULL,
  modulos TEXT NOT NULL,
  tokens INT NOT NULL,
  declaracao_emissoes TINYINT(1) NOT NULL DEFAULT 0,
  observacoes TEXT NULL,
  entrega ENUM('portal', 'email', 'whatsapp') NOT NULL,
  whatsapp VARCHAR(30) NULL,
  original_chave VARCHAR(255) NULL,
  original_nome VARCHAR(150) NULL,
  original_tamanho INT UNSIGNED NULL,
  modificado_chave VARCHAR(255) NULL,
  modificado_nome VARCHAR(150) NULL,
  modificado_tamanho INT UNSIGNED NULL,
  nota TEXT NULL,
  devolvido TINYINT(1) NOT NULL DEFAULT 0,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recebido_em DATETIME NULL,
  concluido_em DATETIME NULL,
  KEY pedidos_oficina (oficina_id, id),
  KEY pedidos_estado (estado, id),
  CONSTRAINT pedidos_oficina_fk FOREIGN KEY (oficina_id) REFERENCES oficinas (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Livro do saldo: o saldo de uma oficina é a soma dos tokens dos seus movimentos.
CREATE TABLE movimentos (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  oficina_id INT UNSIGNED NOT NULL,
  tokens INT NOT NULL,
  tipo ENUM('carregamento', 'pedido', 'devolucao', 'acerto') NOT NULL,
  pedido_id INT UNSIGNED NULL,
  referencia VARCHAR(120) NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY movimentos_oficina (oficina_id, id),
  CONSTRAINT movimentos_oficina_fk FOREIGN KEY (oficina_id) REFERENCES oficinas (id),
  CONSTRAINT movimentos_pedido_fk FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE codigos (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(200) NOT NULL,
  hash CHAR(64) NOT NULL,
  expira_em INT UNSIGNED NOT NULL,
  tentativas TINYINT UNSIGNED NOT NULL DEFAULT 0,
  criado_em INT UNSIGNED NOT NULL,
  KEY codigos_email (email, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sessoes (
  hash CHAR(64) NOT NULL PRIMARY KEY,
  email VARCHAR(200) NOT NULL,
  expira_em INT UNSIGNED NOT NULL,
  KEY sessoes_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Só usada em desenvolvimento ('dev' => true): guarda os emails em vez de os enviar.
CREATE TABLE emails_dev (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  para VARCHAR(200) NOT NULL,
  assunto VARCHAR(255) NOT NULL,
  texto TEXT NOT NULL,
  anexos TEXT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
