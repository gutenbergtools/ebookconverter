#!/bin/bash
#
# Gets the latest covers (pulls updates from gutenbergsite repo -- maybe) and rebuild the jekyll part of the site.
#####
# Changelog
# 20200429 - initial version (hely)
# 20200529 - fix issue with incomplete output (gbnewby)
# 20200902 - copied from cron-latesttitles.sh and ripped out code (eshellman)
# 20200904 - use 'medium' rather than 'small' cover images (gbn)
# 20240717 - run only if there are new images (gbn)
#

# Where to build (we might need to have multiple dev v. production locations
# in the future)
BUILD=/public/vhost/g/gutenberg/gutenbergsite
cd ${BUILD}

## proposed update from github

# git pull

OLDSUM=`/usr/bin/sum ${BUILD}/_includes/latest_covers.html | /usr/bin/cut -f1 -d" "`

# Fetch input, the latest covers:
# /usr/bin/wget --quiet -O ${BUILD}/_includes/latest_covers.html "http://gutenberg-app1:8000/covers/medium/latest/10"
# This is going to appdev:
/usr/bin/wget --quiet -O ${BUILD}/_includes/latest_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/latest/10"

# Are the covers different than previously?
NEWSUM=`/usr/bin/sum ${BUILD}/_includes/latest_covers.html | /usr/bin/cut -f1 -d" "`

if [ ${OLDSUM} = ${NEWSUM} ] ; then
    exit 0
fi

# This deploys the new content. Any errors will be returned; otherwise
# output is quelled:
[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" 

# Deploy the new content:
cd ${BUILD}

# jekyll is in ${HOME}/.rvm/gems
jekyll build > /dev/null

# was only need because cron-latesttitles.sh was called from another script, I think -eshellman
#exit
