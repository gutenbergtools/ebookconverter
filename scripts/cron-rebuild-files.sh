#!/bin/bash
#

D=$(date +"%-d")

# will rebuild up to PG 65100 in a 31 day month
BOOKS_PER_DAY=2100

START=$((($D-1)*$BOOKS_PER_DAY))
STOP=$(($D*$BOOKS_PER_DAY-1)) 

echo "Invoking ebookconverter for range $START to $STOP ..."

cd /export/sunsite/users/gutenbackend/ebookconverter
~/.local/bin/pipenv run ebookconverter -v -v --range=$START-$STOP --build=all --jobs=50 --pidfile=/tmp/pg-cron-rebuild.pid
