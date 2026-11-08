# Notas para o Claude

- Língua do site, do código e dos commits: português de Portugal.
- O HTML é gerado por `build.py`. Nunca editar `site/` nem `preview/` à mão: alterar `build.py` ou `src/`, correr `python3 build.py` e fazer commit de `site/` e `app/` junto com a fonte. `app/catalogo.php` também é gerado.
- Alojamento: cPanel da Dominios.pt (Apache, PHP, MySQL), domínio www.autosolutions.pt. `site/` vai para `public_html`; `app/` fica fora de `public_html` (`.cpanel.yml`).
- API da área de cliente: `app/` (PHP 8.1+, MySQL, migrações em `app/migracoes/`), entrada em `src/api/index.php`. Usar só GET e POST (os alojamentos partilhados bloqueiam muitas vezes PUT e DELETE). Os testes estão em `tests/` e devem passar antes de cada commit que toque na API.
- Dados da empresa: dicionário `DADOS` em `build.py`. Custos em tokens: `TOKENS`; pacotes: `PACOTES`. Os campos vazios aparecem a amarelo e o build lista-os no fim.
- Logótipo: `src/logo-cabecalho.html` (cabeçalho, cores pelas variáveis `--logo-*`) e `src/assets/logo-garc.svg`, gerados por `ferramentas/logo/` a partir do PNG original. Os botões e as faixas usam o azul do logótipo (`#012559`).
- Ligações internas e caminhos de recursos passam por `url()` e `asset()`: relativos e com `.html` na pré-visualização, absolutos e sem `.html` no site publicado (o `.htaccess` faz a correspondência).
- Os módulos de sistemas de emissões (DPF, EGR, AdBlue/SCR, lambda) levam sempre o aviso de uso exclusivo em competição ou fora da via pública e a declaração obrigatória no formulário de pedido, verificada também no servidor.
