# About Project Gutenberg MARC records

Project Gutenberg has reconstituted their MARC record service.  Records are available in MARC and MARCXML at https://gutenberg.org/cache/epub/feeds/

MARC records are the _lingua franca_ of library catalogs. Libraries can import these records, modify them, filter them, redistribute them and display them to patrons looking for free, digital versions of classic books, almost all of them in the public domain, all of them free to read and use.

Project Gutenberg welcomes corrections and errata for its data. (https://gutenberg.org/help/errata.html). For questions specific to MARC records, please email Ray Schwartz (schwartz@panix.com), who worked with Eric Hellman of the Free Ebook Foundation (eric@ebookfoundation.org) to make this a reality. If you would like to make corrections or suggestions for the generating code, the repo is https://github.com/schwartzray/Project-Gutenberg-MARC/ 

Of course none of this would be possible without the close collaboration of Project Gutenberg and its volunteers, who, over the course of many years, have built the up the database that powers the Project Gutenberg website and these MARC records. We are grateful for advice and suggestions from the larger community of library cataloguers.

_____________________


The MARC record extract is generated weekly from the Project Gutenberg Postgres database. This process uses a python script which recreates each MARC record from the entire collection of titles, excluding non-textual titles such as maps, audio files, data sets and so on.

## Summary on Cataloging Decisions Made.

### Description 2xx-5xx
(plus note on 008)

Of the 73,000 records, 63,000 do not have data for a 260 or 264 MARC tag (nor is there a publication year). The option we decided upon is to use the 264 with the `1` indicator

`264 \1$aSalt Lake City, UT :$bProject Gutenberg,$c2005`

For the titles with no publication data, a 534 note is added.

`534 \$nOriginal publication data not identified`

For those titles that DO have original publication data, this 534 would be added.

`534 \$pOriginally published:$cTokyo, Baifukan, 1955`

The fixed field would be treated as so: 

Use both dates in the 008 - original publication and PG release date.

For publications that PG does have the original date
```
008/06 - r
008/07-10 - 2005
008/11-14 - 1955
```
For publications that PG does NOT have the original date
```
008/06 - r
008/07-10 - 2005
008/11-14 - uuuu
```
There is no physical description of the item in the database.  We are using the MARC RDA tags.
```
300 \$a1 online resource :$bmultiple file formats
336 \$atext$btxt$2rdacontent
337 \$acomputer$bc$2rdamedia
338 \$aonline resource$bcr$2rdacarrier
```
Any series statements are tagged with 490 and added an 830.

### Access Points 1xx, 6xx, 7xx
The authors in the database are not delineated by personal, corporate or meeting names.  Neither is there any indication that whether the personal name is a forename or a surname.  Since the vast majority are personal surnames, We assigned MARC tags 100 and 700 to all authors regardless of author type.  Also, the 1st indicator is set at 1 for surname for all records.   Needless to say, this is far from ideal.  The database does have separate fields for birth and death dates and we were able to assign them to `$d`.  The Fuller Form of Name is in the name field but the script will assign a `$q` before the opening parenthesis.  

Subject headings are assigned to the records, but there is no distinction in the database as to which headings are LCSH, personal name, corporate name, or geographic name. In addition, they are not broken down by subfield—such as `$y - Chronological subdivision or $v - Form subdivision`, they are a continuous string of text (e.g., `\$aAmerican literature -- 19th century – Periodicals`). So, we decided to use 653 (uncontrolled index term) instead of 650/600/610/651.

### Fixed Fields
006 is `m` - Computer file/Electronic resource

007 is `cr n` (c - Electronic resource, r - Remote, n - Not applicable)

008 – For date, we used `r` in position 6 then 7-10 for the Gutenberg's release date. If original publication date is available, then code it in 11-14. For position 23, we used `o` for online. We are not coding for language in 008, because the database is not coded with MARC lang codes. Rather the database includes language codes in ISO639-1—so we use MARC tag 041 instead. Position 39 cataloging source `d` - Other.
