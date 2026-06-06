#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

# Computes a Flesch reading-ease score for a book's text and stores it as
# attribute 908. Ported from the standalone end-of-month readability batch so
# the score is generated at build time. Scoring is local (textstat) and free,
# so it runs as part of --build=all.

import textstat

from libgutenberg.GutenbergDatabase import DatabaseError
from libgutenberg.Logger import exception, error, info
from libgutenberg.Models import Attribute
from ebookmaker.writers import TxtWriter

READABILITY_ATTR = 908

# reading-ease score bands: (min, max, grade level, description)
SCORE_RANGES = [
    (90, 100, "5th grade", "Very easy to read."),
    (80, 90, "6th grade", "Easy to read."),
    (70, 80, "7th grade", "Fairly easy to read."),
    (60, 70, "8th & 9th grade", "Neither easy nor difficult to read."),
    (50, 60, "10th to 12th grade", "Somewhat difficult to read."),
    (30, 50, "College-level", "Difficult to read."),
    (10, 30, "College graduate level", "Very difficult to read."),
    (0, 10, "Professional level", "Extremely difficult to read."),
]

def is_non_text(book):
    """Return True for non-text items (audio, images, data)."""
    return book.categories != []

def get_readability_grade(score):
    """Return (grade, description) band for a reading-ease score (clamped to 0-100)."""
    score = min(100, max(0, score))
    for min_val, max_val, grade, description in SCORE_RANGES:
        if min_val <= score <= max_val:
            return grade, description


class Writer (TxtWriter.Writer):
    """ Readability Writer Class. """

    def build(self, job):
        '''Compute reading-ease score and write to database.'''
        id = job.dc.project_gutenberg_id
        if is_non_text(job.dc.book):
            info ("ReadabilityWriter: Non-Text Job, Skipping Writing for %d" % id)
            return
        self.dc = job.dc

        try:
            # this should get the cached parser from our inherited TxtWriter
            parser = TxtWriter.ParserFactory.ParserFactory.parsers[job.url]
            # strip the PG license boilerplate so it doesn't skew the score on short texts
            book_content = self.remove_gutenberg_wrapper(parser.unicode_content())
        except KeyError as kerr:
            error ("ReadabilityWriter: Couldn't Access Text: %s" % kerr)
            return
        except UnicodeError as uerr:
            error ("ReadabilityWriter: Bad Text Content: %s" % uerr)
            return

        score = textstat.flesch_reading_ease(book_content)
        grade, description = get_readability_grade(score)
        db_text = "Reading ease score: %.1f (%s). %s" % (score, grade, description)
        self.insert_into_pg_database(id, db_text)

    def insert_into_pg_database(self, id, db_text):
        '''Insert or update the readability attribute (908).'''
        session = self.dc.get_my_session()
        existing = [a for a in self.dc.book.attributes if a.fk_attriblist == READABILITY_ATTR]
        try:
            if existing:
                existing[0].text = db_text
                session.commit()
                info ("ReadabilityWriter: replaced score: %d" % id)
                return
            self.dc.book.attributes.append(Attribute(
                fk_attriblist=READABILITY_ATTR, text=db_text, nonfiling=0))
            session.commit()
            info ("ReadabilityWriter: created score: %d" % id)
        except DatabaseError as dberr:
            exception ('ReadabilityWriter: could not add score to database: %s' % (dberr))

    def remove_gutenberg_wrapper(self, text):
        """Remove Gutenberg header and footer from book text."""
        lines = text.split('\n')
        start_index = 0
        end_index = len(lines)

        for i, line in enumerate(lines):
            if line.startswith("*** START OF"):
                start_index = i + 1
            elif line.startswith("*** END OF"):
                end_index = i
                break

        return '\n'.join(lines[start_index:end_index]).strip()
