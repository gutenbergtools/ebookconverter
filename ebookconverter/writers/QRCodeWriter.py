#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

QRCodeWriter.py

Copyright 2013 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Writes QRCodes.

"""

import binascii
import os

from PIL import Image
import qrcode

from libgutenberg.Logger import info, exception
from ebookmaker import writers


DESKTOP_URL = 'https://www.gutenberg.org/ebooks/%d'
MOBILE_URL  = 'https://m.gutenberg.org/ebooks/%d'

BOXSIZE     = 4           # pixels per box
COLOR       = '000000ff'  # RGBA
BACKGROUND  = 'ffffff00'


class MyQRCode (qrcode.QRCode):
    """ QRCode with better image builder. """

    def __init__ (self):
        super (MyQRCode, self).__init__ (
            error_correction = qrcode.constants.ERROR_CORRECT_M,
            box_size         = 1,
            border           = 0,
        )


    def make_image (self, color, background):
        """
        Format QR Code as png image one pixel per qr box.

        color and background are RGBA values in hex, eg. '808080ff'.

        """

        clr = binascii.a2b_hex (color)
        bgc = binascii.a2b_hex (background)
        # bg_tuple = tuple (map (ord, bgc))

        # first flatten the data into a string
        # self.modules is an array of arrays of booleans
        rows = []
        for row in self.modules:
            rows.append (b''.join ([clr if x else bgc for x in row]))

        # the busy part of the qrcode, 1 pixel per box
        modules = self.modules_count
        return Image.frombytes ('RGBA', (modules, modules), b''.join (rows), 'raw', 'RGBA', 0, 1)


class Writer (writers.BaseWriter):
    """ QRCode image writer. """

    def build (self, job):
        """ Build qrcode sprite. """

        info ("Making   %s" % job.outputfile)

        try:
            qr = MyQRCode ()
            qr.add_data (DESKTOP_URL % job.ebook)
            qr.make (fit = True)
            qrcode1 = qr.make_image (COLOR, BACKGROUND)

            qr = MyQRCode ()
            qr.add_data (MOBILE_URL % job.ebook)
            qr.make (fit = True)
            qrcode2 = qr.make_image (COLOR, BACKGROUND)

            modules = qr.modules_count

            # build an empty image with room for 2 qrcodes, leave 1 column free between
            sizex, sizey = 2 * modules + 1, modules
            image = Image.new ('RGBA', (sizex, sizey), (0, 0, 0, 0))
            image.paste (qrcode1, (0, 0))
            image.paste (qrcode2, (modules + 1, 0))

            image = image.resize ((sizex * BOXSIZE, sizey * BOXSIZE))

            fn = os.path.join (job.outputdir, job.outputfile)
            with open (fn, 'wb') as fp:
                image.save (fp, 'png')

            info ("Done     %s" % job.outputfile)

        except Exception as what:
            exception ("Error building QR-Code: %s" % what)
            raise
