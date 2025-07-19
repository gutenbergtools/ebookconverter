#!/bin/bash
#
# esh 20250717: adapted from cron-dopush and cron-rebuild-files to reindex all books 

D=$(date +"%-d")

# will reindex up to PG 77999 in a 30 day month
BOOKS_PER_DAY=2600

START=$(($D*$BOOKS_PER_DAY))
STOP=$((($D+1)*$BOOKS_PER_DAY-1))

echo "Invoking fileinfo for range $START to $STOP ..."

cd /export/sunsite/users/gutenbackend/ebookconverter


# This does the basic identification of files and metadata,
for (( i=$START; i<=$STOP; i++ )); do
  ~/.local/bin/pipenv run fileinfo $i
done
