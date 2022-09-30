#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

CoverpageWriter.py

Copyright 2022 by Eric Hellman and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Write metadata from source files to the database

"""
from lxml import etree

from libgutenberg.DublinCore import GutenbergDublinCore
from libgutenberg.Logger import info, exception

from ebookmaker import writers


class Writer(writers.BaseWriter):
    """ Class that checks the main file for a book if the db lacks a record. """


    def build(self, job):
        """ checking files for credit metadata """

        try:
            info(etree.tostring(job.dc.to_html()))
            if not bool(job.dc.credit):
                info("Checking credit metadata in file for %s" % job.ebook)
                file_dc = GutenbergDublinCore()
                file_dc.load_from_parser(job.spider.parsers[0])
                info(etree.tostring(file_dc.to_html()))
                if file_dc.credit:
                    job.dc.credit = file_dc.credit
                    job.dc.save(updatemode=1)
                    info("set credit for  %s", job.ebook)
                    return
                info("no credit metadata in %s", job.url)

        except Exception as what:
            exception ("Error checking metadata: %s" % what)
            raise
