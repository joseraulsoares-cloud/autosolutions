#!/bin/bash
# Publica o site no alojamento. Corrido pelo "Deploy HEAD Commit" do Git Version Control do cPanel
# (.cpanel.yml), a partir da raiz do repositório:
#   site/ -> ~/public_html        app/ -> ~/autosolutions-app
# Não toca em ~/garc-conteudos (dados.txt e notícias) nem no config.php da aplicação.
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

# Alguns alojamentos recusam correr PHP em ficheiros ou pastas com escrita para o grupo ou para
# outros (erro 500). Tira-se essa permissão a tudo o que está dentro de public_html e da aplicação.
find "$DESTINO" -mindepth 1 -perm /022 -exec chmod go-w {} + 2>/dev/null
find "$APP" -perm /022 -exec chmod go-w {} + 2>/dev/null
exit 0
