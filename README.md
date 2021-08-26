# ebookconverter
code that orchestrates ebook conversion for project gutenberg


EbookConverter manages the creation and update of ebook assets for Project Gutenberg. It uses a postgres database to keep track of both ebook metadata and ebook files. the postgress database is managed by the libgutenberg package.

The cron-rebuild-files.sh script runs as a cron job, rebuilding 2100 books per day, so as to rebuild every book roughly once a month.

ebookconverter talks to the gutenberg database to build a list of ebookmaker jobs. These jobs require some metadata about the book, and a target file to process.

ebookconverter expects source files to be in numbered directories in a 'files' directory. The location of the files directory is given by the FILESDIR config parameter.

Config parameters should be set in a file at /etc/ebookconverter.conf or ~/.ebookconverter

ebookconverter has been tested on Python 3.6.7. It's not expected to run on python 2.7

## Installing

`pipenv install ebookconverter`

The following directories should exist:
    - $PRIVATE/logs
    - $PRIVATE/logs/json
    - $PRIVATE/logs/json/backup
    - $PRIVATE/logs/notifications
    - $PRIVATE/logs/dopush
    - $PRIVATE/logs/dopush/backup
