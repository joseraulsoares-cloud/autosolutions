# Site da GARC – Soluções Técnicas

Site da GARC – Soluções Técnicas, Unipessoal Lda, em www.autosolutions.pt: serviços, preços em tokens, loja, notícias, páginas legais e área de cliente para oficinas.

## Estrutura

- `build.py` gera todas as páginas. Os dados da empresa (morada, telefone, email, NIPC, IBAN…) estão no dicionário `DADOS`; os custos em tokens estão em `TOKENS` e os pacotes em `PACOTES`, no início do ficheiro.
- `src/assets/` tem os estilos, os scripts, o ícone e as fontes (Barlow e Barlow Condensed, licença SIL Open Font License, em `src/assets/fonts/OFL.txt`). `src/api/` tem a entrada da API em PHP.
- `site/` é o site gerado, que vai para a pasta `public_html` do alojamento. Não se edita à mão.
- `app/` é o código do servidor da área de cliente (PHP 8.1 ou mais recente, MySQL), que fica fora de `public_html`. O ficheiro `app/catalogo.php` é gerado pelo `build.py`.
- `preview/` é uma versão de revisão, com a área de cliente em modo de demonstração. Não entra no repositório.
- `tests/` tem os testes da API e do browser.
- `ferramentas/logo/` tem o logótipo original (PNG) e os scripts que o passam a vetor.

## Logótipo

O logótipo da GARC foi vetorizado a partir de `ferramentas/logo/logo-original.png` (PNG de 640×640, com compressão), por isso as letras pequenas do lema ficam ligeiramente arredondadas em tamanhos grandes. Se houver o logótipo original em vetor (SVG, PDF ou AI), deve substituir estes ficheiros.

- `src/logo-cabecalho.html`: SVG do cabeçalho, com uma versão larga (com o lema) e uma curta (só a marca e GARC, abaixo de 560 px de largura). As cores vêm das variáveis `--logo-azul`, `--logo-cinza` e `--logo-prata` do `styles.css`, que mudam no tema escuro.
- `src/assets/logo-garc.svg`: logótipo completo, com as cores originais.
- `src/assets/favicon.svg`, `favicon.ico` e `apple-touch-icon.png`: ícones do separador e do ecrã inicial.

Para gerar de novo (precisa de `potrace`, `rsvg-convert`, Pillow, NumPy e SciPy):

```
python3 ferramentas/logo/vetorizar.py ferramentas/logo/logo-original.png /tmp/logo
python3 ferramentas/logo/compor.py /tmp/logo/pecas.json /tmp/logo/final
```

Depois copiar `logo-cabecalho.html` para `src/` e os restantes ficheiros para `src/assets/`.

## Alterar o site

1. Editar `build.py` ou os ficheiros em `src/` e `app/`.
2. Gerar o site: `python3 build.py` (Python 3.8 ou mais recente, sem dependências).
3. Ver a lista "Por preencher" que o comando mostra no fim.
4. Fazer commit das alterações, incluindo as pastas `site/` e `app/`.

## Área de cliente

- As oficinas registam-se com NIF e só entram depois de aprovadas no painel (`/admin`).
- A entrada faz-se com um código de 6 dígitos enviado por email, válido 10 minutos. Não há palavras-passe.
- Os tokens são carregados no painel, com o número da fatura. Cada pedido desconta os tokens dos módulos escolhidos; os tokens voltam ao saldo se o pedido for recusado ou cancelado antes do envio do ficheiro.
- O ficheiro modificado é entregue pela área de cliente, por email com anexo ou por WhatsApp (o painel abre a conversa com a mensagem escrita).
- A API só usa GET e POST e só aceita POST vindos do próprio site.
- Os formulários que enviam emails têm limites por endereço IP (`app/lib/limites.php`): registo e contacto, 5 por hora; códigos de entrada, 10 em 15 minutos. O IP não fica guardado, só um código derivado dele, apagado ao fim de 24 horas. O registo e o contacto têm também um campo-armadilha para robôs.

## Instalação no cPanel (Dominios.pt)

1. **PHP**: em MultiPHP Manager, PHP 8.1 ou mais recente para o domínio.
2. **Base de dados**: em MySQL Database Wizard, criar a base de dados e um utilizador com todas as permissões.
3. **Email**: criar a conta que envia os emails (ex.: pedidos@autosolutions.pt) e confirmar SPF e DKIM em Email Deliverability.
4. **Código**: em Git Version Control, clonar `https://github.com/joseraulsoares-cloud/autosolutions` e usar "Deploy HEAD Commit". O `.cpanel.yml` copia `site/` para `public_html` e `app/` para `~/autosolutions-app`. Em alternativa, enviar as duas pastas pelo Gestor de Ficheiros.
5. **Configuração**: em `~/autosolutions-app/`, copiar `config.exemplo.php` para `config.php` e preencher: base de dados, emails de administração, remetente, pasta dos ficheiros (`/home/UTILIZADOR/autosolutions-dados/ficheiros`) e um segredo com 64 caracteres aleatórios.
6. **Limites de envio**: `site/api/.user.ini` sobe o limite de ficheiros para 32 MB. Se o alojamento o ignorar, definir `upload_max_filesize` e `post_max_size` no MultiPHP INI Editor.
7. **Primeiro acesso**: abrir `https://www.autosolutions.pt/admin` e entrar com um dos emails de administração. As tabelas são criadas automaticamente no primeiro acesso à API.

O `site/.htaccess` trata dos endereços sem `.html`, da página 404, do redirecionamento para `https://www.autosolutions.pt` e dos cabeçalhos de segurança.

## Testes

Com PHP 8.1+, MariaDB ou MySQL e Python 3 (`requests`; `playwright` para o teste no browser):

1. Criar uma base de dados de teste e um `config.php` de teste com `'dev' => true` (os emails ficam na tabela `emails_dev`).
2. Arrancar o servidor: `GARC_APP=<app> SITE_ROOT=<site> php -d upload_max_filesize=32M -d post_max_size=40M -S 127.0.0.1:8790 -t <site> tests/router.php`.
3. Correr `python3 tests/teste_api.py` e `python3 tests/teste_ui.py <pasta-de-saida>`.

Os testes precisam de preços em `TOKENS`; sem preços, os módulos não podem ser pedidos.
