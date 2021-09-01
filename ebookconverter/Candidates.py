#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

Candidates.py

Copyright 2009-2021 by Marcello Perathoner and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Utility class to find candidate files for conversion operations.

"""

import os.path
import fnmatch

from libgutenberg import GutenbergDatabase
from libgutenberg import GutenbergGlobals as gg
from libgutenberg.Logger import info, debug, warning, error, exception
from libgutenberg.Models import File

ob = GutenbergDatabase.Objectbase(False)

class Candidates (object):
    """ Class to get build candidates from the PG database.

    """

    def read_from_database (self, ebook):
        """ Read candidates from PG database. """

        candidates = []
        session = ob.get_session()
        files = session.query(File).filter(
            File.fk_books == ebook,
            File.compression == 'none',
            File.diskstatus == 0,
            File.obsoleted == 0
        ).order_by(File.fk_filetypes, File.fk_encodings, File.modified.desc())

        for file_ in files:
            if (ebook > 10000 and file_.file_type == 'html'
                and not os.path.basename (file_.archive_path).startswith (str (ebook))):
                # must have the form 12345-h.htm (not eg. glossary.htm)
                continue
            if file_.file_type is None:
                continue

            adir = gg.archive_dir (ebook)
            if file_.archive_path.startswith (adir):
                file_.archive_path = file_.archive_path.replace (adir, 'files/%d' % ebook)
            elif file_.archive_path.startswith ('etext'):
                file_.archive_path = 'dirs/' + file_.archive_path

            file_.format = "%s/%s" % (file_.fk_filetypes, file_.encoding or 'unknown')
            candidates.append (file_)

        return candidates


    @staticmethod
    def filter_sort (typeglob_list, candidates, f):
        """ Filter and sort a list of candidates into preference order.

        typeglob_list is a list in the form:
          ('html/utf-8', 'html/iso-8859-*', 'html/*', '*/*')
        where the first entry is the preferred format.

        f (candidate) extracts type from candidate

        example: f = lambda x: x.format if not x.generated else 'skip_this'

        """

        result = []

        for typeglob in typeglob_list:
            for candidate in candidates:
                if fnmatch.fnmatch (f (candidate), typeglob):
                    if candidate not in result:
                        result.append (candidate)
                        info (candidate)

        return result
