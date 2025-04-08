#
# pulls gutenbergsite repo, copies website assets to server directory
#
#####
# Changelog
# 20250404 - initial version (eric)

cd /public/vhost/g/gutenberg/gutenbergsite/
git fetch origin
git checkout remotes/origin/master

cp -p /public/vhost/g/gutenberg/gutenbergsite/gutenberg/* /public/vhost/g/gutenberg/html/gutenberg