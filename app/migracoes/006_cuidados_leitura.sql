-- Confirmação, no envio do pedido, de que a oficina leu e seguiu os cuidados de preparação da leitura.
ALTER TABLE pedidos ADD COLUMN cuidados_leitura TINYINT(1) NOT NULL DEFAULT 0 AFTER declaracao_emissoes;
