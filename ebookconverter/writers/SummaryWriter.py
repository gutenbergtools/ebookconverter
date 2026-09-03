#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

# Writes a short summary of a book into the database (attribute 520).
#
# Process per book:
#   1. Book already has a Wikipedia-based summary  -> leave it alone, do nothing.
#   2. Book has no summary at all                  -> look for a Wikipedia article
#      (stored link, else Google search validated by Claude) and use its intro.
#   3. Otherwise (no summary and no Wikipedia hit, or an existing summary that was
#      made from the book text) -> feed the entire book to a large-context model.
#      Books too long even for that are skipped, leaving whatever summary exists.
# Read the prompts in Prompts.py for a better understanding of step 3.

# One thing to realise is that what we're looking to put on the Gutenberg page is not
# an exhaustive summary of all the content of a book, but rathern an impression of it
# so that users can decide whether try a book or not. Kind of like a trailer to a movie.
# In that sense "summary" is not actually a very accurate term.

# Provenance is encoded by a sentence appended to the stored summary text:
#   LLM_TAG    " (This is an automatically generated summary.)"  composed by AI
#   WIKI_TAG   " (This summary is from Wikipedia.)"              taken from Wikipedia
#   EDITED_TAG " (Summary by Project Gutenberg staff.)"          written by us
# Caveat: WIKI_TAG is recent. Older Wikipedia-based summaries carry LLM_TAG, so the
# reliable sign of a Wikipedia origin is a 500-field note starting with WIKI_CAPTION
# ('Wikipedia page about this book: <url>'), which has always been written alongside.


import os
import requests
import re

from sqlalchemy import and_
from urllib.parse import unquote

from libgutenberg.GutenbergDatabase import DatabaseError
from libgutenberg.Logger import exception, error, info, warning
from libgutenberg.Models import Attribute, Book
from ebookmaker.writers import TxtWriter
from ebookmaker.parsers.boilerplate import strip_headers_from_txt
from ebookconverter.writers.Prompts import WholeBook, WikipediaValidator

from openai import OpenAI
import anthropic

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=4)
OPENAI_MODEL = "gpt-5.6-luna"
# Skip books longer than this (~750k tokens at ~4 chars/token, under the model's 1M-token
# context). Very few books are affected; they keep whatever summary they already have.
MAX_INPUT_CHARS = 3_000_000

anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

# the prompt asks for 80-90 words; anything much shorter is a refusal or an error, not a summary
MIN_SUMMARY_WORDS = 40
AVOID_WIKI = ["simple.", "File:", "/Category:", "(disambiguation)"]

LLM_TAG = " (This is an automatically generated summary.)"
WIKI_TAG = " (This summary is from Wikipedia.)"
EDITED_TAG = " (Summary by Project Gutenberg staff.)"
WIKI_CAPTION = 'Wikipedia page about this book'
WIKIMATCH = re.compile(r"(?ix)https?://([a-z]{2,3})\.wikipedia\.org/wiki/([/!@i^*$a-z0-9_\(\)-]+)")

def is_non_text(book):
    """True for audio, images, data etc. that have no text to summarise."""
    return book.categories != []

class Writer (TxtWriter.Writer):
    """ Summary Writer Class. """

    def __init__(self):
        super (Writer, self).__init__ ()
        self.wiki_request_headers = {
            "User-Agent": "Project-Gutenberg-Summarizer/0.0 (https://www.gutenberg.org/)",
        }
        self.langcode = "en"

    def get_wikis(self, job):
        """Return (lang, page_title) for every Wikipedia link stored in the book's 500 notes."""
        marcnotes = [marc for marc in job.dc.marcs if marc.code == '500']
        wikis = []
        for marc in marcnotes:
            if marc.text.startswith(WIKI_CAPTION):
                wiki_tuple = self.check_wikipedia_url(marc.text)
                if wiki_tuple:
                    wikis.append(wiki_tuple)
        return wikis

    def build(self, job):
        '''Write summary to database.'''
        id = job.dc.project_gutenberg_id
        if is_non_text(job.dc.book):

            info ("SummaryWriter: Non-Text Job, Skipping Writing for %d" % id)
            return
        self.dc = job.dc
        if not len(job.dc.languages) == 0:
            self.langcode = job.dc.languages[0].id

        summary_type, existing_summary_marc = self.get_existing_summary()
        title_and_authors = job.dc.make_pretty_title()
        wikis = self.get_wikis(job)
        if existing_summary_marc:
            # Never touch a Wikipedia-based summary. The 500-note check matters because
            # older Wikipedia summaries carry LLM_TAG (see header).
            if summary_type == "WIKI" or wikis:
                return
        # Only books with no summary get the Wikipedia search: for the rest it was
        # already done once, and repeating it costs Serper + Claude calls.
        elif self.summarise_from_wikipedia(id, wikis, title_and_authors):
            return

        # Summarise from the book text: either there is no summary and no Wikipedia
        # article, or the existing summary was made from the book text and gets redone.
        try:
            # the parser was already run by our TxtWriter base class; reuse its parsed text
            parser = TxtWriter.ParserFactory.ParserFactory.parsers[job.url]
            # drop the Project Gutenberg license header/footer before feeding the model
            book_content, _, _ = strip_headers_from_txt(parser.unicode_content())

        except KeyError as kerr:
            error ("SummaryWriter: Couldn't Access Text: %s" % kerr)
            return
        except UnicodeError as uerr:
            error ("SummaryWriter: Bad Text Content: %s" % uerr)
            return
        if len(book_content) > MAX_INPUT_CHARS:
            info ("SummaryWriter: Book too long for %s, Skipping Writing for %d" % (OPENAI_MODEL, id))
            return
        try:
            content_summary = self.summarise_book(book_content, title_and_authors)
        except Exception as unkerr:
            error ("SummaryWriter: AI Request Failed: %s" % unkerr)
            return
        if len(content_summary.split()) < MIN_SUMMARY_WORDS:
            error ("SummaryWriter: AI Error, Skipping Writing for %d. Summary: %s" % (id, content_summary))
            return

        # updates the existing 520 row in place, or creates one if there is none
        self.insert_into_pg_database(id, content_summary + LLM_TAG, existing_summary_marc)

    def summarise_from_wikipedia(self, id, wikis, title_and_authors):
        """Store a Wikipedia summary from a stored link or a validated search hit; True if stored."""
        # a Wikipedia link already recorded in the 500 notes needs no validation
        for wiki_lang, page_title in wikis:
            wiki_summary = self.get_wikipedia_article_summary(page_title, wiki_lang)
            if wiki_summary:
                self.insert_into_pg_database(id, wiki_summary + WIKI_TAG, None)
                return True

        # otherwise Google for one and let Claude confirm the article is about this book
        urls = self.google_search_with_serper(title_and_authors + " wikipedia")
        for lang, page_title in filter(None, map(self.check_wikipedia_url, urls)):
            wiki_summary = self.get_wikipedia_article_summary(page_title, lang)
            if wiki_summary and self.validate_with_claude(wiki_summary, title_and_authors):
                if (lang, page_title) not in wikis:
                    self.add_wiki_url_to_database(id, page_title, lang)
                self.insert_into_pg_database(id, wiki_summary + WIKI_TAG, None)
                return True
        return False

    def get_existing_summary(self):
        """Return (provenance, 520 row) of the stored summary, or (None, None) if there is none."""
        summarymarcs = [marc for marc in self.dc.book.attributes if marc.fk_attriblist == 520]
        for marc in summarymarcs:
            if LLM_TAG in marc.text:
                return ['LLM', marc]
            elif WIKI_TAG in marc.text:
                return ['WIKI', marc]
            elif EDITED_TAG in marc.text:
                return ['EDITED', marc]
        return None, None

    def insert_into_pg_database(self, id, db_summary, existing_summary_marc):
        """Replace the text of an existing 520 row, or add a new one."""
        session = self.dc.get_my_session()
        try:
            if existing_summary_marc:
                existing_summary_marc.text = db_summary
                session.commit()
                info ("SummaryWriter: replaced summary: %d" % id)
                return
            self.dc.book.attributes.append(Attribute(
                fk_attriblist=520, text=db_summary, nonfiling=0))
            session.commit()
            info ("SummaryWriter: created summary: %d" % id)

        except DatabaseError as dberr:
            exception ('SummaryWriter: could not add summary to database: %s' % (dberr))


    def add_wiki_url_to_database(self, id, wiki_title, wiki_lang):
        """Record the Wikipedia link as a 500 note; this is what later marks the summary as Wikipedia-based."""
        marctext = f"{WIKI_CAPTION}: https://{wiki_lang}.wikipedia.org/wiki/{wiki_title}"
        try:
            self.dc.book.attributes.append(Attribute(
                fk_attriblist=500, nonfiling=len(WIKI_CAPTION) + 2, text=marctext))
            self.dc.get_my_session().commit()
            info("SummaryWriter: Added Wikipedia URL to database")
        except DatabaseError as dberr:
            exception ('SummaryWriter: Could not add Wikipedia URL to database: %s' % (dberr))



    def get_wikipedia_article_summary(self, wiki_title, lang):
        '''Extract and return summary from relevant English Wikipedia article(s).'''
        wiki_summary_api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "format": "json",
            "action": "query",
            "indexpageids": True,
            "redirects": True,
            "prop": "extracts|langlinks",
            "lllang": self.langcode,
            "exintro": True,
            "explaintext": True,
            "titles": wiki_title,
        }

        response = requests.get(wiki_summary_api_url, headers=self.wiki_request_headers, params=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as httperr:
            error("Could not reach MediaWiki API: %s" % httperr)
            return None

        summary_res = response.json()
        page_id = summary_res["query"]["pageids"][0]

        langlinks = summary_res["query"]["pages"][page_id].get("langlinks")
        if langlinks and lang != self.langcode:
            return self.get_wikipedia_article_summary(langlinks[0]["*"], self.langcode)

        wiki_summary = summary_res["query"]["pages"][page_id].get("extract")
        if wiki_summary != "" and wiki_summary != None:
            return wiki_summary

        if lang != self.langcode:
            return self.get_wikipedia_article_summary(wiki_title, self.langcode)

        return None

    def google_search_with_serper(self, query):
        """Searches Google via Serper API and returns list of URLs."""
        headers = {
            'X-API-KEY': os.getenv("SERPER_API_KEY"),
            'Content-Type': 'application/json'
        }
        # serper is 3rd party google search API (paid for ~50k searches)
        # if broken, add more uses or replace with official google search API
        response = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json={"q": query, "num": 20}
        )
        results = []
        box = response.json().get("answerBox") # sometimes relevant wiki article is in answer box instead of search results
        if box:
            results.append(box["link"])
        results.extend([result["link"] for result in response.json()["organic"]])
        return results

    def check_wikipedia_url(self, text):
        # the CAPTION indicates that the subject of the wikipedia entry in the book
        
        wiki_match = WIKIMATCH.search(text)
        if not wiki_match:
            return None
        lang = wiki_match.group(1)
        if lang in ['sco']: # some wikipedias are not trustworthy
            return None
        page_title = wiki_match.group(2)
        if any(pattern in unquote(page_title) for pattern in AVOID_WIKI):
            return None

        return (lang, page_title) # return lang and wiki url title for mediawiki api


    def validate_with_claude(self, wiki_summary, title_and_authors):
        """Validate if Wikipedia summary (intro + explain) matches the book using Claude."""
        wiki_validator = WikipediaValidator(wiki_summary, title_and_authors)
        try:
            response = anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=500,
                system=wiki_validator.system_prompt["content"],
                messages=[wiki_validator.main_prompt]
            )

            answer = response.content[0].text
            verdict_match = re.search(r'VERDICT:\s*(YES|NO)', answer, re.IGNORECASE)
            result = verdict_match and verdict_match.group(1).upper() == "YES"
            return result
        except Exception as e:
            error('SummaryWriter: ' + e)
            return False

    def summarise_book(self, book_content, title_and_author):
        """Generate a summary of the entire book using the WholeBook prompt."""
        # one user message: instructions, then the whole book, then a closing reminder
        user_message = "%s\n\n%s\n\n%s" % (
            WholeBook.user.format(title_and_author=title_and_author), book_content, WholeBook.after)
        response = openai_client.responses.create(
            model=OPENAI_MODEL, instructions=WholeBook.system, input=user_message)
        return response.output_text.strip()
