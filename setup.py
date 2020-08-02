#
# ebookconverter distribution
#

from setuptools import setup

VERSION = '0.6.8'

setup (
    name = 'ebookconverter',
    version = VERSION,

    packages = [
        'ebookconverter',
        'ebookconverter.writers',
    ],

    scripts = [
        'scripts/ebookconverter',
        'scripts/autodelete',
        'scripts/fileinfo',
        'scripts/cron-rebuild-files.sh',
        'scripts/cron-dopush-social.sh',
        'scripts/cron-dopush.sh',
    ],

    install_requires = [
        'ebookmaker>=0.8.2',
        'setproctitle==1.1.10',
        'requests_oauthlib>=1.2.0',
        'rdflib>=4.2.2',
        'qrcode>=6.1',
        'libgutenberg[postgres]>=0.6.2',
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
