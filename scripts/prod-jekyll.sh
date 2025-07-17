
# runs jekyll to build ww.gutenberg.org site from master branch of gutenbergtools/gutenbergsite
# 20250430  changed jekyll invocation to be less sensitive to gemlock changes -ESH

BUILD=/public/vhost/g/gutenberg/gutenbergsite
cd ${BUILD}

## proposed update from github

git fetch origin
git checkout remotes/origin/master


# Fetch input, the latest covers:
/usr/bin/wget --quiet -O ${BUILD}/_includes/latest_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/latest/10"

# Deploy the new content:
cd ${BUILD}

# jekyll is in ${HOME}/.rvm/gems
bundle install
bundle exec jekyll build 
