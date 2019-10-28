#!/bin/bash
#

# echo "cron-dopush: checking for files ..."

cd /public/vhost/g/gutenberg/private/bin
. ./env

cd $PRIVATE/lib/python/autocat/

# this pulls from pglaf.org and writes trigger files 
# for changed files just like dopush does

# ./HgPull.py

# returns 0 if files processed, else 1
# bail out if no files processed

./FileInfo.py | $PHP autocat.php || exit 1

echo "do_push: making files ..."

./AutoDelete.py

cd ..

$LOCAL/bin/ebookconverter -v --range=1- --goback=24 --make=all

sleep 300

$LOCAL/bin/ebookconverter -v -v --range=1- --goback=24 --build=facebook --build=twitter
wget -O $PUBLIC/cache/latest-covers.html.utf8 "http://gutenberg2:8000/covers/small/latest/10"
gzip -c $PUBLIC/cache/latest-covers.html.utf8 > $PUBLIC/cache/latest-covers.html.utf8.gzip
