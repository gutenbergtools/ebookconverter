'''export a CSV file '''

import csv
import gzip
import os
import shutil


from libgutenberg import GutenbergDatabase
from libgutenberg.DublinCoreMapping import DublinCoreObject
from libgutenberg.Models import Book


FEEDS = os.getenv ('FEEDS') or ''
CSV_FN = 'pg_catalog.csv'
OB = GutenbergDatabase.Objectbase(False)

def books():
    yield ['Text#', 'Type', 'Issued', 'Title', 'Language', 'Authors',
           'Subjects', 'LoCC', 'Bookshelves',]
    session = OB.get_session()
    booknums = session.query(Book.pk).where(Book.pk < 99999).order_by(Book.pk).all()
    for booknum in booknums:
        dc = DublinCoreObject()
        dc.load_from_database(booknum[0])
        if not dc.book:
            continue
        row = [dc.book.pk,
               '; '.join([dcmitype.id for dcmitype in dc.dcmitypes]),
               dc.book.release_date.isoformat(),
               dc.title,
               '; '.join([lang.id for lang in dc.languages]),
               '; '.join([dc.format_author_date_role(author) for author in dc.authors]),
               '; '.join([subject.subject for subject in dc.subjects]),
               '; '.join([locc.id for locc in dc.loccs]),
               '; '.join([shelf.bookshelf for shelf in dc.bookshelves]),
              ]
        yield row


def main():
    fn = os.path.join(FEEDS, CSV_FN)
    with open(fn, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        for row in books():
            csvwriter.writerow(row)
    with open(fn, 'rb') as f_in:
        with gzip.open(fn + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
