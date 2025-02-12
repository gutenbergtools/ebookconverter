#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""
AutoRebuild.py

Copyright 2025 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Looks for any ebooks with significant changed metadata in the last X hours and then
rebuilds the book.
"""

import os
import re
import subprocess

from libgutenberg.Logger import debug, info
from libgutenberg import Logger
from libgutenberg import GutenbergDatabase

from ebookmaker.CommonCode import Options

from ebookconverter.EbookConverter import config

PRIVATE = os.getenv('PRIVATE') or ''
PUBLIC = os.getenv('PUBLIC') or ''

DIRS = PUBLIC + '/dirs'

options = Options()

RE_AUTHOR_BOOK = re.compile(r'fk_books = (\d\d+)')
RE_BOOK_ADD_AUTHOR = re.compile(r'values \((\d\d+),')
RE_TITLE_ATTRIBS = re.compile(r'where pk = (\d\d+)')

def get_book_for_attrib(attrib):
    c = GutenbergDatabase.DB.get_cursor()

    c.execute("select fk_books from public.attributes where pk = %(attrib)s",
               {'attrib': attrib})

    for row in c.fetchall():
        row = GutenbergDatabase.xl(c, row)
        return row.fk_books

def check_sql(sql):
    """ return an ebook number needing rebuild """
    if sql.startswith('update mn_books_authors ') \
            or sql.startswith('delete from mn_books_authors '):
        # change or delete in author
        match = RE_AUTHOR_BOOK.search(sql)
        if match:
            return match.group(1)

    elif sql.startswith('insert into mn_books_authors (fk_books,'):
        # add author
        match = RE_BOOK_ADD_AUTHOR.search(sql)
        if match:
            return match.group(1)
    
    elif sql.startswith('update attributes set  "fk_attriblist" = 245'):
        # change in title
        match = RE_TITLE_ATTRIBS.search(sql)
        attrib = match.group(1)
        return get_book_for_attrib(attrib)
    return None
        
        


def main():
    goback = 1
    try:
        config()
    except configparser.Error as what:
        error("Error in configuration file: %s", str(what))
        return 1

    Logger.setup(Logger.LOGFORMAT, 'autorebuild.log')
    Logger.set_log_level(2)

    debug("Starting AutoRebuild.py")

    GutenbergDatabase.DB = GutenbergDatabase.Database()
    GutenbergDatabase.DB.connect()
    c  = GutenbergDatabase.DB.get_cursor()

    c.execute("select sql from public.changelog "
               "where time >= now () - interval '%(goback)s hours' ", {'goback': goback})

    to_rebuild = set()
    for row in c.fetchall():
        row = GutenbergDatabase.xl(c, row)
        to_rebuild.add(check_sql(row.sql))
    buildlist = ''
    for ebook in to_rebuild:
        buildlist = f'{buildlist}{ebook},' if ebook else buildlist
    buildlist = buildlist.strip(',')
    if buildlist:
        info(f'rebuilding {buildlist}')
        subprocess.call(["ebookconverter", "-v", "--build=all", "--range=%s" % buildlist])        
    Logger.ebook = 0
    debug("Done AutoRebuild.py")


if __name__ == '__main__':
    main()
