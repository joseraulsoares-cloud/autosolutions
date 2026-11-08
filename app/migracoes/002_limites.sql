-- Limites por endereço IP nos formulários públicos (registo, contacto e códigos de entrada).
-- O IP não é guardado: guarda-se um código derivado dele, apagado ao fim de 24 horas.

CREATE TABLE limites (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  acao VARCHAR(20) NOT NULL,
  chave CHAR(32) NOT NULL,
  criado_em INT UNSIGNED NOT NULL,
  KEY limites_acao (acao, chave, criado_em),
  KEY limites_data (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
