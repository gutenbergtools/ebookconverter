#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

AutoDelete.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Looks for any ebooks with changed files in the last X days and then
checks if any of the known files of that ebook have been deleted.


"""

import os
import sys
from datetime import datetime, timedelta

from six.moves import builtins
from six.moves import configparser

from libgutenberg.Logger import debug, info
from libgutenberg import Logger
from libgutenberg import GutenbergGlobals as gg
from libgutenberg import GutenbergDatabase

from libgutenberg.Models import Book, File

PRIVATE = os.getenv ('PRIVATE') or ''
PUBLIC  = os.getenv ('PUBLIC')  or ''
OB = GutenbergDatabase.Objectbase(False)

DIRS  = PUBLIC + '/dirs'

def check_book (ebook):
    """ Check all files of ebook for presence. """

    session = OB.get_session()
    files = session.query(File).filter(
        File.fk_books == ebook,
        File.diskstatus != 5
    ).all()
    
    for file in files:
        try:
            if file.archive_path.startswith('/'):
                os.stat(file.archive_path)
                continue
            if file.archive_path.startswith('cache'):
                os.stat(os.path.join(PUBLIC, file.archive_path))
                continue
            if file.archive_path.startswith('dirs'):
                os.stat(os.path.join(PUBLIC, file.archive_path))
                continue
            os.stat(os.path.join(DIRS, file.archive_path))
        except OSError:
            file.diskstatus = 5 
            session.commit()
            info("Removing from database: %s" % file.archive_path)
    session.commit()


def main ():
    goback = 1
    Logger.setup (Logger.LOGFORMAT, 'autodelete.log')
    Logger.set_log_level (2)

    debug ("Starting AutoDelete.py")

        Logger.ebook = ebook
        debug ("Checking ebook")
        check_book (ebook)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                Logger.ebook = int(arg)
                if check_book (int(arg)):
                    error('No directory for {arg}')
                
            except ValueError: # no int
                error ("not an ebook number: %s", str (arg))

    else:
        session = OB.get_session()

        # 1. Define the time threshold (goback days ago)
        time_threshold = datetime.utcnow() - timedelta(days=goback)
        
        # 2. Build the select statement
        stmt = (
            select(File.fk_books)
            .distinct()
            .where(
                File.modified >= time_threshold,
                # 'archive_path !~ ^cache/' -> regex match 'not similar'
                not_(File.archive_path.op('~')('^cache/')),
                File.diskstatus != 5,
                # 'fk_books is not null'
                File.fk_books.isnot(None)
            )
        )
        booknums =  session.execute(stmt).scalars().all()    
        for ebook in booknums:

    Logger.ebook = 0
    debug ("Done AutoDelete.py")


if __name__ == '__main__':
    main ()
