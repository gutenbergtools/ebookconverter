#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
TwitterWriter.py

Copyright 2010,2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Cackle about new ebooks.

"""

from __future__ import unicode_literals

import os

import requests_oauthlib

from requests import RequestException
from oauthlib.oauth1.rfc5849.errors import OAuth1Error

from libgutenberg.Logger import exception
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from libgutenberg import GutenbergDatabase

from ebookmaker import writers


URL = "https://api.twitter.com/1.1/statuses/update.json"

class Writer (writers.BaseWriter):
    """ Class to cackle about new ebooks.

    """

    __instance = None

    def __new__ (cls):
        """ Make Writer a singleton. """

        if cls.__instance is None:
            cls.__instance = object.__new__ (cls)
        return cls.__instance


    def __init__ (self):
        if hasattr (self, 'session'):
            # already initialized
            return

        super (Writer, self).__init__ ()

        get = os.environ.get

        if not get ('TWITTER_API_SECRET'):
            raise SkipOutputFormat ('Twitter credentials not found.')

        self.session = requests_oauthlib.OAuth1Session (
            get ('TWITTER_API_KEY'),
            client_secret = get ('TWITTER_API_SECRET'),
            resource_owner_key = get ('TWITTER_ACCESS_TOKEN'),
            resource_owner_secret = get ('TWITTER_ACCESS_TOKEN_SECRET')
        )


    def build (self, job):
        """ Cackle. """

        if job.dc.project_gutenberg_id < 45400:
            # don't cackle about old books
            return

        db = GutenbergDatabase.Database ()
        db.connect ()
        c = db.get_cursor ()

        c.execute ("select * from tweets where media = 'Twitter' and fk_books = %(fk_books)s",
                   { 'fk_books': job.dc.project_gutenberg_id })

        rows = c.fetchone ()
        if rows:
            # already cackled
            return

        try:
            title = job.dc.make_pretty_title (74)
            tweet = "New #ebook @gutenberg_org: %s https://www.gutenberg.org/ebooks/%d" % (
                title, job.dc.project_gutenberg_id)

            r = self.session.post (URL, data = { 'status': tweet })
            r.raise_for_status ()

            c.execute ('start transaction')
            c.execute (
                """\
                insert into tweets (fk_books, media, time)
                values (%(fk_books)s, 'Twitter', now ())
                """,
                       { 'fk_books': job.dc.project_gutenberg_id })
            c.execute ('commit')

        except (RequestException, OAuth1Error) as what:
            exception ('TwitterWriter: could not cackle about ebook: %s' % what)

        except (GutenbergDatabase.DatabaseError) as what:
            c.execute ('rollback')
            exception ('TwitterWriter: could not write to database (#%s)' % what)
