#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

ReparseCredits.py


Copyright 2024 by Eric Hellman and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Reparses files that have no credit attributes in the database, and sets a credit if it finds one.
A bit kludgy.

"""
import configparser
import os

from sqlalchemy import select, desc

from libgutenberg import GutenbergDatabase
from libgutenberg import DBUtils, Logger
from libgutenberg.DublinCoreMapping import DublinCoreObject
from libgutenberg.GutenbergGlobals import Struct
from libgutenberg.Logger import critical, info, debug, warning, error, exception
from libgutenberg.Models import Attribute, Book

from ebookmaker.CommonCode import Options
from ebookmaker.ParserFactory import load_parsers, ParserFactory

from ebookconverter.Candidates import Candidates
from ebookconverter.EbookConverter import PREFERRED_INPUT_FORMATS

Logger.setup(Logger.LOGFORMAT, 'fileinfo.log')

options = Options()
options.mediatype_from_extension = True
options.verbose = 2


def config():
    # put command-line args into options

    cp = configparser.ConfigParser()
    cp.read(os.path.expanduser('~/.ebookconverter'))

    options.config = Struct()

    for section in cp.sections():
        for name, value in cp.items(section):
            setattr(options.config, name.upper(), value)

def get_source(ebook):
    cf = Candidates()
    all_candidates = cf.read_from_database(ebook)
    f = lambda x: x.format
    for type_ in ['html.images', 'txt.utf-8']:
        candidate_types = PREFERRED_INPUT_FORMATS.get(type_, {})
        candidates = all_candidates[:]
        candidate = None
        if len(candidate_types) > 0:
            if DBUtils.is_not_text(ebook):
                continue

            candidates = cf.filter_sort(candidate_types, candidates, f)

            if not candidates:
                continue

            candidate = candidates[0]
        if candidate:
            return os.path.join(options.config.FILESDIR, candidate.archive_path)

def reparse(book):
    ebook = book.pk
    src = get_source(ebook)
    if not src:
        return
    parser = ParserFactory.create(src)
    if parser:
        parser.parse()
        dc = DublinCoreObject()
        dc.project_gutenberg_id = ebook
        dc.load_from_parser(parser)
        return dc

def main():
    load_parsers()
    ob = GutenbergDatabase.Objectbase(False)
    session = ob.get_session()
    config()
    
    books = session.query(Book).join(Attribute.book)
    creditless = books.except_(books.filter(
            Attribute.fk_attriblist == 508)).order_by(desc(Book.pk)).all()
    info(f'reparsing {len(creditless)} books without credits')
    for book in creditless:
        dc = reparse(book)
        if dc and dc.credit:
            dc.add_attribute(book, dc.credit, marc=508)
            session.commit()
            info(f"set credit for {book.pk} to db: {dc.credit}")
    
main()
