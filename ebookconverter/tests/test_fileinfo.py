#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import unittest
from pathlib import Path

from libgutenberg.DBUtils import author_exists, ebook_exists, remove_ebook, check_session
from libgutenberg.GutenbergFiles import remove_file_from_database
from libgutenberg.Models import File

from .. import FileInfo, Notifier

class TestFileInfo(unittest.TestCase):
    def setUp(self):
        self.test_file = os.path.join(os.path.dirname(__file__),'4554-h.htm')
        self.test_file2 = os.path.join(os.path.dirname(__file__),'4554.txt')
        self.test_file3 = os.path.join(os.path.dirname(__file__),'4554-0.txt')
        self.test_fakebook = os.path.join(os.path.dirname(__file__),'99999-h.htm')
        self.test_fakebook_json = os.path.join(os.path.dirname(__file__),'99999.json')

    def test_scan_file(self):
         result = FileInfo.scan_file(self.test_file, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file2, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file3, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file3, 99999)
         self.assertNotEqual(result, 99999)

    def test_save_metadata(self):
        result = FileInfo.scan_file(self.test_fakebook, 99999)
        self.assertTrue(result)
        self.assertTrue(ebook_exists(99999))
        self.assertTrue(author_exists("Lorem Ipsum Jr."))
        remove_ebook(99999)
        self.assertFalse(ebook_exists(99999))
        self.assertTrue(author_exists("Hemingway, Ernest"))

    def test_scan_dopush(self):
        # set up
        Path(os.path.join(FileInfo.DOPUSH_LOG_DIR, '99999.zip.trig')).touch()
        Path(os.path.join(FileInfo.DOPUSH_LOG_DIR, '4554.zip.trig')).touch()
        shutil.copy(self.test_fakebook_json, 
            os.path.join(FileInfo.WORKFLOW_LOG_DIR, '99999.json'))
        if not os.path.exists(os.path.join(FileInfo.FILES, '4554')):
            os.mkdir(os.path.join(FileInfo.FILES, '4554'))
        if not os.path.exists(os.path.join(FileInfo.FILES, '99999')):
            os.mkdir(os.path.join(FileInfo.FILES, '99999'))
        shutil.copy(self.test_file, os.path.join(FileInfo.FILES, '4554'))
        shutil.copy(self.test_fakebook, os.path.join(FileInfo.FILES, '99999'))
        session = check_session(None)
        
        nfiles_test = session.query(File.id).filter_by(fk_books=4554).count()
        self.assertTrue(nfiles_test > 0)
        nfiles_fake = session.query(File.id).filter_by(fk_books=99999).count()
        self.assertEqual(nfiles_fake, 0)

        # test the scanning
        FileInfo.scan_dopush_log()
        
        # verify
        self.assertTrue(ebook_exists(99999))
        self.assertTrue(session.query(File.id).filter_by(fk_books=99999).count() > 0)
        self.assertTrue(session.query(File.id).filter_by(fk_books=4554).count() > nfiles_test)
        

        # clean up
        os.remove(os.path.join(FileInfo.WORKFLOW_LOG_DIR, 'backup', '99999.json'))
        os.remove(os.path.join(FileInfo.DOPUSH_LOG_DIR, 'backup', '99999.zip.trig'))
        os.remove(os.path.join(FileInfo.DOPUSH_LOG_DIR, 'backup', '4554.zip.trig'))
        os.remove(os.path.join(FileInfo.FILES, '4554', '4554-h.htm'))
        os.remove(os.path.join(FileInfo.FILES, '99999', '99999-h.htm'))
        remove_file_from_database(os.path.join(FileInfo.FILES, '4554', '4554-h.htm'),
            session=session)
        remove_ebook(99999, session=session)
        self.assertTrue(session.query(File.id).filter_by(fk_books=99999).count() == 0)
        self.assertTrue(session.query(File.id).filter_by(fk_books=4554).count() == nfiles_test)
        
    def tearDown(self):        
        remove_file_from_database(os.path.join(FileInfo.FILES, '4554', '4554-h.htm'))

