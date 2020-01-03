#!/bin/bash
#

D=$(date +"%-d")

BOOKS_PER_DAY=100

START=$((($D-1)*$BOOKS_PER_DAY))
STOP=$(($D*$BOOKS_PER_DAY-1))

echo "Invoking ebookconverter for range $START to $STOP ..."

cd /export/sunsite/users/gutenbackend/ebookconverter
~/.local/bin/pipenv run ebookconverter -v -v --range=$START-$STOP --build=all --jobs=50 --pidfile=/tmp/test-pg-cron-rebuild.pid --shadow
