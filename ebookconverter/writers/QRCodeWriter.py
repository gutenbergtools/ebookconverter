#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

QRCodeWriter.py

Copyright 2013-2020 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Writes QRCodes.

"""

import os

import qrcode

from libgutenberg.Logger import info, exception
from ebookmaker import writers


DESKTOP_URL = 'https://www.gutenberg.org/ebooks/%d'

class MyQRCode(qrcode.QRCode):
    """ QRCode with parameters. """

    def __init__(self):
        super(MyQRCode, self).__init__(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=0,
        )


class Writer(writers.BaseWriter):
    """ QRCode image writer. """

    def build(self, job):
        """ write qrcode . """

        info("Making   %s" % job.outputfile)

        try:
            qr = MyQRCode()
            qr.add_data(DESKTOP_URL % job.ebook)
            qr.make(fit=True)
            qrcode1 = qr.make_image(fill_color="black", back_color="white")

            fn = os.path.join(job.outputdir, job.outputfile)
            with open(fn, 'wb') as fp:
                qrcode1.save(fp, 'png')

            info("Done     %s" % job.outputfile)

        except Exception as what:
            exception("Error building QR-Code: %s" % what)
            raise
