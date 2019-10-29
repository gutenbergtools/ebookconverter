#!/bin/bash
#

# echo "cron-dopush: checking for files ..."

cd /export/sunsite/users/gutenbackend/ebookconverter
~/.local/bin/pipenv shell


fileinfo | ${PHP} ${PRIVATE}/lib/python/autocat/autocat.php || exit 1

echo "do_push: making files ..."

autodelete

ebookconverter -v --range=1- --goback=24 --make=all

exit
sleep 300

wget -O ${PUBLIC}/cache/latest-covers.html.utf8 "http://gutenberg2:8000/covers/small/latest/10"
gzip -c ${PUBLIC}/cache/latest-covers.html.utf8 > $PUBLIC/cache/latest-covers.html.utf8.gzip
