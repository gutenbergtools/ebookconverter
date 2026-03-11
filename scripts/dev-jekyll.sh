# runs jekyll to build dev.gutenberg.org site from dev branch of gutenbergtools/gutenbergsite
# 20250430  changed jekyll invocation to be less sensitive to gemlock changes -ESH
# 20250728 added popular covers -ESH

BUILD=/public/vhost/g/gutenberg/gutenbergdev
cd ${BUILD}

## proposed update from github

git fetch origin
git checkout remotes/origin/dev


# Fetch input, the latest covers:
/usr/bin/wget --quiet -O ${BUILD}/_includes/latest_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/latest/10"

# Fetch input, the popular covers:
/usr/bin/wget --quiet -O ${BUILD}/_includes/popular_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/popular/10"


# This deploys the new content. Any errors will be returned; otherwise
# output is quelled:
# I think this is not needed if ruby version is set properly  and jekyll in invoked with bundle - ESH 2025-05-20
#[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" 

# Deploy the new content:
cd ${BUILD}

# jekyll is in ${HOME}/.rvm/gems
bundle install
bundle exec jekyll build --config _config_dev.yml
