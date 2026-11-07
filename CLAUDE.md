# Notas para o Claude

- Língua do site, do código e dos commits: português de Portugal.
- O HTML é gerado por `build.py`. Nunca editar `site/` nem `preview/` à mão: alterar `build.py` ou `src/assets/`, correr `python3 build.py` e fazer commit de `site/` junto com a fonte.
- Dados da empresa: dicionário `DADOS` em `build.py`. Os campos vazios aparecem a amarelo e o build lista-os no fim.
- Ligações internas e caminhos de recursos passam por `url()` e `asset()`: relativos e com `.html` na pré-visualização, absolutos e sem `.html` no site publicado.
- Os módulos de sistemas de emissões (DPF, EGR, AdBlue/SCR, lambda) levam sempre o aviso de uso exclusivo em competição ou fora da via pública e a declaração obrigatória no formulário de pedido.
