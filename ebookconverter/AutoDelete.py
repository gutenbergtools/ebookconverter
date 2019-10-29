#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

AutoDelete.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Looks for any ebooks with changed files in the last X days and then
checks if any of the known files of that ebook have been deleted.


"""

from __future__ import unicode_literals
from __future__ import print_function

import os

from six.moves import builtins
from six.moves import configparser

from libgutenberg.Logger import debug, info
from libgutenberg import Logger
from libgutenberg import GutenbergGlobals as gg
from libgutenberg import GutenbergDatabase

from ebookmaker.CommonCode import Options

from ebookconverter.EbookConverter import config

PRIVATE = os.getenv ('PRIVATE') or ''
PUBLIC  = os.getenv ('PUBLIC')  or ''

DIRS  = PUBLIC + '/dirs'

options = Options()

def check_book (ebook):
    """ Check all files of ebook for presence. """

    c  = GutenbergDatabase.DB.get_cursor ()
    c2 = GutenbergDatabase.DB.get_cursor ()

    c.execute ("select filename from files where fk_books = %(ebook)s and diskstatus != 5",
               { 'ebook': ebook })

    for row in c.fetchall ():
        row = GutenbergDatabase.xl (c, row)
        try:
            if row.filename.startswith ('/'):
                os.stat (row.filename)
                continue
            if row.filename.startswith ('cache'):
                os.stat (os.path.join (PUBLIC, row.filename))
                continue
            if row.filename.startswith ('dirs'):
                os.stat (os.path.join (PUBLIC, row.filename))
                continue
            os.stat (os.path.join (DIRS, row.filename))
        except OSError:
            c2.execute ("start transaction")
            c2.execute ("update files set diskstatus = 5 where filename = %(filename)s",
                        { 'filename': row.filename })
            c2.execute ("commit")
            info ("Removed from database: %s" % row.filename)


def main ():
    goback = 1
    try:
        config ()
    except configparser.Error as what:
        error ("Error in configuration file: %s", str (what))
        return 1

    Logger.setup (Logger.LOGFORMAT, 'autodelete.log')
    Logger.set_log_level (2)

    debug ("Starting AutoDelete.py")

    GutenbergDatabase.DB = GutenbergDatabase.Database ()
    GutenbergDatabase.DB.connect ()
    c  = GutenbergDatabase.DB.get_cursor ()

    c.execute ("select distinct fk_books from files "
               "where filemtime >= now () - interval '%(goback)s days' "
               "and filename !~ '^cache/' "
               "and diskstatus != 5 and fk_books is not null",
               { 'goback': goback } )

    for row in c.fetchall ():
        row = GutenbergDatabase.xl (c, row)
        ebook = int (row.fk_books)
        Logger.ebook = ebook
        debug ("Checking ebook")
        check_book (ebook)

    Logger.ebook = 0
    debug ("Done AutoDelete.py")


if __name__ == '__main__':
    main ()
