#!/usr/bin/env python
''' test for Notifier '''
import datetime
import unittest

from .. import Notifier

class TestNotifier(unittest.TestCase):
    def setUp(self):
        self.notify_email = 'eric@hellman.net'

    def test_add_2emails(self):
        Notifier.ADDRESS_BOOK.add_email(99999, self.notify_email)
        self.assertTrue(self.notify_email in
            Notifier.ADDRESS_BOOK.address_book.get('99999', []))
        Notifier.ADDRESS_BOOK.add_email(99999, 'eric@gluejar.com')
        self.assertTrue(len(Notifier.ADDRESS_BOOK.address_book.get('99999', [])) > 1)

    def test_add_new_email(self):
        try:
            del Notifier.ADDRESS_BOOK.address_book[99999]
        except KeyError:
            pass
        Notifier.ADDRESS_BOOK.add_email(99999, self.notify_email)
        Notifier.ADDRESS_BOOK.add_email(99999, self.notify_email)
        self.assertTrue('eric@hellman.net' in
            Notifier.ADDRESS_BOOK.address_book.get('99999', []))

    def test_notify_queue(self):
        ''' notifications to an unused ebook number should save in queue
            #199 is a reserved ebook number '''
        message =  "Message sent %s" % datetime.date.today().isoformat()
        Notifier.notify(199, message)
        archive_file = '{}/{}.messages'.format(Notifier.ARCHIVE_DIR, 199)
        with open(archive_file, 'r') as messagefile:
            messages = messagefile.read()
            self.assertTrue(message in messages)
