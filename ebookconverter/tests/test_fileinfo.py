#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest


from .. import FileInfo

class TestFileInfo(unittest.TestCase):
    def setUp(self):
        self.test_file = os.path.join(os.path.dirname(__file__),'4554-h.htm')
        self.test_file2 = os.path.join(os.path.dirname(__file__),'4554.txt')
        self.test_file3 = os.path.join(os.path.dirname(__file__),'4554-0.txt')

    def test_scan_file(self):
         result = FileInfo.scan_file(self.test_file)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file2)
         self.assertTrue(result)
         result = FileInfo.scan_file(self.test_file3)
         self.assertTrue(result)

