#
# ebookconverter distribution
#

from setuptools import setup

VERSION = '0.8.6'

setup (
    name = 'ebookconverter',
    version = VERSION,

    packages = [
        'ebookconverter',
        'ebookconverter.writers',
    ],

    scripts = [
        'scripts/autodelete',
        'scripts/ebookconverter',
        'scripts/fileinfo',
        'scripts/make_csv',
        'scripts/reload_workflow',
        'scripts/update_from_backup_workflow',
        'scripts/cron-rebuild-files.sh',
        'scripts/cron-dopush-social.sh',
        'scripts/cron-dopush.sh',
        'scripts/cron-jekyll.sh',
    ],

    install_requires = [
        'ebookmaker>=0.12.30',
        'setproctitle==1.1.10',
        'requests_oauthlib>=1.2.0',
        'rdflib>=4.2.2',
        'qrcode>=6.1',
        'libgutenberg[postgres]>=0.10.15',
    ],
    
    package_data = {
    },

    data_files = [
        ('', ['CHANGES', 'README.md']),
    ],

    # metadata for upload to PyPI

    author = "Eric Hellman",
    author_email = "eric@hellman.org",
    description = "The Project Gutenberg tool to orchestrate ebook generation.",
    long_description = open ('README.md').read(),
    license = "GPL v3",
    url = "https://github.com/gutenbergtools/ebookconverter/",

    classifiers = [
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Intended Audience :: Other Audience",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
    ],

    platforms = 'OS-independent'
)
