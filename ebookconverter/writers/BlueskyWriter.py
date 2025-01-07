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

from libgutenberg.Logger import error, exception
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from libgutenberg import GutenbergDatabase

from ebookmaker import writers
from ..EbookConverter import make_output_filename


URL = 'https://bsky.social/xrpc/com.atproto.server.createSession'
SKEETURL = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
BLOBURL = "https://bsky.social/xrpc/com.atproto.repo.uploadBlob"

HANDLE = 'new.gutenberg.org'
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
            return cls.__session
        
        resp = requests.post(URL, json={'identifier': HANDLE, 'password': APP_PASSWORD})
        resp.raise_for_status()
        cls.__session = resp.json()
        return cls.__session

    def get_blob(self, img_path):
        """ get cover image, post it to get a blob identifier """

        session = self.get_session()
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        
        # this size limit is specified in the app.bsky.embed.images lexicon
        if len(img_bytes) > 1000000:
            raise Exception(
                f"image file size too large. 1000000 bytes maximum, got: {len(img_bytes)}"
            )
        
        resp = requests.post(BLOBURL,
            headers={
                "Content-Type": "image/jpeg",
                "Authorization": "Bearer " + session["accessJwt"],
            },
            data=img_bytes,
        )
        resp.raise_for_status()
        return resp.json()["blob"]

    def build(self, job):
        """ Skeet. """
        
        pg_id = job.dc.project_gutenberg_id
        coverfile = make_output_filename('cover.medium', pg_id)
        coverpath = os.path.join(job.outputdir, coverfile)

        if pg_id < 75000:
            # don't skeet about old books
            return

        db = GutenbergDatabase.Database()
        db.connect()
        c = db.get_cursor()

        c.execute("select * from tweets where media = 'Bluesky' and fk_books = %(fk_books)s",
                   {'fk_books': pg_id})

        rows = c.fetchone()
        if rows:
            # already skeeted
            return

        try:
            session = self.get_session()
            try:
                blob = self.get_blob(coverpath)
            except (FileNotFoundError) as what:
                exception('BlueskyWriter: could not find cover file (#%s)' % what)
                blob = ""

            title = job.dc.make_pretty_title(300 - 84).replace('"', '\\"')  # 300 is max length
            headers = {'Authorization': 'Bearer ' + session["accessJwt"]}
            pg_url = f'https://www.gutenberg.org/ebooks/{pg_id}'
            skeet = f"New #ebook at Project Gutenberg: {title} {pg_url}"
            skeetlen = len(skeet.encode("UTF-8"))
            facets =  [{
                "index": {
                    "byteStart": skeetlen - len(pg_url),
                    "byteEnd": skeetlen
                },
                "features": [{
                  "$type": "app.bsky.richtext.facet#link",
                  "uri": pg_url
                }]
            }]
            embed = {"$type": "app.bsky.embed.images",
                     "images": [{"alt": "", "image": blob,}],
                    }
            lang_id = job.dc.languages[0].id if len(job.dc.languages) else 'en'
            post = {"$type": "app.bsky.feed.post",
                    "text": skeet,
                    "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "langs": [lang_id],
                    "facets": facets,
                    }
            if blob:
                post['embed'] = embed
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

