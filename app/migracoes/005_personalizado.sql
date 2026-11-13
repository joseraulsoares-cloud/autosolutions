-- Pedido personalizado: descrição escrita pela oficina para trabalhos que não estão na lista.
ALTER TABLE pedidos ADD COLUMN personalizado TEXT NULL AFTER modulos;
