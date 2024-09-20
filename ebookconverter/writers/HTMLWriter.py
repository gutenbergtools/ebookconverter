#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

HTMLWriter.py

Copyright 2023 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

"""
import os
import zipfile

from libgutenberg.Logger import debug, exception, info, error, warning
import libgutenberg.GutenbergGlobals as gg

from ebookmaker.writers import HTMLWriter as BaseHTMLWriter
from ..EbookConverter import make_output_filename, FILENAMES

BaseHTMLWriter.FILENAMES = FILENAMES

def arcurl(job, outfile):
    if outfile.startswith(job.outputdir):
        return outfile[len(job.outputdir) + 1:]
    else:
        info(job.outputdir, outfile)
        return outfile

class Writer(BaseHTMLWriter.Writer):
    """ Class for writing HTML files, including Zip bundle. """


    def build(self, job):
        """ Build HTML file. """
        old_credit = job.dc.credit
        info(f"credit was db: {job.dc.credit}")
        super().build(job)
        try:
            # now zip up the files
            zipfilename = os.path.join(job.outputdir, make_output_filename('zip', job.ebook))
            with zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED) as outzipfile:
                for p in job.spider.parsers:
                    outfile = gg.normalize_path(self.outputfileurl(job, p.attribs.url))
                    if outfile.endswith('/'):
                        # main file, special handling
                        outfile = os.path.join(outfile, job.outputfile)

                    try:
                        os.stat(outfile)
                        dummy_name, ext = os.path.splitext(outfile)
                        info(' Adding file: %s as %s' % (outfile, arcurl(job, outfile)))
                        outzipfile.write(outfile, arcurl(job, outfile),
                                    zipfile.ZIP_STORED if ext in ['.zip', '.png', '.jpeg', '.jpg']
                                    else zipfile.ZIP_DEFLATED)
                    except OSError:
                        warning ('build zip: Cannot add file %s', outfile)
        except Exception as what:
            exception("Error making zip %s: %s" % (outzipfile, what))
            if os.access(outfile, os.W_OK):
                os.remove(outfile)
            raise what
        
        info("Done making zip: %s" % job.outputfile)
        
        if job.dc.credit and job.dc.credit != old_credit:
            job.dc.add_attribute(job.dc.book, job.dc.credit, marc=508)
            job.dc.session.commit()
            info(f"set credit to db: {job.dc.credit}")
        
