#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

FileInfo.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Extract metadata from posted PG ebook.

Notes: 10/28/2019

- FileInfo.py looks for files named [number].zip.trig in the dopush "log" directory. If it finds 
  one, it looks for files in the in the FILES/[number] directory. 
- FileInfo scans the files (or members of the zip file) for a source file containing a plain-text 
  "PG header" and puts the metadata from the header into STDOUT. 
- TODO: remove hash columns from the Postgres database.
- When finished, the .trig files are moved to a 'backup' subdirectory.


"""

import base64
import binascii
import datetime
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile

import lxml

from libgutenberg.DBUtils import ebook_exists
from libgutenberg.GutenbergGlobals import xpath
from libgutenberg.Logger import debug, error, exception
from libgutenberg import Logger
from libgutenberg.DublinCoreMapping import DublinCoreObject

PRIVATE = os.getenv ('PRIVATE') or ''
PUBLIC  = os.getenv ('PUBLIC')  or ''
PUBLISH = os.getenv ('PUBLISH')  or ''

DOPUSH_LOG_DIR = PRIVATE + '/logs/dopush'
FILES = PUBLIC + '/files'
FTP   = '/public/ftp/pub/docs/books/gutenberg/'


PARSEABLE_FILES = '.rst .html .htm .tex .txt'.split ()
HTML_FILES = '.html .htm'.split ()



def parseable_file (filename):
    """ Return true if this file should be parsed for a pg header judging by the extension. """
    # these extension are parseable (ascii-ish) files
    return os.path.splitext (filename)[1] in PARSEABLE_FILES


def save_metadata(dc):
    """ Save the metadata. Assumes that there is no existing enty in the database. """

    if dc.title:
        dc.title = re.sub (r'\s*\n\s*', ' _ ', dc.title.strip ())

    if dc.rights.lower ().find ('copyright') > -1:
        dc.rights = 1 # ???

    dc.save()

def scan_header (bytes_, filename, ebook):
    """ Scan pg header in file. """

    try:
        dc = DublinCoreObject()
        dc.get_my_session()
        ext = os.path.splitext (filename)[1]

        if ext in HTML_FILES:
            body = None
            if bytes_.startswith (b'<?xml'):
                try:
                    # use XML parser
                    html = lxml.etree.fromstring (bytes_, lxml.etree.XMLParser (load_dtd = True))
                    if html is not None:
                        body = xpath (html, "//xhtml:body")[0]
                        for p in xpath (body, "//xhtml:p"): # fix PGTEI
                            p.tail = "\n"
                except (lxml.etree.ParseError, IndexError) as what:
                    debug ("# lxml XMLParser: %s" % what)

            else:
                try:
                    # use HTML parser
                    html = lxml.etree.fromstring (bytes_, lxml.etree.HTMLParser ())
                    if html is not None:
                        body = xpath (html, "//body")[0]
                except (lxml.etree.ParseError, IndexError) as what:
                    debug ("# lxml HTMLParser: %s" % what)

            if body is not None:
                try:
                    s = lxml.etree.tostring (
                        body,
                        encoding='unicode',
                        method='text')
                    dc.load_from_pgheader (s)
                except UnicodeError:
                    return None

        elif ext == '.rst':
            dc.load_from_rstheader (bytes_.decode ('utf-8'))

        else:
            try:
                dc.load_from_pgheader (bytes_.decode ('us-ascii'))
            except UnicodeError:
                try:
                    dc.load_from_pgheader (bytes_.decode ('utf-8'))
                except UnicodeError:
                    try:
                        dc.load_from_pgheader (bytes_.decode ('windows-1252'))
                    except UnicodeError:
                        return None

        if str(dc.project_gutenberg_id) == str(ebook):
            Logger.ebook = dc.project_gutenberg_id
            save_metadata(dc)
            return dc.project_gutenberg_id
        elif dc.project_gutenberg_id:
            error('loaded gutenberg id %s in %s did not match trigger id %s',
                  dc.project_gutenberg_id, filename, ebook)
        return None

    except ValueError as what:
        exception (what)
        debug ("Could not scan header of %s" % filename)
        return None


def scan_file (filename, ebook):
    """ Scan one file. """

    if parseable_file (filename):
        with open (filename, 'rb') as fp:
            if scan_header (fp.read (), filename, ebook):
                return True
    return False


def scan_zip (filename, ebook):
    """ Scan a zip file like a dir. """

    try:
        zip_ = zipfile.ZipFile (filename)
        for member in sorted (zip_.namelist (), key=file_sort_key):
            if parseable_file (member):
                if scan_header (zip_.read (member), member, ebook):
                    return True

    except (zipfile.error, NotImplementedError):
        pass

    return False


def stat_file (filename):
    """ Stat file. """

    try:
        # is file readable? else raise IOError
        fp = open (filename, 'r')
        fp.close ()

        st = os.stat (filename)

        print ('filename: %s'  % os.path.split (filename)[1])

        directory = os.path.split (filename)[0]
        directory = os.path.realpath (directory)
        directory = directory.replace (FTP, '')

        print ('directory: %s' % directory)

        print ('mtime: %d' % st.st_mtime)
        print ('size: %d'  % st.st_size)

        return 1

    except (OSError, IOError):
        return 0


def file_sort_key (filename):
    """ Sort files according to metadata quality.

    Files with best metadata first. """

    name, ext = os.path.splitext (filename)

    # sort parseable files first
    if ext in PARSEABLE_FILES:
        # -z sorts ascii text files last
        return "%02d %s-z" % (PARSEABLE_FILES.index (ext), name)
    return '99' + name + '-z'


def scan_directory(ebook_num):
    """ Scan one directory in the new archive filesystem. """
    # is ebook_num in db?

    dirname = os.path.join(FILES, str(ebook_num))
    debug ("Scanning directory %s ..." % dirname)

    found_files = []
    for root, dummy_dirs, files in os.walk (dirname):
        if '.hg' in root:
            continue
        for f in files:
            found_files.append (os.path.join (root, f))

    for filename in sorted (found_files, key=file_sort_key):
        debug ("Found file: %s" % filename)
        
        # statfile adds the file to the database
        if stat_file (filename, ebook_num):
            if not ebook_exists(ebook_num):
                if filename.endswith ('.zip'):
                    scan_zip (filename, ebook_num)
                else:
                    scan_file (filename, ebook_num)


def scan_dopush_log ():
    """ Scan the dopush log directory for new files.

    Files in this directory are placeholders only. The real files are
    in FILES/ and DIRS/ and PUBLISH/.

    """

    retcode = 1

    for filename in sorted (os.listdir (DOPUSH_LOG_DIR)):
        mode = os.stat (os.path.join (DOPUSH_LOG_DIR, filename))[stat.ST_MODE]
        if stat.S_ISDIR (mode):
            continue

        debug ("Tag file: %s" % filename)

        m = re.match (r'^(\d+)\.zip\.trig$', filename)
        if m:
            ebook_num = int(m.group(1))
            Logger.ebook = ebook_num
            scan_directory(ebook_num)

        shutil.move (os.path.join (DOPUSH_LOG_DIR, filename),
                     os.path.join (DOPUSH_LOG_DIR, 'backup', filename))
        retcode = 0

    return retcode

def main ():
    Logger.setup (Logger.LOGFORMAT, 'fileinfo.log')
    Logger.set_log_level (2)

    # This is the only encoding used at PG/ibiblio.
    # Bail out early if the environment is misconfigured.
    assert sys.stdout.encoding.lower () == 'utf-8'

    if len (sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                Logger.ebook = int(arg)
                scan_directory (int (arg))
            except ValueError: # no int
                scan_file (arg)

    else:
        sys.exit (scan_dopush_log ())

if __name__ == '__main__':
    main()
