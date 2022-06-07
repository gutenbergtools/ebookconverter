#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

ReloadWorkflow.py

arguments: a list of ebook numbers

Copyright 2022 by Eric Hellman and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

looks for the newest workflow json file, and reloads the data into the database, overwriting whatever is there. Use with caution!!

"""
import os
import sys

from libgutenberg import Logger
from libgutenberg.DublinCoreMapping import DublinCoreObject
from .FileInfo import get_workflow_file, WORKFLOW_LOG_DIR

def get_newest_workflow_file(ebook):
    current = get_workflow_file(ebook)
    if current:
        return current
    for rev in reversed(range(0,10)):
        archived = os.path.join(WORKFLOW_LOG_DIR, 'backup', '%s.json.%s' % (ebook, rev))
        if os.path.exists(archived):
            return archived
    archived = os.path.join(WORKFLOW_LOG_DIR, 'backup', '%s.json' % ebook)
    if os.path.exists(archived):
        return archived

def reload_workflow_file(ebook):
    workflow_file = get_newest_workflow_file(ebook)
    if not workflow_file:
        print(f'No workflow file for {ebook}')
        return
    dc = DublinCoreObject()
    dc.load_book(ebook)
    with open(workflow_file, 'r') as fp:
        data = fp.read()
    try:
        dc.load_from_pgheader(data)
    except ValueError:
        print(f'Tried {workflow_file}; was it a valid workflow file?')
        Logger.error("Tried %s; was it a valid workflow file?", workflow_file)
        return
    dc.save(updatemode=1)


def main():
    Logger.setup(Logger.LOGFORMAT, 'fileinfo.log')
    Logger.set_log_level(2)

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                Logger.ebook = int(arg)
                print(f'loading metadata for {arg}')
                reload_workflow_file(int(arg))
            except ValueError: # no int
                print('need a book number to load')

    else:
        print('need a book number to load')

if __name__ == '__main__':
    main()
