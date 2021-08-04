#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest

from libgutenberg.DBUtils import author_exists, ebook_exists, remove_ebook

from .. import FileInfo

class TestFileInfo(unittest.TestCase):
    def setUp(self):
        self.test_file = os.path.join(os.path.dirname(__file__),'4554-h.htm')
        self.test_file2 = os.path.join(os.path.dirname(__file__),'4554.txt')
        self.test_file3 = os.path.join(os.path.dirname(__file__),'4554-0.txt')
        self.test_fakebook = os.path.join(os.path.dirname(__file__),'99999-h.htm')

    def test_scan_file(self):
         result = FileInfo.scan_file(self.test_file, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file2, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file3, 4554)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file3, 99999)
         self.assertFalse(result)

    def test_save_metadata(self):
        result = FileInfo.scan_file(self.test_fakebook, 99999)
        self.assertTrue(result)
        self.assertTrue(ebook_exists(99999))
        self.assertTrue(author_exists("Lorem Ipsum Jr."))
        remove_ebook(99999)
        self.assertFalse(ebook_exists(99999))
        self.assertTrue(author_exists("Hemingway, Ernest"))

