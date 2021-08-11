#!/usr/bin/env python3
"""
Allows etext-specific messages to be sent to an address registered for that etext.

uses a json file to save notification addresses.


"""

from datetime import datetime
import json
import os
import smtplib

from email.message import EmailMessage

from libgutenberg.Logger import debug, error, info, warning

PRIVATE = os.getenv('PRIVATE') or ''
NOTIFY_FILE = os.path.join(PRIVATE, 'logs', 'json', 'notify.json')
ARCHIVE_DIR = os.path.join(PRIVATE,'logs', 'json', 'backup')
SMTP_SERVER = os.getenv('SMTP_SERVER') or 'localhost'
REPLY_TO_EMAIL = os.getenv('REPLY_TO_EMAIL') or 'webmaster@gutenberg.org'

class AddressBook:
    def __init__(self):
        self.address_book = {}
        try:
            with open(NOTIFY_FILE, 'r') as json_file:
                self.address_book = json.loads(json_file.read())
        except FileNotFoundError:
            error('could not find %s', NOTIFY_FILE)

    def add_email(self, ebook, email):
        try:
            ebook = str(int(ebook))
        except ValueError:
            return False
        if ebook in self.address_book:
            addresses = self.address_book[ebook]
        else:
            addresses = []
            self.address_book[ebook] = addresses
        if email not in addresses:
            addresses.append(email)
        return True

    def get(self, ebook):
        try:
            ebook = str(int(ebook))
        except ValueError:
            return []
        return self.address_book.get(ebook, [])


    def __del__(self):
        """ save the data before destroying the object """
        print('dumping ' + NOTIFY_FILE)
        with open (NOTIFY_FILE, 'w+') as json_file:
            json.dump(self.address_book, json_file)

ADDRESS_BOOK = AddressBook()

def notify(ebook, message, subject='Gutenberg backend notification'):
    addresses = ADDRESS_BOOK.get(ebook)
    if not addresses:
        message_archive = '{}/{}.messages'.format(ARCHIVE_DIR, ebook)
        now = datetime.now().isoformat()
        with open(message_archive, 'a+') as messagefile:
            messagefile.write('Unsent: %s\n%s\n' % (now, message))
        return

    server = smtplib.SMTP(SMTP_SERVER)
    for email in addresses:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = REPLY_TO_EMAIL
        msg['To'] = email
        server.send_message(msg)
    server.quit()
