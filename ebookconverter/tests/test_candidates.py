#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest


from .. import Candidates

class TestCandidates(unittest.TestCase):
    def setUp(self):
        self.ebook = 4554

    def test_read_from_database(self):
        candidates = Candidates.Candidates()
        result = candidates.read_from_database(self.ebook)
        self.assertTrue(len(result) > 2)

    def test_filter_sort(self):
        typeglob_list = ('html/utf-8', 'html/iso-8859-*', 'html/*', '*/*')
        candidates = Candidates.Candidates()
        files = candidates.read_from_database(self.ebook)
        Candidates.Candidates.filter_sort(typeglob_list, files, lambda x: x.format)
