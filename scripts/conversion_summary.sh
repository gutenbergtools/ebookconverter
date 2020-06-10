#!/bin/bash
#

grep 'Missing file' ebookconverter.log > missingfiles.txt
grep 'Failed' ebookconverter.log > conversionfails.txt
grep -C1 "kindlegen: E" ebookconverter.log > kindlegen.txt
grep 'Omitted file' ebookconverter.log | sort --unique > too_deep.txt