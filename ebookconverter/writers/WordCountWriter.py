#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

# Counts the words in a book's text and stores the total as attribute 909 (for now).
# Rather than naively splitting on spaces, we pick out the actual words, so that
# stray punctuation and formatting marks aren't miscounted as words.


import re

from libgutenberg.GutenbergDatabase import DatabaseError
from libgutenberg.Logger import exception, error, info, debug
from libgutenberg.Models import Attribute
from ebookmaker.writers import TxtWriter
from ebookmaker.parsers.boilerplate import strip_headers_from_txt

WORDCOUNT_ATTR = 909  # placeholder code -- Eric to confirm/replace

# We match runs of letters/digits (keeping internal apostrophes and hyphens,
# so "don't" and "mother-in-law" stay single words) instead of a plain split().
# A naive split() gets fooled by PG plain text: em-dashes are glued between
# words ("said--and"), and italics are marked with underscores ("_word_"), so
# it would miscount. Matching word-runs sidesteps both and drops punctuation
# and blank lines for free.
WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*")

def is_non_text(book):
    """Return True for non-text items (audio, images, data)."""
    return book.categories != []


class Writer (TxtWriter.Writer):
    """ Word Count Writer Class. """

    def build(self, job):
        '''Count words in the book text and write the total to the database.'''
        id = job.dc.project_gutenberg_id
        if is_non_text(job.dc.book):
            info ("WordCountWriter: Non-Text Job, Skipping Writing for %d" % id)
            return
        self.dc = job.dc

        try:
            # this should get the cached parser from our inherited TxtWriter
            parser = TxtWriter.ParserFactory.ParserFactory.parsers[job.url]
            # strip the PG license boilerplate so it isn't counted
            book_content, _, _ = strip_headers_from_txt(parser.unicode_content())
        except KeyError as kerr:
            error ("WordCountWriter: Couldn't Access Text: %s" % kerr)
            return
        except UnicodeError as uerr:
            error ("WordCountWriter: Bad Text Content: %s" % uerr)
            return

        count = len(WORD_RE.findall(book_content))
        self.insert_into_pg_database(id, str(count))

    def insert_into_pg_database(self, id, db_text):
        '''Insert or update the word-count attribute (909).'''
        session = self.dc.get_my_session()
        existing = [a for a in self.dc.book.attributes if a.fk_attriblist == WORDCOUNT_ATTR]
        try:
            if existing:
                existing[0].text = db_text
                session.commit()
                debug ("WordCountWriter: replaced count: %d" % id)
                return
            self.dc.book.attributes.append(Attribute(
                fk_attriblist=WORDCOUNT_ATTR, text=db_text, nonfiling=0))
            session.commit()
            info ("WordCountWriter: created count: %d" % id)
        except DatabaseError as dberr:
            exception ('WordCountWriter: could not add count to database: %s' % (dberr))
