#!/bin/bash
#
# esh 20200902: removed invocation of the jekyll build so that can have its own cron schedule
# gbn 20200826: If this file exists, what's below will fail. Check
# for it first, and squawk if it exists:
if [ -f /tmp/ebookconverter.pid ] ; then
    echo "$0: Cannot run, because /tmp/ebookconverter.pid exists"
    /bin/ls -l /tmp/ebookconverter.pid
    exit 1
fi

# echo "cron-dopush: checking for files ..."

cd /export/sunsite/users/gutenbackend/ebookconverter

# Load environment variables:
# gbn 2020-05-07: This confuses things due to multiple Python installs
# on login2. Instead, let ~gutenbackend/.bashrc take care of this:
# esh 2021-08-24 setting environment variable in .env which gets loaded by pipenv#
#. ./.env
#export VHOST="/public/vhost/g/gutenberg"
#export PRIVATE="${VHOST}/private"
#export PUBLIC="${VHOST}/html"
#export PHP="php -c ${PRIVATE}/lib/php/"


# First check whether there are any .trig files in 
#  /public/vhost/g/gutenberg/private/logs/dopush/
LIST=`/bin/ls -1 /public/vhost/g/gutenberg/private/logs/dopush/ | grep .trig | sed 's/\.zip.trig//'`

# No .trig files? Exit:
if [ "${LIST}x" = x ] ; then
#   echo DEBUG: empty list is $LIST .. exiting
    exit 0
fi

# echo DEBUG: non-empty list is $LIST 
# exit 0

# This does the basic identification of files and metadata,
# extracted from the .zip files identified by the .trig files:
~/.local/bin/pipenv --bare run fileinfo

# We have work to do! 
# echo "do_push: making files ..."

~/.local/bin/pipenv run autodelete

# echo "ran autodelete"

# gbn 2020-04-03: "goback-24" runs the last 24 hours. Instead, we
# will expicitly rebuild every item in the LIST:
# ~/.local/bin/pipenv run ebookconverter -v --range=1- --goback=24 --build=all
for i in ${LIST}; do
    ~/.local/bin/pipenv run ebookconverter -v --range=${i} --build=all --validate --notify
done

~/.local/bin/pipenv run autorebuild
