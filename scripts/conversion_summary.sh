#!/bin/bash
#

grep 'CRITICAL' ebookconverter.log > critical.log
grep 'ERROR' ebookconverter.log > error.log
grep 'Failed' ebookconverter.log > conversionfails.txt
grep "This is an ERROR for white-washed files" -C2 ebookconverter.log > headfoot.log
