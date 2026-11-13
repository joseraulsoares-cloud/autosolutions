#!/bin/bash
# Publica o site no alojamento. Corrido pelo "Deploy HEAD Commit" do Git Version Control do cPanel
# (.cpanel.yml), a partir da raiz do repositório:
#   site/ -> ~/public_html        app/ -> ~/autosolutions-app
# Em ~/garc-conteudos só esconde as notícias retiradas do site (NOTICIAS_RETIRADAS, mais abaixo);
# não toca no dados.txt, nas outras notícias nem no config.php da aplicação.
set -u
umask 022
DESTINO="$HOME/public_html"
APP="$HOME/autosolutions-app"
mkdir -p "$DESTINO" "$APP" || exit 1

# O cPanel escreve no .htaccess de public_html os blocos da versão do PHP (MultiPHP Manager) e das
# diretivas do PHP (MultiPHP INI Editor). O .htaccess do site substitui o anterior: estes blocos são
# guardados antes e repostos no fim, para o domínio continuar com a versão do PHP escolhida.
BLOCOS=""
if [ -f "$DESTINO/.htaccess" ]; then
  BLOCOS=$(sed -n '/BEGIN cPanel-generated/,/END cPanel-generated/p' "$DESTINO/.htaccess")
fi

cp -R site/. "$DESTINO/" || exit 1
cp -R app/. "$APP/" || exit 1

if [ -n "$BLOCOS" ]; then
  if ! grep -q 'BEGIN cPanel-generated' "$DESTINO/.htaccess"; then
    printf '\n%s\n' "$BLOCOS" >> "$DESTINO/.htaccess"
  fi
fi

# Notícias retiradas do site que já estavam no servidor: ficam escondidas com _ à frente do nome
# (as começadas por _ não aparecem), para o texto não se perder. Retirar uma notícia de
# app/conteudos-iniciais não chega, porque o servidor guarda a sua própria cópia.
NOTICIAS="$HOME/garc-conteudos/noticias"
NOTICIAS_RETIRADAS=(como-preparar-uma-leitura.txt)
for n in "${NOTICIAS_RETIRADAS[@]}"; do
  if [ -f "$NOTICIAS/$n" ]; then
    if [ -e "$NOTICIAS/_$n" ]; then rm -f "$NOTICIAS/$n"; else mv "$NOTICIAS/$n" "$NOTICIAS/_$n"; fi
  fi
done

# Alguns alojamentos recusam correr PHP em ficheiros ou pastas com escrita para o grupo ou para
# outros (erro 500). Tira-se essa permissão a tudo o que está dentro de public_html e da aplicação.
find "$DESTINO" -mindepth 1 -perm /022 -exec chmod go-w {} + 2>/dev/null
find "$APP" -perm /022 -exec chmod go-w {} + 2>/dev/null
exit 0
