#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
MastodonWriter.py

Copyright 2023 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Toot about new ebooks.

"""

import os
import uuid

import requests

from requests import RequestException

from libgutenberg.Logger import exception
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from libgutenberg import GutenbergDatabase

from ebookmaker import writers


URL = "https://mastodon.social/api/v1/statuses"

class Writer(writers.BaseWriter):
    """ Class to toot about new ebooks.

    """

    __instance = None

    def __new__(cls):
        """ Make Writer a singleton. """

        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance


    def __init__(self):

        super(Writer, self).__init__()

        self.access_token = os.environ.get('MASTODON_ACCESS_TOKEN')
        if not self.access_token:
            raise SkipOutputFormat ('Mastodon credentials not found.')


    def build(self, job):
        """ Toot. """

        if job.dc.project_gutenberg_id < 70800:
            # don't toot about old books
            return

        db = GutenbergDatabase.Database()
        db.connect()
        c = db.get_cursor()

        c.execute("select * from tweets where media = 'Mastodon' and fk_books = %(fk_books)s",
                   {'fk_books': job.dc.project_gutenberg_id})

        rows = c.fetchone()
        if rows:
            # already tooted
            return

        try:
            title = job.dc.make_pretty_title(500 - 84)  # 500 is max length
            headers = {'Authorization': 'Bearer %s' % self.access_token,
                       'Idempotency-Key': str(uuid.uuid4())}
            toot = "New #ebook @gutenberg_org@mastodon.social: %s https://www.gutenberg.org/ebooks/%d" % (
                title, job.dc.project_gutenberg_id)
            lang_id = job.dc.languages[0].id if len(job.dc.languages) else 'en'
            data = {'status': toot,
                    'visibility': 'public',
                    'language': lang_id}
            r = requests.post(URL, headers=headers, data=data)
            r.raise_for_status()

            c.execute('start transaction')
            c.execute(
                """\
                insert into tweets (fk_books, media, time)
                values (%(fk_books)s, 'Mastodon', now ())
                """, {'fk_books': job.dc.project_gutenberg_id})
            c.execute('commit')

        except (RequestException) as what:
            exception('MastodonWriter: could not toot about ebook: %s' % what)

        except (GutenbergDatabase.DatabaseError) as what:
            c.execute('rollback')
            exception('MastodonWriter: could not write to database (#%s)' % what)
