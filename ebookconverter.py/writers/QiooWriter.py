#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""
QiooWriter.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Build a QiOO(tm) document out of a PG plain text file.
That is just a java jar file with the plain text stuffed in.

"""

import os.path
import zipfile

import requests

from pkg_resources import resource_string # pylint: disable=E0611

from libgutenberg.Logger import debug, info
from ebookmaker import writers

class Writer (writers.BaseWriter):
    """ Class to write the proprietary QiOO format. """


    def build (self, job):
        """ Build QiOO file. """

        basename = job.outputfile
        zipfilename = os.path.join (job.outputdir, basename)

        info ("Creating QiOO file: %s" % zipfilename)

        manifest = """Manifest-Version: 1.0
MIDlet-Data-Size: 2000
MicroEdition-Configuration: CLDC-1.0
MIDlet-Name: %s
MIDlet-Description: QiOO Mobile Reader
MIDlet-Info-URL: http://www.qioo.com
MIDlet-Vendor: http://www.qioo.com
MIDlet-1: %s, /MobileLibrary.png, reader.MobileLibrary
MIDlet-Version: 1.1
MicroEdition-Profile: MIDP-2.0
""" % (basename, basename)

        # write skeleton zip
        with open (zipfilename, 'wb') as fp:
            data = resource_string ('ebookconverter.writers', 'qioo-skeleton.zip')
            fp.write (data)

        # open skeleton zip for append
        jar = zipfile.ZipFile (zipfilename, 'a', zipfile.ZIP_DEFLATED)

        # add manifest
        jar.writestr ('META-INF/MANIFEST.MF', manifest)

        # add plain txt
        url = job.url
        debug ("Fetching %s ..." % url)
        fp = requests.get (url)
        jar.writestr ('data', fp.content)
        fp.close ()

        jar.close ()

        info ("Done QiOO file: %s" % zipfilename)
