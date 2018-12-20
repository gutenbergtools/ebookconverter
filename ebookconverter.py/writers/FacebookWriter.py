#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
FacebookWriter.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Cackle about new ebooks.
"""


import os

import requests

from libgutenberg import GutenbergDatabase
from libgutenberg.Logger import exception, error, info, debug
from libgutenberg.GutenbergGlobals import SkipOutputFormat

from ebookmaker import writers

PGURL = "https://www.gutenberg.org/"

GRAPH = "https://graph.facebook.com/v2.8/"

class Writer (writers.BaseWriter):
    """ Class to post about new ebooks.

    """

    __instance = None

    def __new__ (cls):
        """ Make Writer a singleton. """

        if cls.__instance is None:
            cls.__instance = object.__new__ (cls)
        return cls.__instance


    def __init__ (self):
        # already initialized
        if hasattr (self, 'access_token'):
            return

        super (Writer, self).__init__ ()

        self.page_id = '171646249561837' # New Project Gutenberg Books Page
        self.access_token = os.environ.get ('FB_ACCESS_TOKEN')

        if not self.access_token:
            raise SkipOutputFormat ('Facebook credentials not found.')


    def build (self, job):
        """ Post. """

        if job.dc.project_gutenberg_id < 45000:
            # don't post about old books
            return

        db = GutenbergDatabase.Database ()
        db.connect ()
        c = db.get_cursor ()

        c.execute ("select * from tweets where media = 'Facebook' and fk_books = %(fk_books)s",
                   { 'fk_books': job.dc.project_gutenberg_id })

        rows = c.fetchone ()
        if rows:
            # already posted
            return

        try:
            id_ = job.dc.project_gutenberg_id
            data = {
                'link': PGURL + "ebooks/%d" % id_,
                'picture': PGURL + "cache/epub/%d/pg%d.cover.medium.jpg" % (id_, id_),
                'name': job.dc.make_pretty_title (200),
                'caption': "",
                'description': "This is a free ebook by Project Gutenberg.",
                'access_token': self.access_token,
                }

            fp = requests.post (
                "%s%s/feed" % (GRAPH, self.page_id),
                data = data,
                timeout = 60
            )
            if fp.status_code == 200:
                c.execute ('start transaction')
                c.execute ("insert into tweets (fk_books, media, time) values (%(fk_books)s, 'Facebook', now ())",
                           { 'fk_books': job.dc.project_gutenberg_id })
                c.execute ('commit')
                info ("FacebookWriter: posted ebook: %d" % id_)
            else:
                error ("Facebook returned HTTP code %d (%s)" % (fp.status_code, fp.text))

        except GutenbergDatabase.DatabaseError as what:
            c.execute ('rollback')
            exception ('FacebookWriter: could not post ebook: %s' % (what))
