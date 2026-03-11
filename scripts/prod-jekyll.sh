# runs jekyll to build www.gutenberg.org site from master branch of gutenbergtools/gutenbergsite
# 20250430  changed jekyll invocation to be less sensitive to gemlock changes -ESH

BUILD=/public/vhost/g/gutenberg/gutenbergsite
cd ${BUILD}

## proposed update from github

git fetch origin
git checkout remotes/origin/master


# Fetch input, the latest covers:
/usr/bin/wget --quiet -O ${BUILD}/_includes/latest_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/latest/10"
# Fetch input, the popular covers:
/usr/bin/wget --quiet -O ${BUILD}/_includes/popular_covers.html "http://[2610:28:3090:3001:0:dead:cafe:100]:8000/covers/medium/popular/10"



# This deploys the new content. Any errors will be returned; otherwise
# output is quelled:
#[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" 

# Deploy the new content:
cd ${BUILD}

# jekyll is in ${HOME}/.rvm/gems
bundle install
bundle exec jekyll build --config _config.yml > /dev/null
