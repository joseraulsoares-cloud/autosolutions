# Site da GARC – Soluções Técnicas

Site da GARC – Soluções Técnicas, Unipessoal Lda, em www.autosolutions.pt: serviços, preços em tokens, loja, notícias, páginas legais e área de cliente para oficinas.

## Estrutura

- `build.py` gera todas as páginas. Os dados da empresa (morada, telefone, email, NIPC…) estão no dicionário `DADOS`; os custos em tokens estão em `TOKENS` e os pacotes em `PACOTES`, no início do ficheiro.
- `src/assets/` tem os estilos, os scripts, o ícone e as fontes (Barlow e Barlow Condensed, licença SIL Open Font License, em `src/assets/fonts/OFL.txt`).
- `site/` é o site gerado, que vai para a pasta `public_html` do alojamento. Não se edita à mão.
- `app/` tem o código do servidor da área de cliente, que fica fora de `public_html`. O ficheiro `app/catalogo.php` é gerado pelo `build.py`.
- `preview/` é uma versão de revisão, com a área de cliente em modo de demonstração. Não entra no repositório.

## Alterar o site

1. Editar `build.py` ou os ficheiros em `src/`.
2. Gerar o site: `python3 build.py` (Python 3.8 ou mais recente, sem dependências).
3. Ver a lista "Por preencher" que o comando mostra no fim.
4. Fazer commit das alterações, incluindo as pastas `site/` e `app/`.

## Alojamento

- Dominios.pt, com cPanel (Apache, PHP e MySQL), no domínio www.autosolutions.pt.
- O conteúdo de `site/` é copiado para `public_html`. O `site/.htaccess` trata dos endereços sem `.html`, da página 404, do redirecionamento para `https://www.autosolutions.pt` e dos cabeçalhos de segurança.

## Área de cliente

Em construção, em PHP e MySQL para correr no cPanel: registo das oficinas com aprovação, entrada por código enviado por email, saldo de tokens, pedidos com envio do ficheiro, entrega pela área de cliente, por email ou por WhatsApp, e painel de administração.
