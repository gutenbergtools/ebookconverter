#!/bin/bash
#

grep 'Missing file' ebookconverter.log > missingfiles.txt
grep 'Failed' ebookconverter.log > conversionfails.txt