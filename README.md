# ebookconverter
code that orchestrates ebook conversion for project gutenberg


EbookConverter manages the creation and update of ebook assets for Project Gutenberg. It uses a postgres database to keep track of both ebook metadata and ebook files. the postgress database is managed by the libgutenberg package.

The cron-rebuild-files.sh script runs as a cron job, rebuilding 2100 books per day, so as to rebuild every book roughly once a month.

ebookconverter talks to the gutenberg database to build a list of ebookmaker jobs. These jobs require some metadata about the book, and a target file to process.

ebookconverter expects source files to be in numbered directories in a 'files' directory. The location of the files directory is given by the FILESDIR config parameter.

Config parameters should be set in a file at /etc/ebookconverter.conf or ~/.ebookconverter

ebookconverter has been tested on Python 3.9.

## Installing

`pipenv install ebookconverter`

The following directories should exist:
    - $PRIVATE/logs
    - $PRIVATE/logs/json
    - $PRIVATE/logs/json/backup
    - $PRIVATE/logs/notifications
    - $PRIVATE/logs/dopush
    - $PRIVATE/logs/dopush/backup

## Using the EbookConverter Scripts

you can run these commands either by first entering a `pipenv shell` or on a single line using `pipenv run <command> <args>`

Rebuild one or more books
`ebookconverter --range=<start>-<finish> --build=all`
`ebookconverter --range=<booknumber>  --build=all`
`ebookconverter --range=<booknumber>  --build=all --validate`

Reload metadata from a workflow json file (use with care, it will overwrite any metadata in the DB)
`reload_workflow <booknumber>`

Regenerate the csv file
`make_csv`

Look for any ebooks with changed files in the last X days and then check if any of the previously known files of that ebook have been deleted.

`autodelete`