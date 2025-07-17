# script for deleting a book from the pg database


import sys

from libgutenberg.Models import  Book, File
from libgutenberg import GutenbergDatabase

OB = GutenbergDatabase.Objectbase(False)
session = OB.get_session()

def forget_book(pg_id):
    try:
        pg_id = int(pg_id)
    except ValueError:
        print('[pg_id] must be an integer')
        exit()
    book = session.query(Book).where(Book.pk == pg_id).first()
    if book == None:
        print(f'book {pg_id} does not exist')
        exit()
    book.loccs = []
    book.subjects = []
    book.categories = []
    book.bookshelves = []
    book.langs = []
    book.authors = []
    files = session.query(File).where(File.fk_books == pg_id).delete()
    session.delete(book)
    session.commit()
    

def main():
    try:
        if len(sys.argv) == 2:
            pg_id = sys.argv[1]
            forget_book(pg_id)
        else:
            print('syntax: python -m ebookconverter.forget_book [pg_id] ')
            exit()
    except Exception as e:
        print(f'problems forgetting book {pg_id}: {e}')
        exit()
    print(f'book {pg_id} has been successfully forgotten')

# boilerplate for main method
if __name__ == '__main__':
    main ()
