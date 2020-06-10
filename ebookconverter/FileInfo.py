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
  "PG header" and puts the metadata from the header into STDOUT. dopush pipes this metadata to 
  autocat.php 
  TODO: bring autocat.php functionality into EbookConverter so that metadata initialization can be 
  smarter.
- All that BitCollider does is compute file hashes. These hashes were used in various Torrent-like
  distribution networks. The hashes are no longer used anywhere; the Postgres database only stores 
  hashes for the file used as the source file; not hashes are computed for other files. 
  TODO: remove Bitcollider, remove hash columns from the Postgres database.
- When finished, the .trig files are moved to a 'backup' subdirectory.


"""

from __future__ import unicode_literals
from __future__ import print_function

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

from libgutenberg.GutenbergGlobals import xpath
from libgutenberg.Logger import debug, exception
from libgutenberg import Logger
from libgutenberg import DublinCore

PRIVATE = os.getenv ('PRIVATE') or ''
PUBLIC  = os.getenv ('PUBLIC')  or ''
PUBLISH = os.getenv ('PUBLISH')  or ''

DOPUSH_LOG_DIR = PRIVATE + '/logs/dopush'
DIRS  = PUBLIC + '/dirs'
FILES = PUBLIC + '/files'
FTP   = '/public/ftp/pub/docs/books/gutenberg/'

BITCOLLIDER_EXECUTABLE = PRIVATE + '/bin/bitcollider-0.6.0'

PARSEABLE_FILES = '.rst .html .htm .tex .txt'.split ()
HTML_FILES = '.html .htm'.split ()

BITCOLLIDER_REGEXES = {
    'crc32.hex'    : re.compile (r'^tag\.crc32\.crc32=([A-Z0-9]+)$',   re.I | re.M),
    'md5.hex'      : re.compile (r'^tag\.md5\.md5=([A-Z0-9]+)$',       re.I | re.M),
    'kzhash.hex'   : re.compile (r'^tag\.kzhash\.kzhash=([A-Z0-9]+)$', re.I | re.M),
    'ed2khash.hex' : re.compile (r'^tag\.ed2k\.ed2khash=([A-Z0-9]+)$', re.I | re.M),
}


def parseable_file (filename):
    """ Return true if this file should be parsed for a pg header judging by the extension. """
    # these extension are parseable (ascii-ish) files
    return os.path.splitext (filename)[1] in PARSEABLE_FILES


def call_bitcollider (filename):
    """ Call the bitcollider executable and process results. """

    output = subprocess.Popen ([BITCOLLIDER_EXECUTABLE, '-p', '--md5', '--crc32', filename],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate ()[0]

    try:
        output = output.decode ('ascii')
    except UnicodeError as what:
        sys.stderr.write ("Bitcollider Error: %s\n" % what)
        return

    hashes = dict ()

    for key, regex in BITCOLLIDER_REGEXES.items ():
        m = regex.search (output)
        if m:
            hashes[key] = m.group (1)

    m = re.search (r'^bitprint=([A-Z0-9]+)\.([A-Z0-9]+)$', output, re.I | re.M)
    if m:
        s1 = m.group (1).ljust (32, '=')
        s2 = m.group (2).ljust (40, '=')
        hashes['sha1.base32']      = s1
        hashes['tigertree.base32'] = s2
        hashes['sha1.hex']         = binascii.hexlify (base64.b32decode (s1)).decode ('ascii')
        hashes['tigertree.hex']    = binascii.hexlify (base64.b32decode (s2)).decode ('ascii')

    hashes['crc32.hex'] = (hashes['crc32.hex'].lower ())

    for key in sorted (hashes.keys ()):
        print ('%s: %s' % (key, hashes[key]))


def print_metadata_text (dc):
    """ Print out the metadata. """

    def print_caption (caption, data):
        """ Print one or more lines of metadata. """

        if isinstance (data, list):
            for d in data:
                print ("%s: %s" % (caption, d))
        else:
            if data:
                print ("%s: %s" % (caption, data))

    for a in dc.authors:
        if ',' in a.name:
            print_caption (a.role.title (), a.name)
        else:
            m = re.match (r'^(.+?)\s+([-\'\w]+)$', a.name, re.I | re.U)
            if m:
                print_caption (a.role.title (), "%s, %s" % (m.group (2), m.group (1)))
            else:
                print_caption (a.role.title (), a.name)

    for l in dc.languages:
        print_caption ('Language', l.language)

    for s in dc.subjects:
        print_caption ('Subject', s.subject)

    for l in dc.loccs:
        print_caption ('Locc', l.locc)

    if dc.project_gutenberg_id:
        print_caption ('Etext-Nr',     str (dc.project_gutenberg_id))

    if dc.title:
        dc.title = re.sub (r'\s*\n\s*', ' _ ', dc.title.strip ())

    print_caption ('Title',        dc.title)
    print_caption ('Encoding',     dc.encoding)
    print_caption ('Category',     dc.categories)
    print_caption ('Contents',     dc.contents)
    print_caption ('Notes',        dc.notes)
    print_caption ('Edition',      dc.edition)

    if dc.release_date:
        print_caption ('Release-Date', datetime.datetime.strftime (dc.release_date, '%b %d, %Y'))

    if dc.rights.lower ().find ('copyright') > -1:
        print_caption ('Copyright', '1')


def scan_header (bytes_, filename):
    """ Scan pg header in file. """

    try:
        dc = DublinCore.GutenbergDublinCore ()
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

        if dc.project_gutenberg_id:
            Logger.ebook = dc.project_gutenberg_id
            print_metadata_text (dc)
            return dc.project_gutenberg_id
        return None

    except ValueError as what:
        exception (what)
        debug ("Could not scan header of %s" % filename)
        return None


def scan_file (filename):
    """ Scan one file. """

    if parseable_file (filename):
        with open (filename, 'rb') as fp:
            if scan_header (fp.read (), filename):
                return True
    return False


def scan_zip (filename):
    """ Scan a zip file like a dir. """

    try:
        zip_ = zipfile.ZipFile (filename)
        for member in sorted (zip_.namelist (), key=file_sort_key):
            if parseable_file (member):
                if scan_header (zip_.read (member), member):
                    print ('Zipmemberfilename: %s' %  member)
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


def scan_directory (dirname):
    """ Scan one directory in the new archive filesystem. """

    # dirname = os.path.realpath (dirname)
    debug ("Scanning directory %s ..." % dirname)

    found_files = []
    for root, dummy_dirs, files in os.walk (dirname):
        if '.hg' in root:
            continue
        for f in files:
            found_files.append (os.path.join (root, f))

    for filename in sorted (found_files, key=file_sort_key):
        debug ("Found file: %s" % filename)

        if stat_file (filename):
            if filename.endswith ('.zip'):
                scan_zip (filename)
            else:
                scan_file (filename)
            call_bitcollider (filename)
            print ('-' * 10)


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
            Logger.ebook = m.group(1)
            dirname = os.path.join (FILES, m.group (1))
            scan_directory (dirname)

            dirname = os.path.join (PUBLISH, m.group (1))
            # scan_directory (dirname)
        else:
            # old archive /etextXX
            m = re.match (r'^(etext\d\d)-(\w+\.\w+).trig$', filename)
            if m:
                fn = os.path.join (DIRS, m.group (1), m.group (2))
                if stat_file (fn):
                    if filename.endswith ('.zip'):
                        scan_zip (fn)
                    else:
                        scan_file (fn)
                    call_bitcollider (fn)
                    print ('-' * 10)

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
                scan_directory (os.path.join (FILES, str (int (arg))))
            except ValueError: # no int
                scan_file (arg)

    else:
        sys.exit (scan_dopush_log ())

if __name__ == '__main__':
    main()
