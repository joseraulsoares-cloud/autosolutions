-- Custo definido no painel. No envio descontam-se os tokens mínimos; o custo final é definido depois de analisada
-- a ECU. "pagos" são os tokens já descontados do saldo; "custo_definido" indica que o custo já é o final.
-- "a_aguardar_saldo": o custo final é maior do que o pago e o saldo não chega para a diferença.
-- "fechado_em" e "ficheiros_apagados" servem para apagar os ficheiros ao fim do prazo de conservação.

ALTER TABLE pedidos
  MODIFY estado ENUM('a_aguardar_ficheiro', 'recebido', 'em_curso', 'a_aguardar_saldo', 'concluido', 'recusado', 'cancelado') NOT NULL DEFAULT 'a_aguardar_ficheiro',
  ADD COLUMN pagos INT NOT NULL DEFAULT 0 AFTER tokens,
  ADD COLUMN custo_definido TINYINT(1) NOT NULL DEFAULT 0 AFTER pagos,
  ADD COLUMN fechado_em DATETIME NULL AFTER concluido_em,
  ADD COLUMN ficheiros_apagados TINYINT(1) NOT NULL DEFAULT 0 AFTER devolvido;

UPDATE pedidos SET pagos = tokens, custo_definido = 1;

UPDATE pedidos SET fechado_em = COALESCE(concluido_em, criado_em) WHERE estado IN ('concluido', 'recusado', 'cancelado');
