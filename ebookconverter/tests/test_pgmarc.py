#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import subprocess

FEEDS = os.getenv ('FEEDS')  or ''
MARCFILE = os.path.join(FEEDS, 'pgmarc.mrc')
MARCXMLFILE = os.path.join(FEEDS, 'pgmarc.xml')    


class TestMarc(unittest.TestCase):

    def test_10(self):
        cmd = 'pipenv run python -m ebookconverter.PGMarc 31105 31115'

        output = subprocess.check_output(cmd, shell=True)

        self.assertFalse(output)
        for out in [MARCFILE, MARCXMLFILE]:
            self.assertTrue(os.path.exists(out))
            os.remove(out)
