#!/bin/bash
#

D=$(date +"%-d")

BOOKS_PER_DAY=2100

START=$((($D-1)*$BOOKS_PER_DAY))
STOP=$(($D*$BOOKS_PER_DAY-1)) 

echo "Invoking ebookconverter for range $START to $STOP ..."

ebookconverter -v -v --range=$START-$STOP --build=all --jobs=50 --pidfile=/tmp/pg-cron-rebuild.pid