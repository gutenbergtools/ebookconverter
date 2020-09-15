
export PUBLIC="${VHOST}/html"
export PHP="php -c ${PRIVATE}/lib/php/"


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
~/.local/bin/pipenv --bare run fileinfo | ${PHP} ${PRIVATE}/lib/python/autocat/autocat.php || exit 1

# We have work to do! 
# echo "do_push: making files ..."

~/.local/bin/pipenv run autodelete

# echo "ran autodelete"

# gbn 2020-04-03: "goback-24" runs the last 24 hours. Instead, we
# will expicitly rebuild every item in the LIST:
# ~/.local/bin/pipenv run ebookconverter -v --range=1- --goback=24 --make=all
for i in ${LIST}; do
    ~/.local/bin/pipenv run ebookconverter -v --range=${i} --build=all
done



#hely 2020-04-29: This pushes the latest book covers to the jekyll site generator
./cron-latesttitles.sh