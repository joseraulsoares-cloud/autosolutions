# Site da GARC – Soluções Técnicas

Site estático da GARC – Soluções Técnicas, Unipessoal Lda: serviços, pedido de ficheiro, loja, notícias e páginas legais.

## Estrutura

- `build.py` gera todas as páginas. Os dados da empresa (morada, telefone, email, NIPC…) estão no dicionário `DADOS`, no início do ficheiro.
- `src/assets/` tem os estilos, o script, o ícone e as fontes (Barlow e Barlow Condensed, licença SIL Open Font License, em `src/assets/fonts/OFL.txt`).
- `site/` é o site gerado, que o Cloudflare Pages publica. Não se edita à mão.
- `preview/` é uma versão de revisão, sem envio de formulários. Não entra no repositório.

## Alterar o site

1. Editar `build.py` ou os ficheiros em `src/assets/`.
2. Gerar o site: `python3 build.py` (Python 3.8 ou mais recente, sem dependências).
3. Ver a lista "Por preencher" que o comando mostra no fim.
4. Fazer commit das alterações, incluindo a pasta `site/`.

## Publicação no Cloudflare Pages

- Repositório ligado ao Cloudflare Pages, com `main` como ramo de produção.
- Predefinição de framework: nenhuma. Comando de build: vazio. Diretório de saída: `site`.
- `site/_headers` define os cabeçalhos de segurança e a cache das fontes.
- O Cloudflare Pages serve `servicos.html` em `/servicos`; as ligações internas do site já usam esses endereços.

## Formulários

Os formulários enviam para `/api/pedido` (pedido de ficheiro, com anexo) e `/api/contacto`. Estas rotas vão ser criadas como Pages Functions na pasta `functions/`. Até lá, o envio mostra uma mensagem de erro.
