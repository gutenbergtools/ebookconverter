#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

Candidates.py

Copyright 2009-2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Utility class to find candidate files for conversion operations.

"""

import os.path
import fnmatch

from libgutenberg import GutenbergDatabase
from libgutenberg import GutenbergGlobals as gg


class Candidates (object):
    """ Class to get build candidates from the PG database.

    """

    def read_from_database (self, ebook):
        """ Read candidates from PG database. """

        candidates = []

        c = GutenbergDatabase.DB.get_cursor ()

        c.execute ("""
select filename, fk_encodings as encoding, fk_filetypes as type, filemtime as mtime, filesize as size, mediatype, generated
from files
  left join filetypes on (files.fk_filetypes = filetypes.pk)
where fk_books = %(ebook)s
  and fk_compressions = 'none'
  and diskstatus = 0
  and obsoleted = 0
order by fk_filetypes, fk_encodings, filemtime DESC""", {'ebook': ebook} )

        for row in c.fetchall ():
            file_ = GutenbergDatabase.xl (c, row)

            if (ebook > 10000 and file_.type == 'html'
                and not os.path.basename (file_.filename).startswith (str (ebook))):
                # must have the form 12345-h.htm (not eg. glossary.htm)
                continue

            adir = gg.archive_dir (ebook)
            if file_.filename.startswith (adir):
                file_.filename = file_.filename.replace (adir, 'files/%d' % ebook)
            elif file_.filename.startswith ('etext'):
                file_.filename = 'dirs/' + file_.filename

            file_.format = "%s/%s" % (file_.type, file_.encoding or 'unknown')

            file_.mediatype = str (gg.DCIMT (file_.mediatype, file_.encoding))

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

        return result
