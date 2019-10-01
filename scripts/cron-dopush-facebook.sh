#!/bin/bash
#
cd /export/sunsite/users/gutenbackend/ebookconverter
~/.local/bin/pipenv run ebookconverter -v -v --range=1- --goback=24 --build=facebook
