#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""
EbookConverter.py

Copyright 2009-2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Driver for the ibiblio environment.  Queries the PG database and finds
out which files to convert, then passes them to Ebookmaker.

"""

import argparse
import collections
import configparser
import datetime
import itertools
import logging
import os
import subprocess
import sys

from six.moves import builtins, urllib, cPickle
import setproctitle

from libgutenberg import GutenbergDatabase, GutenbergDatabaseDublinCore, \
     DummyConnectionPool, Logger
from libgutenberg.GutenbergGlobals import Struct
from libgutenberg.Logger import info, debug, warning, error, exception

from ebookmaker import CommonCode
from ebookmaker.CommonCode import Options

from ebookconverter import Candidates
from ebookconverter.Version import VERSION

options = Options()

CONFIG_FILES = ['/etc/ebookconverter.conf', os.path.expanduser ('~/.ebookconverter')]

NON_UTF_TXTS = ('txt/windows-125*', 'txt/iso-8859-*', 'txt/big5', 'txt/ibm*', 'txt/*')
ALL_TXTS = ('txt/utf-8', ) + NON_UTF_TXTS
ALL_HTM =  ('html/utf-8', 'html/windows-125*', 'html/iso-8859-*', 'html/*')
ALL_SRCS = ('rst/*',) + ALL_HTM + ALL_TXTS
PREFERRED_INPUT_FORMATS = {

    # current practice is not to upload rst.master yet
    'rst.gen': ('rst/*', ),

    # epub readers should be able to handle unicode,
    # prefer the big charsets but accept any charset
    'epub.images': ALL_SRCS,

    'kindle.images': ('epub.images/*', ),
    'kindle.noimages': ('epub.noimages/*', ),

    # html is created from rst files or text files
    'html.images': ('rst/*', ) + ALL_TXTS,

    # utf txt is created from text files
    'txt.utf-8': ('rst/*', ) + NON_UTF_TXTS,

    # pdf is created only from rst
    'pdf.images': ('rst/*', ),

    # picsdir only if pdf or html are created
    'picsdir.images': ('rst/*', ),

    # coverpage (a cover will be generated, whatever)
    'cover.medium':  ('rst/*', 'html/*', 'txt/*'),
    
    # only make these if there's a source file registered in the database
    'rdf': ('rst/*', 'html/*', 'txt/*'),
    'qrcode': ('rst/*', 'html/*', 'txt/*'),
    'facebook': ('rst/*', 'html/*', 'txt/*'),
    'twitter': ('rst/*', 'html/*', 'txt/*'),
}

PREFERRED_INPUT_FORMATS['html.noimages']      = PREFERRED_INPUT_FORMATS['html.images']
PREFERRED_INPUT_FORMATS['epub.noimages']      = PREFERRED_INPUT_FORMATS['epub.images']
PREFERRED_INPUT_FORMATS['pdf.noimages']       = PREFERRED_INPUT_FORMATS['pdf.images']
PREFERRED_INPUT_FORMATS['picsdir.noimages']   = PREFERRED_INPUT_FORMATS['picsdir.images']
PREFERRED_INPUT_FORMATS['cover.small']        = PREFERRED_INPUT_FORMATS['cover.medium']
PREFERRED_INPUT_FORMATS['null']               = PREFERRED_INPUT_FORMATS['epub.images']

EXCLUSIONS = {
    'epub.images':     ('epub.dp',   ),
    'epub.noimages':   ('epub.dp',   ),
    'html.images':     ('html/*',    ),
    'html.noimages':   ('html/*',    ),
    'txt.utf-8':       ('txt/utf-8', ),
}

FILENAMES = {
    'html.noimages':    'pg{id}.html.utf8',
    'html.images':      'pg{id}-images.html.utf8',
    'epub.noimages':    'pg{id}.epub',
    'epub.images':      'pg{id}-images.epub',
    'kindle.noimages':  'pg{id}.mobi',
    'kindle.images':    'pg{id}-images.mobi',
    'pdf.noimages':     'pg{id}.pdf',
    'pdf.images':       'pg{id}-images.pdf',
    'txt.utf-8':        'pg{id}.txt.utf8',
    'rdf':              'pg{id}.rdf',
    'rst.gen':          'pg{id}.rst.utf8',
    'twitter':          'pg{id}.twitter',            # FIXME: do we need these?
    'facebook':         'pg{id}.facebook',           #
    'picsdir.noimages': 'pg{id}-noimages.picsdir',   #
    'picsdir.images':   'pg{id}-images.picsdir',     #
    'cover.small':      'pg{id}.cover.small.jpg',
    'cover.medium':     'pg{id}.cover.medium.jpg',
    'qrcode':           'pg{id}.qrcode.png',
    'logfile':          'pg{id}.converter.log',      # .converter because of conflicts with latex log
}

DEPENDENCIES = collections.OrderedDict ((
    ('everything',      ('all', 'facebook', 'twitter')),
    ('all',             ('html', 'epub', 'kindle', 'pdf', 'txt', 'rst',
                         'cover', 'qrcode', 'rdf')),
    ('html',            ('html.images',    'html.noimages')),
    ('epub',            ('epub.images',    'epub.noimages')),
    ('kindle',          ('kindle.images',  'kindle.noimages')),
    ('pdf',             ('pdf.images',     'pdf.noimages')),
    ('txt',             ('txt.utf-8',      'txt.iso-8859-1', 'txt.us-ascii')),
    ('rst',             ('rst.gen', )),
    ('kindle.noimages', ('epub.noimages', )),
    ('kindle.images',   ('epub.images', )),
    ('html.noimages',   ('picsdir.noimages', )),
    ('html.images',     ('picsdir.images', )),
    ('pdf.noimages',    ('picsdir.noimages', )),
    ('pdf.images',      ('picsdir.images', )),
    ('rst.gen',         ('picsdir.images', )),
    ('cover',           ('cover.medium',   'cover.small')),
))

BUILD_ORDER = """
picsdir.images picsdir.noimages
rst.gen
txt.utf-8
html.images html.noimages
epub.images epub.noimages
kindle.images kindle.noimages
cover.small cover.medium
pdf.images pdf.noimages
qrcode rdf
facebook twitter
null
""".split ()


def make_output_filename (type_, ebook = 0):
    """ Make a suitable filename for output type. """

    return FILENAMES[type_].format (id = ebook)


class Maker (object):
    """ Helper class """

    def __init__ (self, ebook, dc):
        self.ebook = ebook
        self.dc = dc


    def get_cache_dir (self):
        """ return the cache directory for this ebook """
        return os.path.join (options.config.CACHEDIR, "%d" % self.ebook)

    def get_cache_loc (self):
        """ return the cache loc for this ebook """
        return os.path.join (options.config.CACHELOC, "%d" % self.ebook)

    @staticmethod
    def target_outdated (job, candidate):
        """ Return True if outputfile newer than candidate exists. """

        path = os.path.join (job.outputdir, job.outputfile)

        if os.path.isfile (path):
            mtime_cand = candidate.mtime
            mtime_epub = datetime.datetime.fromtimestamp (os.path.getmtime (path))

            debug ('mtime cand:  %s' % mtime_cand)
            debug ('mtime dest:  %s' % mtime_epub)

            if mtime_cand < mtime_epub:
                if job.type in options.build:
                    info ('Making   %s: user requested build.' % job.outputfile)
                    return True
                else:
                    info ('Skipping %s: target newer than candidate.' % job.outputfile)
                    return False

            info ('Making   %s: target out of date.' % job.outputfile)
            return True

        info ('Making   %s: does not exist.' % job.outputfile)
        return True


    def remove_type (self, type_):
        """ Remove file for type. """

        fn = os.path.join (self.get_cache_dir (), make_output_filename (type_, self.ebook))
        try:
            os.remove (fn)
            debug ("Removed file from disk: %s" % fn)
        except OSError:
            pass
        try:
            os.remove (fn + '.gz')
            debug ("Removed file from disk: %s.gz" % fn)
        except OSError:
            pass

        fn = os.path.join (self.get_cache_loc (), make_output_filename (type_, self.ebook))

        if options.shadow:
            debug ("If not in shadow, would have removed file from database: %s" % fn)
        else:
            self.dc.remove_file_from_database (fn)
            debug ("Removed file from database: %s" % fn)


    def mk_job_queue (self):
        """ Make job queue for one ebook. """

        cf = Candidates.Candidates ()
        all_candidates = cf.read_from_database (self.ebook)
        job_queue = []
        f = lambda x: x.format
        debug ("All Candidates: %s" % ' '.join (map (f, all_candidates)))

        for type_ in options.make:
            debug ("Trying: %s ..." % type_)

            job = CommonCode.Job (type_)
            job.ebook = self.ebook
            job.dc = self.dc
            job.outputdir  = self.get_cache_dir ()
            job.outputfile = make_output_filename (type_, self.ebook)
            job.logfile = make_output_filename ('logfile', self.ebook)

            candidates = all_candidates[:]
            needs_source = len (PREFERRED_INPUT_FORMATS[type_]) > 0

            if type_ in EXCLUSIONS and cf.filter_sort (
                    EXCLUSIONS[type_], [c for c in candidates if not c.generated], f):
                info ('%s is already posted.' % type_)
                if not options.dry_run:
                    self.remove_type (type_)
                continue

            if needs_source:
                if not 'Text' in self.dc.categories:
                    info ("Book is not a text book. Skipping %s ..." % type_)
                    continue

                candidates = cf.filter_sort (PREFERRED_INPUT_FORMATS[type_], candidates, f)

                if not candidates:
                    info ('No input file found for type: %s' % type_)
                    if not options.dry_run:
                        self.remove_type (type_) # clean leftovers
                    continue

                candidate = candidates[0]

                debug ("Candidates: %s" % ' '.join (map (f, candidates)))

                # oom-killer safeguard
                if job.maintype == 'txt' and candidate.size > 8 * 1024 * 1024:
                    warning ('Skipping %s: file too big' % candidate.filename)
                    continue
                if job.maintype != 'kindle' and candidate.size > 32 * 1024 * 1024:
                    # the candidates for kindle, epubs, can get quite big
                    warning ('Skipping %s: file too big' % candidate.filename)
                    continue

                job.url = os.path.join (options.config.FILESDIR, candidate.filename)
                # allow any file below basedir of ebook
                job.include = [ os.path.join (
                    options.config.FILESDIR, os.path.dirname (candidate.filename) + '/*') ]
                job.max_depth = 3
                job.dc.source = urllib.parse.urljoin (options.config.PGURL, candidate.filename)
                job.dc.opf_identifier = (urllib.parse.urljoin (
                    options.config.BIBREC + '/', str (self.ebook)))

            if not needs_source or self.target_outdated (job, candidate):
                job_queue.append (job)

                new_candidate = Struct ()
                new_candidate.filename = os.path.join (job.outputdir, job.outputfile)
                new_candidate.format = job.type + '/unknown'
                new_candidate.mtime = datetime.datetime.now ()
                new_candidate.size = 0
                new_candidate.generated = True
                all_candidates.insert (0, new_candidate)

        return job_queue


def run_job_queue (job_queue):
    """ Run EbookMaker for all jobs in the queue. """

    for job in job_queue:
        try:
            os.mkdir (job.outputdir, 0o775)
        except OSError: # directory exists
            pass

    verbosity = ''
    if options.verbose:
        verbosity = '-' + 'v' * options.verbose

    try:
        ebm = subprocess.Popen (
            [
                options.config.EBOOKMAKER, verbosity,
                "--extension-package", "ebookconverter.writers",
                "--packager", "gzip",
                "--jobs", "no_such_url",
            ],
            stdin  = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
    except OSError as what:
        error ("%s %s" % (options.config.EBOOKMAKER, what))
        raise

    debug ("Calling Ebookmaker ...")
    stdout, stderr = ebm.communicate (cPickle.dumps (job_queue))
    debug ("Ebookmaker returned code: %d." % ebm.returncode)
    debug (stdout.decode (sys.stdout.encoding))
    debug (stderr.decode (sys.stderr.encoding))

    if ebm.returncode == 0:
        for job in job_queue:
            filename = os.path.join (job.outputdir, job.outputfile)
            Logger.ebook = job.ebook
            if os.access (filename, os.R_OK):
                if options.shadow:
                    debug ('if not in shadow, would have stored %s in database.' % filename)
                else:
                    job.dc.store_file_in_database (job.ebook, filename, job.type)
                mod_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
                if datetime.date.today() - mod_timestamp.date() > datetime.timedelta(1):
                    warning ('Failed to build new file: %s' % filename)
            elif filename.split('.')[-1] not in {'facebook', 'twitter', 'picsdir'}:
                error ('Failed to build file: %s' % filename)


def add_local_options (ap):
    """ Add local options to commandline. """

    ap.add_argument (
        '--version',
        action='version',
        version = "%%(prog)s %s" % VERSION
    )

    ap.add_argument (
        "--pidfile",
        metavar  = "FILE",
        dest     = "pidfile",
        action   = "store",
        default  = "/tmp/ebookconverter.pid",
        help     = "use pid file (default: /tmp/ebookconverter.pid)")

    ap.add_argument (
        "--make",
        metavar = "TYPES",
        dest    = "make",
        choices = CommonCode.add_dependencies (['everything'], DEPENDENCIES),
        default = [],
        action  = "append",
        help    = "types to make if source newer than target")

    ap.add_argument (
        "--build",
        metavar = "TYPES",
        dest    = "build",
        choices = CommonCode.add_dependencies (['everything'], DEPENDENCIES),
        default = [],
        action  = "append",
        help    = "types to make unconditionally")

    ap.add_argument (
        "--range",
        dest     = "range",
        default  = "",
        help     = "ebook range to convert: eg. 1,2-4,6,8-")

    ap.add_argument (
        "--goback",
        metavar = "HOURS",
        dest    = "goback",
        type    = int,
        default = 0,
        action  = "store",
        help    = "convert only ebooks younger than HOURS hours")

    ap.add_argument (
        "--top",
        metavar = "N",
        dest    = "top",
        type    = int,
        default = 0,
        action  = "store",
        help    = "convert only the N most-downloaded ebooks")

    ap.add_argument (
        "--jobs",
        metavar = "N",
        dest    = "jobs",
        type    = int,
        default = 1,
        action  = "store",
        help    = "send N ebooks per job to ebookmaker (default: 1)")

    ap.add_argument (
        "--fk-filetype",
        metavar = "TYPE",
        dest    = "fk_filetype",
        default = [],
        action  = "store",
        help    = "convert only books that have a file of this filetype eg rst or html")

    ap.add_argument (
        "-n", "--dry-run",
        dest    = "dry_run",
        action  = "store_true",
        help    = "don't actually run Ebookmaker; just print the commands.")

    ap.add_argument (
        "--shadow",
        dest    = "shadow",
        action  = "store_true",
        help    = "run, but don't change postgres.")

    ap.add_argument (
        "--stop",
        dest    = "stop_on_errors",
        action  = "store_true",
        help    = "stop immediately on errors.")


def fix_option_range (options, last_ebook):
    """ Convert a range from user input into list of ebook nos. """

    if not options.range:
        return

    res = []

    try:
        for value in options.range.split (','):
            r = value.split ('-')
            if len (r) == 2:
                r[0] = int (r[0]) if r[0] else 1
                if r[1] == '':
                    r[1] = last_ebook
                else:
                    r[1] = int (r [1])

                if r[0] > r[1]:
                    raise ValueError

                res.extend (range (r[0], r[1] + 1))
            elif len (r) == 1:
                res.append (int (value))
            else:
                raise ValueError

    except ValueError:
        raise ValueError ("error in range parameter")

    options.range = res


def pretty_print_list (list_of_ebook_nos):
    """ Return list of ebooks as pretty string. """

    result = []
    for dummy_k, group in itertools.groupby (
            enumerate (list_of_ebook_nos), lambda x: x[0] - x[1]):
        subrange = [str (g[1]) for g in group]
        if len (subrange) <= 2:
            result += subrange
        else:
            result.append ('%s-%s' % (subrange[0], subrange[-1]))
    return ' '.join (result)


def config ():
    """ Process config files and commandline params. """

    ap = argparse.ArgumentParser (prog = 'EbookConverter')
    CommonCode.add_common_options (ap, CONFIG_FILES[1])
    add_local_options (ap)
    CommonCode.set_arg_defaults (ap, CONFIG_FILES[1])

    global options 
    options.update(vars(CommonCode.parse_config_and_args (
        ap,
        CONFIG_FILES[0],
        {
            'proxies' : None,
            'logfile': None,
            'pgvpncmd': None,
            'ebookmaker': 'ebookmaker',
            'timestamp': datetime.datetime.today ().isoformat ()[:19],
        }
    )))

def grouper (iterable, n, fillvalue = None):
    """ Itertools recipe: Collect data into fixed-length chunks or blocks """
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest (*args, fillvalue = fillvalue)


def main ():
    """ Main program. """

    try:
        config ()
    except configparser.Error as what:
        error ("Error in configuration file: %s", str (what))
        return 1

    Logger.setup (Logger.LOGFORMAT, options.config.LOGFILE)
    Logger.set_log_level (options.verbose)
    if options.verbose >= 1 and options.config.LOGFILE:
        print ("Logging to: %s" % options.config.LOGFILE)

    debug ("Using config file: %s" % options.config_file)

    # write pidfile
    try:
        fd = os.open (options.pidfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        debug ("Writing pid file")
        os.write (fd, ("%d\n" %  os.getpid ()).encode ('us-ascii'))
        os.close (fd)
    except OSError:
        info ("Not running: pidfile exists.")
        print ("Not running: pidfile %s exists." % options.pidfile)
        sys.exit (2)

    info ("Program start")

    # find last book no.
    GutenbergDatabase.DB = GutenbergDatabase.Database ()
    GutenbergDatabase.DB.connect ()
    cursor = GutenbergDatabase.DB.get_cursor ()
    cursor.execute ('select max (pk) as last from books')
    row = cursor.fetchone ()
    last_ebook = int (row[0])
    debug ("Last ebook: #%d" % last_ebook)
    fix_option_range (options, last_ebook)

    if options.goback:
        cursor.execute ("SELECT distinct fk_books from files "
                        "where filename !~ '^cache/' and "
                        "filemtime >= now () - interval '%d hours'"
                        % options.goback)
        pks = set ([row[0] for row in cursor.fetchall ()])
        pks = pks.intersection (options.range)
        options.range = sorted (pks)

    if options.top:
        cursor.execute ("SELECT pk from books order by downloads desc limit %d" % options.top)
        pks = set ([row[0] for row in cursor.fetchall ()])
        pks = pks.intersection (options.range)
        options.range = sorted (pks)

    if options.fk_filetype:
        cursor.execute ("SELECT distinct fk_books from files "
                        "where filename !~ '^cache/' and "
                        "fk_filetypes = %(fk_filetype)s",
                        { 'fk_filetype' : options.fk_filetype })
        pks = set ([row[0] for row in cursor.fetchall ()])
        pks = pks.intersection (options.range)
        options.range = sorted (pks)

    info ("Processing %d ebooks" % len (options.range))
    info ("Processing ebooks: %s" % pretty_print_list (options.range))

    if options.goback:
        # make sure the books just posted get done first
        options.range.sort (reverse = True)

    options.make += options.build

    options.make  = CommonCode.add_dependencies (options.make,  DEPENDENCIES, BUILD_ORDER)
    options.build = CommonCode.add_dependencies (options.build, DEPENDENCIES, BUILD_ORDER)

    info ("Making:   %s" % " ".join (options.make))
    info ("Building: %s" % " ".join (options.build))

    done_books  = 0

    try:
        for group in grouper (options.range, options.jobs):
            job_queue = []
            last = 0
            progress = done_books * 100 // len (options.range)
            info ("Progress: %d%% done", progress)

            for ebook in group:
                if ebook is None:
                    break
                Logger.ebook = last = ebook

                dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore (
                    DummyConnectionPool.ConnectionPool ())

                try:
                    dc.load_from_database (ebook)
                except Exception:
                    exception ("Error getting DublinCore info.")
                    continue

                if dc.project_gutenberg_id is None:
                    warning ("No ebook #%d (trying to get DublinCore info).", ebook)
                    continue

                maker = Maker (ebook, dc)

                try:
                    job_queue += maker.mk_job_queue ()
                except Exception as what:
                    # report errors, but keep going
                    exception (what)
                    if options.stop_on_errors:
                        return 1

                done_books += 1

            # send up group
            if options.dry_run:
                info ("Job list for #%d - #%d (%d jobs)" % (group[0], last, len (job_queue)))
                print ('*' * 80)
                for job in job_queue:
                    print (job)
                    print ('*' * 80)
            else:
                info ("Calling ebookmaker for #%d - #%d (%d jobs)" %
                      (group[0], last, len (job_queue)))
                setproctitle.setproctitle (
                    "Converting Project Gutenberg #%d - #%d (%d%%)" %
                    (group[0], last, progress)
                )
                run_job_queue (job_queue)


    except KeyboardInterrupt as what:
        # also triggered by: kill -INT (or: kill -2)
        error ("User interrupt")
        return 1

    finally:
        os.remove (options.pidfile)

    setproctitle.setproctitle ("Cleaning Up")
    info ("Program end")
    logging.shutdown ()

    return 0


if __name__ == "__main__":
    sys.exit (main ())
