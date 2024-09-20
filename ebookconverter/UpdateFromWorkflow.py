#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""
UpdateFromWorkflow.py

Copyright 2022 by Eric Hellman and Project Gutenberg
Distributable under the GNU General Public License Version 3 or newer.
scans the backup folder and adds possibly unloaded data.
"""

import os
import json
import re
import stat

from libgutenberg import Logger
from libgutenberg.DublinCore import handle_dc_languages
from libgutenberg.DublinCoreMapping import DublinCoreObject
from libgutenberg.GutenbergGlobals import Struct

from ebookconverter.FileInfo import get_workflow_file, WORKFLOW_LOG_DIR, archive_workflow_file

WORKFLOW_BACKUP_DIR = os.path.join(WORKFLOW_LOG_DIR, 'backup')


def update_from_workflow(dc, record):
    # check if there's a pubinfo, if so, don't update it.
    has_pubinfo = dc.pubinfo and bool(
        dc.pubinfo.publisher or dc.pubinfo.country or dc.pubinfo.years)
    changed = False
    if not has_pubinfo and (not dc.languages or dc.languages[0].id == 'en'):
        set_lang = record.get('LANGUAGE', None)
        if set_lang:
            handle_dc_languages(dc, set_lang)
            changed = True
    if not has_pubinfo:
        dc.pubinfo.publisher = record.get('PUBLISHER', None)
        changed = changed or bool(dc.pubinfo.publisher)
        dc.pubinfo.country = record.get('PUBLISHER_COUNTRY', None)
        changed = changed or bool(dc.pubinfo.country)
        value = record.get('SOURCE_PUBLICATION_YEARS', None)
        if value:
            value = [value] if isinstance(value, str) else value
            if isinstance(value, list):
                for event_year in value:
                    if ':' in event_year:
                        [event, year] = event_year.split(':')
                        dc.pubinfo.years.append((event, year))
                    elif event_year:
                        dc.pubinfo.years.append(('copyright', year))
                changed = True
    if not dc.scan_urls:
        value = record.get('SCANS_ARCHIVE_URL', None)
        if value:
            if isinstance(value, str):
                value = [value]
            if isinstance(value, list):
                for scan_url in value:
                    dc.scan_urls.add(scan_url)
                changed = True
    if not dc.request_key:
        dc.request_key = record.get('REQUEST_KEY', None)
        changed = changed or bool(dc.request_key)
    if not dc.credit:
        dc.credit = record.get('CREDIT', None)
        changed = changed or bool(dc.credit)
    if changed:
        dc.save(updatemode=1)
        Logger.info('updated #%s', dc.project_gutenberg_id)


def main():
    Logger.setup(Logger.LOGFORMAT, 'fileinfo.log')
    Logger.set_log_level(2)

    for filename in sorted(os.listdir(WORKFLOW_LOG_DIR)):
        workflow_file = os.path.join(WORKFLOW_LOG_DIR, filename)
        mode = os.stat(workflow_file)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            continue
        ebook_num = 0
        m = re.match(r'^(\d+)\.json$', filename)
        if m:
            ebook_num = int(m.group(1))
            Logger.ebook = ebook_num
        else:
            continue

        with open(workflow_file, 'r') as fp:
            wf_data = fp.read()
        data = json.loads(wf_data)
        record = data['DATA']

        dc = DublinCoreObject()
        dc.load_from_database(ebook_num)
        if dc.book:
            update_from_workflow(dc, record)
        archive_workflow_file(workflow_file)

if __name__ == '__main__':
    main()
