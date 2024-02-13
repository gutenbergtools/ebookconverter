import os
import datetime
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv('SMTP_HOST') or 'localhost'
SMTP_USER = os.getenv('SMTP_USER') or ''
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD') or ''
REPLY_TO_EMAIL = os.getenv('REPLY_TO_EMAIL') or 'help2024@pglaf.org'
SMTP_SSL = os.getenv('SMTP_SSL') or False


def test_email():
    message = 'test message at %s' % datetime.datetime.now().isoformat()
    try:
        if SMTP_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST)
        else:
            server = smtplib.SMTP(SMTP_HOST)
        if SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = "test email"
        msg['From'] = REPLY_TO_EMAIL
        msg['To'] = 'eric@hellman.net'
        server.send_message(msg)
        server.quit()
        return 2
    except ConnectionError as e:
        print(e)
        return 0

test_email()