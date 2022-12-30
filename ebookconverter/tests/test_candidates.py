#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest


from .. import Candidates
from ebookconverter.EbookConverter import PREFERRED_INPUT_FORMATS

class TestCandidates(unittest.TestCase):
    def setUp(self):
        self.ebook = 4554
        self.ebook2 = 9846

    def test_read_from_database(self):
        candidates = Candidates.Candidates()
        result = candidates.read_from_database(self.ebook)
        self.assertTrue(len(result) > 2)

    def test_filter_sort(self):
        typeglob_list = PREFERRED_INPUT_FORMATS['html.images']
        candidates = Candidates.Candidates()
        files = candidates.read_from_database(self.ebook2)
        cf = Candidates.Candidates.filter_sort(typeglob_list, files, lambda x: x.format)
        self.assertEqual(cf[0].archive_path, 'files/9846/9846-h/9846-h.htm')
