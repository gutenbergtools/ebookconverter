#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
BlueskyWriter.py

Copyright 2025 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Skeet about new ebooks.

"""

import os
from datetime import datetime, timezone

import requests

from requests import RequestException

from libgutenberg.Logger import exception
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from libgutenberg import GutenbergDatabase

from ebookmaker import writers


URL = 'https://bsky.social/xrpc/com.atproto.server.createSession'
HANDLE = 'new.gutenberg.org'
SKEETURL = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
APP_PASSWORD = os.environ.get('BLUESKY_APP_PASSWORD')

class Writer(writers.BaseWriter):
    """ Class to skeet about new ebooks.

    """

    __instance = None
    __session = None

    def __new__(cls):
        """ Make Writer a singleton. """

        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance


    def __init__(self):

        super(Writer, self).__init__()

        
        if not APP_PASSWORD:
            raise SkipOutputFormat ('Bluesky credentials not found.')
            
    def get_session(cls):
        if cls.__session:
            return __session
        
        resp = requests.post(URL, json={'identifier': HANDLE, 'password': APP_PASSWORD})
        resp.raise_for_status()
        cls.__session = resp.json()
        return cls.__session


    def build(self, job):
        """ Skeet. """

        if job.dc.project_gutenberg_id < 74866:
            # don't skeet about old books
            return

        db = GutenbergDatabase.Database()
        db.connect()
        c = db.get_cursor()

        c.execute("select * from tweets where media = 'Bluesky' and fk_books = %(fk_books)s",
                   {'fk_books': job.dc.project_gutenberg_id})

        rows = c.fetchone()
        if rows:
            # already skeeted
            return

        try:
            session = self.get_session()
            title = job.dc.make_pretty_title(300 - 84)  # 300 is max length
            {"Authorization": "Bearer " + session["accessJwt"]}
            headers = {'Authorization': 'Bearer ' + session["accessJwt"]}
            skeet = "New #ebook @new.gutenberg.org: %s https://www.gutenberg.org/ebooks/%d" % (
                title, job.dc.project_gutenberg_id)
            lang_id = job.dc.languages[0].id if len(job.dc.languages) else 'en'
            post = {"$type": "app.bsky.feed.post",
                    "text": skeet,
                    "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "langs": [lang_id]
                    }
            data = {"repo": session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": post,
                    }

            r = requests.post(SKEETURL, headers=headers, json=data)
            r.raise_for_status()

            c.execute('start transaction')
            c.execute(
                """\
                insert into tweets (fk_books, media, time)
                values (%(fk_books)s, 'Bluesky', now ())
                """, {'fk_books': job.dc.project_gutenberg_id})
            c.execute('commit')

        except (RequestException) as what:
            exception('BlueskyWriter: could not skeet about ebook: %s' % what)

        except (GutenbergDatabase.DatabaseError) as what:
            c.execute('rollback')
            exception('BlueskyWriter: could not write to database (#%s)' % what)
