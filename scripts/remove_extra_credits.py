from libgutenberg.Models import Attribute, Book
from libgutenberg import GutenbergDatabase
OB = GutenbergDatabase.Objectbase(False)
session = OB.get_session()

for book in session.query(Book):
    credits = []
    longest = 0
    for att in book.attributes:
        if att.fk_attriblist == 508:
            if att.text.startswith('Updated:'):
                print(f'deleting {book.pk}: {att.text}')
                session.query(Attribute).where(Attribute.pk == att.pk).delete()
                session.commit()
            else:
                credits.append(att)
                longest = max(longest, len(att.text))
    if len(credits) > 1:
        for att in credits:
            if len(att.text) < longest:
                session.query(Attribute).where(Attribute.pk == att.pk).delete()
                session.commit()
            else:
                text = att.text
        print(f'{book.pk}: {text}')