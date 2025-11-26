#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

Puller.py

Copyright 2025 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Use git to pull files from an upstream repo into the corresponding folder in the FILES directory

- Puller.py looks for files named [number].zip.trig in the dopull "log" directory. If it finds
  one, it uses utils.gitpull to sync the repo with the FILES/[number] directory.
- When finished, the .trig files are moved to the dopush "log" directory (triggering FileInfo.py so
  that it can index and process the files, as if pglaf-dopush (same triggering as present))

"""
import os
import re
import shutil
import stat
import sys

from libgutenberg import Logger
from libgutenberg.GutenbergFiles import FILES
from libgutenberg.Logger import error

from utils.gitpull import update_folder

PRIVATE = os.getenv('PRIVATE') or ''
UPSTREAM_REPO_DIR = os.getenv('UPSTREAM_REPO_DIR') or 'https://r.pglaf.org/git/'

DOPULL_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopull')
DOPUSH_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopush')


def scan_dopull_log():
    """ 
    Scan the dopull log directory for new files.
    """

    retcode = 1

    for filename in sorted(os.listdir(DOPULL_LOG_DIR)):
        mode = os.stat(os.path.join(DOPULL_LOG_DIR, filename))[stat.ST_MODE]
        # skip directories JIC
        if stat.S_ISDIR(mode):
            continue

        ebook_num = 0
        m = re.match(r'^(\d+)\.zip\.trig$', filename)
        if m:
            ebook_num = int(m.group(1))
            Logger.ebook = ebook_num
            print(ebook_num)
            origin = f'{UPSTREAM_REPO_DIR}{ebook_num}.git/'
            target_path = os.path.join(FILES, str(ebook_num))
            print(origin,target_path)
            if update_folder(origin, target_path):
                shutil.move(os.path.join(DOPULL_LOG_DIR, filename),
                             os.path.join(DOPUSH_LOG_DIR, filename))
                retcode = 0            
            else:
                error(f'failed to update {ebook_num}')
    return retcode

def main():
    Logger.setup(Logger.LOGFORMAT, 'puller.log')
    Logger.set_log_level(2)

    sys.exit(scan_dopull_log())

if __name__ == '__main__':
    main()
