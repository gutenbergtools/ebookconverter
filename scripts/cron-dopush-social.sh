#!/bin/bash
# 20201217 changed goback to 6, not 24 esh
cd /export/sunsite/users/gutenbackend/ebookconverter
~/.local/bin/pipenv run ebookconverter -v -v --range=1- --goback=6 --build=facebook --build=bluesky --build=mastodon

