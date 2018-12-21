#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

CoverpageWriter.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Writes coverpage thumbnails.

"""


import os

from libgutenberg.Logger import info, exception

from ebookmaker import writers


MAX_IMAGE_SIZE  =  63 * 1024  # in bytes
MAX_IMAGE_DIMEN = (200, 300)  # in pixels

MAX_THUMB_SIZE  =  16 * 1024  # in bytes
MAX_THUMB_DIMEN = ( 66, 100)  # in pixels

class Writer (writers.BaseWriter):
    """ Class that writes coverpage thumbs. """

    dimensions = {
        'cover.medium': (MAX_IMAGE_SIZE, MAX_IMAGE_DIMEN),
        'cover.small':  (MAX_THUMB_SIZE, MAX_THUMB_DIMEN),
        }


    def build (self, job):
        """ Build coverpage thumbs """

        info ("Making   %s" % job.outputfile)

        try:
            for p in job.spider.parsers:
                if hasattr (p, 'resize_image') and 'coverpage' in p.attribs.rel:
                    dimen = self.dimensions [job.type]
                    np = p.resize_image (dimen[0], dimen[1], 'jpeg')

                    fn = os.path.join (job.outputdir, job.outputfile)
                    with open (fn, 'wb') as fp:
                        fp.write (np.serialize ())

                    info ("Found coverpage %s" % p.attribs.url)
                    # if job.ebook and hasattr (job.dc, 'register_coverpage'):
                    #     job.dc.register_coverpage (job.ebook, p.attribs.url)
                    break

            info ("Done     %s" % job.outputfile)

        except Exception as what:
            exception ("Error building coverpage: %s" % what)
            raise
