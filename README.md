# Site da GARC – Soluções Técnicas

Site da GARC – Soluções Técnicas, Unipessoal Lda, em www.autosolutions.pt: serviços, notícias, páginas legais e área de cliente para oficinas (com os preços em tokens, só para contas aprovadas).

## Estrutura

- `build.py` gera todas as páginas. Os dados da empresa (sede, conservatória, NIPC, WhatsApp, email…) estão no dicionário `DADOS`. Os valores que mudam (preços, prazo de entrega, horário, pagamentos) e as notícias alteram-se no servidor, sem mexer no código (ver «Alterar preços, prazos, horário e pagamentos»); os valores de origem estão em `app/conteudos-iniciais/`.
- `src/assets/` tem os estilos, os scripts, o ícone e as fontes (Barlow e Barlow Condensed, licença SIL Open Font License, em `src/assets/fonts/OFL.txt`). `src/api/` tem a entrada da API em PHP.
- `site/` é o site gerado, que vai para a pasta `public_html` do alojamento. Não se edita à mão.
- `app/` é o código do servidor da área de cliente (PHP 8.1 ou mais recente, MySQL), que fica fora de `public_html`. O ficheiro `app/catalogo.php` é gerado pelo `build.py`. `app/conteudos.php` lê os valores e as notícias alteráveis (não precisa da base de dados).
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

## Alterar preços, prazos, horário e pagamentos

No servidor, ao lado de `public_html`, há a pasta `garc-conteudos` (criada automaticamente na primeira visita a Serviços, Notícias, Sobre ou Termos, ou na primeira entrada na área de cliente). As atualizações do site nunca lhe tocam.

1. No cPanel, abrir o Gestor de Ficheiros e entrar em `garc-conteudos`.
2. Selecionar `dados.txt` e carregar em Edit.
3. Mudar só o que está à direita dos dois pontos e carregar em Save Changes. As alterações aparecem logo no site.

O `dados.txt` tem: preço do token, carregamento mínimo (que é também o número de tokens descontado no envio de cada pedido), carregamentos de exemplo da tabela, IVA, validade dos tokens, unidades sob consulta, prazo de entrega, horário, MB WAY, PayPal.Me e ligação de pagamento por cartão (Stripe). Um meio de pagamento vazio deixa de aparecer. Um valor que não seja válido (por exemplo, letras no preço) é ignorado e o site usa o valor de origem.

Os preços só aparecem na área de cliente, no separador Preços, a contas aprovadas: vêm da API com a sessão e não ficam no HTML de nenhuma página. O endereço antigo `/precos` leva à área de cliente.

## Publicar notícias

Na pasta `garc-conteudos/noticias`, cada ficheiro `.txt` é uma notícia: primeira linha `Título: …`, segunda `Data: dd/mm/aaaa`, uma linha em branco e o texto (parágrafos separados por linha em branco; linhas começadas por `- ` ficam em lista; os endereços `https://…` ficam com ligação). Aparecem logo na página Notícias, a mais recente primeiro. Os ficheiros cujo nome começa por `_` não aparecem (o `_como-escrever-uma-noticia.txt` explica o formato).

## Área de cliente

- As oficinas registam-se com NIF e só entram depois de aprovadas no painel (`/admin`).
- A entrada faz-se com um código de 6 dígitos enviado por email, válido 10 minutos. Não há palavras-passe.
- Cada pedido exige a matrícula da viatura, portuguesa ou estrangeira (até 15 carateres: letras, números, espaços e hífenes). Fica em maiúsculas, e as portuguesas sem hífenes ficam no formato AA-00-AA. A matrícula aparece no painel, na área de cliente e nos emails e mensagens de WhatsApp do pedido.
- Os tokens são carregados no painel, com o número da fatura. O preço do token e o mínimo estão no `dados.txt` do servidor (valores de origem: 1 token = 6 €, IVA incluído, a partir de 5 tokens).
- O custo de cada pedido depende da ECU. No envio desconta-se o mínimo (5 tokens, nos valores de origem); depois de analisar a ECU, o administrador define o custo final no painel. Se o saldo chegar, a diferença é descontada logo; se não chegar, o pedido fica "à espera de saldo" e avança sozinho quando forem carregados tokens (por ordem de chegada). Baixar o custo devolve a diferença.
- Depois de enviado o ficheiro, a oficina já não pode cancelar o pedido. Se o administrador o recusar, os tokens pagos voltam ao saldo. Antes de enviar o ficheiro, a oficina pode cancelar e recuperar os 5 tokens.
- Prazos de conservação (1 mês): os ficheiros dos pedidos concluídos, recusados ou cancelados são apagados um mês depois de fechados, e os pedidos que ficaram sem ficheiro durante um mês são cancelados, com devolução dos tokens. A limpeza corre no máximo uma vez por hora, quando o painel ou a lista de pedidos são abertos.
- O ficheiro modificado é entregue pela área de cliente, por email com anexo ou por WhatsApp (o painel abre a conversa com a mensagem escrita).
- A API só usa GET e POST e só aceita POST vindos do próprio site.
- Os formulários que enviam emails têm limites por endereço IP (`app/lib/limites.php`): registo e contacto, 5 por hora; códigos de entrada, 10 em 15 minutos. O IP não fica guardado, só um código derivado dele, apagado ao fim de 24 horas. O registo e o contacto têm também um campo-armadilha para robôs.

## Instalação no cPanel (Dominios.pt)

1. **Site antigo**: se o `public_html` já tiver outro site, fazer cópia de segurança e esvaziá-lo antes do primeiro Deploy (os ficheiros antigos não são apagados pelo Deploy).
2. **PHP**: em MultiPHP Manager, PHP 8.1 ou mais recente para o domínio.
3. **Base de dados**: em MySQL Database Wizard, criar a base de dados e um utilizador com todas as permissões. O cPanel junta o nome da conta como prefixo (por exemplo, `UTILIZADOR_garc`).
4. **HTTPS**: em SSL/TLS Status, confirmar que o certificado cobre `autosolutions.pt` e `www.autosolutions.pt` (correr o AutoSSL, se faltar). O `.htaccess` redireciona tudo para `https://www.autosolutions.pt`.
5. **Email**: a conta fileservice@autosolutions.pt (já criada) envia e recebe os emails do site. Confirmar SPF e DKIM em Email Deliverability.
6. **Código**: em Git Version Control, criar um repositório com o Clone URL `https://github.com/joseraulsoares-cloud/autosolutions` (público, não precisa de chave), o caminho `/home/UTILIZADOR/repositories/autosolutions` (fora de `public_html`) e o ramo `main`. Depois, em Manage → Pull or Deploy, usar "Deploy HEAD Commit". O `.cpanel.yml` copia `site/` para `public_html` e `app/` para `~/autosolutions-app`. Em alternativa, enviar as duas pastas pelo Gestor de Ficheiros.
7. **Configuração**: em `~/autosolutions-app/`, copiar `config.exemplo.php` para `config.php` e preencher: base de dados, emails de administração, remetente, pasta dos ficheiros (`/home/UTILIZADOR/autosolutions-dados/ficheiros`, criada automaticamente) e um segredo com 64 caracteres aleatórios (no Terminal do cPanel: `openssl rand -hex 32`). O `config.php` não está no repositório e o Deploy não lhe toca.
8. **Limites de envio**: `site/api/.user.ini` sobe o limite de ficheiros para 32 MB. Se o alojamento o ignorar, definir `upload_max_filesize` e `post_max_size` no MultiPHP INI Editor.
9. **Primeiro acesso**: abrir `https://www.autosolutions.pt/admin` e entrar com um dos emails de administração. As tabelas são criadas automaticamente no primeiro acesso à API.

**Atualizar o site** depois de cada alteração no `main`: em Git Version Control → Manage → Pull or Deploy, "Update from Remote" e depois "Deploy HEAD Commit". O Deploy instala sempre a versão do `main` por cima do que estiver no servidor: não misturar com envios por zip, senão o Deploy seguinte repõe a versão do `main`. A pasta `garc-conteudos` e o `config.php` não são tocados.

O `site/.htaccess` trata dos endereços sem `.html` (e sem `.php`, nas páginas Serviços, Notícias, Sobre e Termos, que leem os valores alteráveis), da página 404, do redirecionamento para `https://www.autosolutions.pt`, do endereço antigo `/precos` e dos cabeçalhos de segurança.

## Testes

Com PHP 8.1+, MariaDB ou MySQL e Python 3 (`requests`; `playwright` para o teste no browser):

1. Criar uma base de dados de teste e um `config.php` de teste com `'dev' => true` (os emails ficam na tabela `emails_dev`).
2. Arrancar o servidor: `GARC_APP=<app> GARC_CONTEUDOS=<pasta-de-conteudos-de-teste> SITE_ROOT=<site> php -d upload_max_filesize=32M -d post_max_size=40M -S 127.0.0.1:8790 -t <site> tests/router.php`.
3. Correr `GARC_TESTE_CONTEUDOS=<a mesma pasta> python3 tests/teste_api.py` e `python3 tests/teste_ui.py <pasta-de-saida>`. A pasta de conteúdos deve começar vazia (o teste confirma que é criada com os valores de origem).

