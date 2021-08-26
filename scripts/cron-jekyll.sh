#!/bin/bash
#
# Gets the latest covers (pulls updates from gutenbergsite repo -- maybe) and rebuild the jekyll part of the site.
#####
# Changelog
# 20200429 - initial version (hely)
# 20200529 - fix issue with incomplete output (gbnewby)
# 20200902 - copied from cron-latesttitles.sh and ripped out code (eshellman)
# 20200904 - use 'medium' rather than 'small' cover images (gbn)
#

# Where to build (we might need to have multiple dev v. production locations
# in the future)
BUILD=/public/vhost/g/gutenberg/gutenbergsite
cd ${BUILD}

## proposed update from github

# git pull


# Fetch input, the latest covers:
wget -O ${BUILD}/_includes/latest_covers.html "http://gutenberg1:8000/covers/medium/latest/10"


# This deploys the new content. Any errors will be returned; otherwise
# output is quelled:
[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" 

# Deploy the new content:
cd ${BUILD}
jekyll build > /dev/null

# was only need because cron-latesttitles.sh was called from another script, I think -eshellman
#exit
