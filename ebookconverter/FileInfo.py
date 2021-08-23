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

import json
import os
import re
import shutil
import stat
import sys
import zipfile

import lxml

from libgutenberg.DBUtils import check_session, ebook_exists
from libgutenberg.DublinCoreMapping import DublinCoreObject
from libgutenberg.GutenbergFiles import store_file_in_database
from libgutenberg.GutenbergGlobals import xpath
from libgutenberg.Models import Book
from libgutenberg.Logger import critical, debug, error, exception, info, warning
from libgutenberg import Logger

from .Notifier import ADDRESS_BOOK
PRIVATE = os.getenv ('PRIVATE') or ''
PUBLIC  = os.getenv ('PUBLIC')  or ''
PUBLISH = os.getenv ('PUBLISH')  or ''

DOPUSH_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopush')
WORKFLOW_LOG_DIR = os.path.join(PRIVATE, 'logs', 'json')

FILES = os.path.join(PUBLIC, 'files')
FTP   = '/public/ftp/pub/docs/books/gutenberg/'

PARSEABLE_FILES = '.rst .html .htm .tex .txt'.split ()
HTML_FILES = '.html .htm'.split ()



def parseable_file (filename):
    """ Return true if this file should be parsed for a pg header judging by the extension. """
    # these extension are parseable (ascii-ish) files
    return os.path.splitext (filename)[1] in PARSEABLE_FILES


def save_metadata(dc):
    """ Save the metadata. """

    if dc.title:
        dc.title = re.sub (r'\s*\n\s*', ' _ ', dc.title.strip ())

    if dc.rights.lower ().find ('copyright') > -1:
        dc.rights = 1 # ???

    dc.save()

def get_workflow_file(ebook):
    """ return the workflow metadata file, if it exists"""
    if not ebook:
        return None
    wf_file = os.path.join(WORKFLOW_LOG_DIR, str(ebook) + '.json')
    non_wf_file = os.path.join(WORKFLOW_LOG_DIR, str(ebook) + '.txt')
    debug('wf_file %s exists: %s', wf_file, os.path.exists(wf_file))
    if os.path.exists(wf_file):
        return wf_file
    if os.path.exists(non_wf_file):
        return non_wf_file
    return None

def archive_workflow_file(filename):
    """ archive the workflow metadata file"""
    try:
        shutil.move(filename, os.path.join(WORKFLOW_LOG_DIR, 'backup'))
    except shutil.Error:
        filename_nopath = os.path.split(filename)[1]
        for rev in range(0, 10):
            dest = os.path.join(WORKFLOW_LOG_DIR, 'backup', '%s.%s' % (filename_nopath, rev))
            if not os.path.exists(dest):
                shutil.copy(filename, dest)
                break
            if rev == 9:
                warning('too many revisions, %s not archived', filename)
        os.remove(filename)


def handle_non_dc(data, ebook):
    try:
        non_dc = json.loads(data)
        try:
            notify = non_dc['DATA']['NOTIFY']
        except KeyError:
            info("no notify address for %s", ebook)
            notify = None
        try:
            ww = non_dc['DATA']['WW']
        except KeyError:
            info("no ww address for %s", ebook)
            ww = None
    except ValueError:
        error("bad json file for %s", ebook)
        notify = None

    if notify:
        ADDRESS_BOOK.set_email(ebook, notify)
    if ww:
        ADDRESS_BOOK.set_email(ebook, ww, role='ww')


def scan_header(data, filename, ebook):
    """ Scan pg header in file. Or see if there is a workflow json file. """

    try:
        dc = DublinCoreObject()
        dc.load_book(ebook)
        ext = os.path.splitext(filename)[1]

        workflow_file = get_workflow_file(ebook)
        info('workflow file found: %s', workflow_file)

        if workflow_file and workflow_file.endswith('.json'):
            data = ''
            with open(workflow_file, 'r') as fp:
                data = fp.read()
            try:
                dc.load_from_pgheader(data)
            except ValueError:
                critical("%s was not a valid workflow file", workflow_file)
            if dc.project_gutenberg_id:
                dc.encoding = 'utf-8'
                handle_non_dc(data, dc.project_gutenberg_id)
            archive_workflow_file(workflow_file)
            save_metadata(dc)
            return dc.project_gutenberg_id
        if workflow_file and workflow_file.endswith('.txt'):
            # get text from the non-workflow txt file, if it exists
            with open(workflow_file, 'r') as fp:
                ww = fp.read()
                ADDRESS_BOOK.set_email(ebook, ww, role='ww')
            archive_workflow_file(workflow_file)

        if ext in HTML_FILES:
            body = None
            if data.startswith('<?xml'):
                try:
                    # use XML parser
                    html = lxml.etree.fromstring(data, lxml.etree.XMLParser(load_dtd = True))
                    if html is not None:
                        body = xpath(html, "//xhtml:body")[0]
                        for p in xpath(body, "//xhtml:p"): # fix PGTEI
                            p.tail = "\n"
                except (lxml.etree.ParseError, IndexError) as what:
                    debug("# lxml XMLParser: %s" % what)

            else:
                try:
                    # use HTML parser
                    html = lxml.etree.fromstring(data, lxml.etree.HTMLParser())
                    if html is not None:
                        body = xpath(html, "//body")[0]
                except (lxml.etree.ParseError, IndexError) as what:
                    debug("# lxml HTMLParser: %s" % what)

            if body is not None:
                try:
                    s = lxml.etree.tostring(
                        body,
                        encoding='unicode',
                        method='text')
                    dc.load_from_pgheader(s)
                except UnicodeError:
                    return None

        elif ext == '.rst':
            dc.load_from_rstheader(data)

        else:
            dc.load_from_pgheader(data)

        if str(dc.project_gutenberg_id) == str(ebook):
            save_metadata(dc)
            return dc.project_gutenberg_id
        if dc.project_gutenberg_id:
            error('loaded gutenberg id %s in %s did not match trigger id %s',
                  dc.project_gutenberg_id, filename, ebook)
        return None

    except ValueError as what:
        exception (what)
        debug("Could not scan header of %s" % filename)
        return None


def scan_file(filename, ebook):
    """ Scan one file. """
    data = ''
    if parseable_file(filename):
        with open(filename, 'rb') as fp:
            data = read_string(fp.read())
    if scan_header(data, filename, ebook):
        return True
    return False


def scan_zip(filename, ebook):
    """ Scan a zip file like a dir. """

    try:
        zip_ = zipfile.ZipFile(filename)
        for member in sorted(zip_.namelist(), key=file_sort_key):
            if parseable_file(member):
                if scan_header(read_string(zip_.read(member)), member, ebook):
                    return True
    except (zipfile.error, NotImplementedError):
        pass
    return False

def read_string(bytes_data):
    for encoding in ['utf-8', 'iso-8859-1']:
        try:
            data = bytes_data.decode(encoding)
            return data
        except UnicodeError:
            pass
    return ''

def is_readable(filename):
    """ Used to be "stat_file. The 'stat' part has been refactored into libgutenberg """
    try:
        # is file readable? else raise IOError
        fp = open(filename, 'r')
        fp.close()
        return 1

    except IOError:
        return 0


def file_sort_key(filename):
    """ Sort files according to metadata quality.

    Files with best metadata first. """

    name, ext = os.path.splitext(filename)

    # sort parseable files first
    if ext in PARSEABLE_FILES:
        # -z sorts ascii text files last
        return "%02d %s-z" % (PARSEABLE_FILES.index(ext), name)
    return '99' + name + '-z'


def create_ebook(ebook_num, session=None):
    """ create an ebook, only info will be the number
    release_date=today() autoassigned by server"""
    session = check_session(session)
    new_ebook = Book(pk=ebook_num)
    session.add(new_ebook)
    session.commit()


def scan_directory(ebook_num):
    """ Scan one directory in the new archive filesystem. """
    # is ebook_num in db?

    dirname = os.path.join(FILES, str(ebook_num))
    debug("Scanning directory %s ...", dirname)

    found_files = []
    for root, dummy_dirs, files in os.walk(dirname):
        # don't catalog dot files
        if '/.' in root or root.startswith('.'):
            continue
        for f in files:
            if f.startswith('.'):
                continue
            found_files.append(os.path.join(root, f))

    header_found = False
    for filename in sorted(found_files, key=file_sort_key):
        if is_readable(filename):
            if not ebook_exists(ebook_num):
                create_ebook(ebook_num)
            if not header_found:
                if filename.endswith('.zip'):
                    header_found = scan_zip(filename, ebook_num)
                else:
                    header_found = scan_file(filename, ebook_num)

            store_file_in_database(ebook_num, filename, None)
        else:
            warning(filename + 'is not readable')

def scan_dopush_log():
    """ Scan the dopush log directory for new files.

    Files in this directory are placeholders only. The real files are
    in FILES/  and PUBLISH/.

    """

    retcode = 1

    for filename in sorted(os.listdir(DOPUSH_LOG_DIR)):
        mode = os.stat(os.path.join(DOPUSH_LOG_DIR, filename))[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            continue

        debug("Tag file: %s" % filename)

        ebook_num = 0
        m = re.match(r'^(\d+)\.zip\.trig$', filename)
        if m:
            ebook_num = int(m.group(1))
            Logger.ebook = ebook_num
            scan_directory(ebook_num)

        shutil.move(os.path.join(DOPUSH_LOG_DIR, filename),
                     os.path.join(DOPUSH_LOG_DIR, 'backup', filename))
        retcode = 0

    return retcode

def main():
    Logger.setup(Logger.LOGFORMAT, 'fileinfo.log')
    Logger.set_log_level(2)

    # This is the only encoding used at PG/ibiblio.
    # Bail out early if the environment is misconfigured.
    assert str(sys.stdout.encoding).lower() == 'utf-8'

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                Logger.ebook = int(arg)
                scan_directory(int(arg))
            except ValueError: # no int
                scan_file(arg, None)

    else:
        sys.exit(scan_dopush_log())

if __name__ == '__main__':
    main()
