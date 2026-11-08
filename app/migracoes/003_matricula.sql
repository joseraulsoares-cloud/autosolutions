-- Matrícula da viatura em cada pedido (obrigatória nos pedidos novos; a API valida-a).

ALTER TABLE pedidos ADD COLUMN matricula VARCHAR(20) NULL AFTER ano;
