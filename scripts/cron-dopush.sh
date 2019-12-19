#!/bin/bash
#

# echo "cron-dopush: checking for files ..."

cd /export/sunsite/users/gutenbackend/ebookconverter

# Load environment variables:
. ./.env

# First check whether there are any .trig files in 
#  /public/vhost/g/gutenberg/private/logs/dopush/
~/.local/bin/pipenv --bare run fileinfo | ${PHP} ${PRIVATE}/lib/python/autocat/autocat.php || exit 1

# We have work to do! 
echo "do_push: making files ..."

~/.local/bin/pipenv run autodelete

echo "ran autodelete"

~/.local/bin/pipenv run ebookconverter -v --range=1- --goback=24 --make=all

echo "ran ebookconverter"

exit
sleep 300

wget -O ${PUBLIC}/cache/latest-covers.html.utf8 "http://gutenberg2:8000/covers/small/latest/10"
gzip -c ${PUBLIC}/cache/latest-covers.html.utf8 > $PUBLIC/cache/latest-covers.html.utf8.gzip
