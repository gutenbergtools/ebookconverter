#!/usr/bin/env python
''' test for Notifier '''
import datetime
import os
import unittest

from libgutenberg import Logger
from libgutenberg.CommonOptions import options
from ebookmaker import CommonCode
from .. import Notifier

class TestNotifier(unittest.TestCase):
    def setUp(self):
        self.notify_email = 'eric@hellman.net'
        self.ww_email = 'eric@gluejar.com'

    def test_add_ww(self):
        Notifier.ADDRESS_BOOK.set_email(99999, self.notify_email, role='ww')
        self.assertEqual(self.notify_email,
            Notifier.ADDRESS_BOOK.get_email('99999', role='ww'))

    def test_add_2emails(self):
        Notifier.ADDRESS_BOOK.set_email(99999, self.notify_email)
        self.assertEqual(self.notify_email,
            Notifier.ADDRESS_BOOK.get_email('99999'))
        Notifier.ADDRESS_BOOK.set_email(99999, self.ww_email)
        self.assertEqual(Notifier.ADDRESS_BOOK.get_email('99999'), self.ww_email)
        Notifier.ADDRESS_BOOK.set_email(99999, self.notify_email, role='ww')
        self.assertEqual(Notifier.ADDRESS_BOOK.get_email('99999', role='ww'), self.notify_email)


    def test_notify_queue(self):
        """
            notifications to an unused ebook number should save in queue
            199 is a reserved ebook number
        """
        message =  "Message sent %s" % datetime.date.today().isoformat()
        Notifier.notify(199, message)
        archive_file = '{}/{}.messages'.format(Notifier.ARCHIVE_DIR, 199)
        with open(archive_file, 'r') as messagefile:
            messages = messagefile.read()
            self.assertTrue(message in messages)

    def test_log_notifier(self):
        Logger.notifier = CommonCode.queue_notifications
        Logger.setup(Logger.LOGFORMAT)
        Logger.ebook = 99999
        Notifier.ADDRESS_BOOK.set_email(99999, self.notify_email)
        Notifier.ADDRESS_BOOK.set_email(99999, self.ww_email, role='ww')
        Logger.critical('testing the notifier')
        message_file = os.path.join(Notifier.NOTIFICATION_DIR, '99999.txt')
        self.assertTrue(os.path.exists(message_file))
        Notifier.send_notifications()
        if Notifier.SMTP_USER:
            self.assertFalse(os.path.exists(message_file))
