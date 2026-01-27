#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

# Generates a summary of a book using ChatGPT.
# For short books we feed in the entire book, for long books we feed in roughly the first 35 pages.
# This is necessary due to cost and context-size limitations.
# Read the prompting for a better understanding of how it works.

# One thing to realise is that what we're looking to put on the Gutenberg page is not
# actually an exhaustive summary of all the content of a book, but rathern an impression of it
# so that users can decide whether try a book or not. Kind of like a trailer to a movie.
# In that sense "summary" is not actually a very accurate term.


import os
import requests
import re

from sqlalchemy import and_
from urllib.parse import unquote

from libgutenberg.GutenbergDatabase import DatabaseError
from libgutenberg.Logger import exception, error, info, warning
from libgutenberg.Models import Attribute, Book
from ebookmaker.writers import TxtWriter
from ebookconverter.writers.Prompts import BeginningBook, FullBook, WikipediaValidator

from openai import OpenAI
import tiktoken
import anthropic

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_MODEL = "gpt-5"

anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

NON_TEXT_IDS = [76962,50,65,127,576,4656,10802,11220]  # ideally there should be a way to automatically recognize
                                                       # when a newly added PG item is text-based or not 
AI_BAD = ['It appears%%', 'It seems%%', '%%no content provided%%', '%%no content has been provided%%']
AVOID_WIKI = ["simple.", "File:", "/Category:", "(disambiguation)"]

LLM_TAG = " (This is an automatically generated summary.)"
WIKI_TAG = " (This summary is from Wikipedia.)"
HUMAN_TAG = " (This summary was written fully or in part by a human.)"


class Writer (TxtWriter.Writer):
    """ Summary Writer Class. """

    def __init__(self):
        super (Writer, self).__init__ ()
        self.beginning = BeginningBook()
        self.full = FullBook()
        self.wiki_request_headers = {
            "User-Agent": "Project-Gutenberg-Summarizer/0.0 (https://www.gutenberg.org/)",
        }
        self.langcode = "en"

    def build(self, job):
        '''Write summary to database.'''
        id = job.dc.project_gutenberg_id

        if id in NON_TEXT_IDS:
            info ("SummaryWriter: Non-Text Job, Skipping Writing for %d" % id)
            return
        
        # if wikipedia url already exists, use it if possible
        try:
            session = job.dc.get_my_session()
            # attribs = session.query(Attribute).where(and_(Attribute.fk_books == id, 
            #                                                  Attribute.fk_attriblist == 500))
            # for attrib in attribs:
            #     tup = self.check_wikipedia_url(attrib.text)
            #     if tup == None:
            #         continue
            #     existing_wiki_summary = self.get_wikipedia_article_summary(tup[0], tup[1])
            #     if existing_wiki_summary == None:
            #         info('SummaryWriter: Wikipedia URL in database no longer exists. Overwriting.')
            #         break
            #     else:
            #         self.insert_into_pg_database(session, id, existing_wiki_summary)
            #         return
        except DatabaseError as dberr:
            exception ('SummaryWriter: could not access database: %s' % (dberr))
            return
        
        if not len(job.dc.languages) == 0:
            self.langcode = job.dc.languages[0].id

        title_and_authors = job.dc.make_pretty_title()
        
        urls = self.google_search_with_serper(title_and_authors + " wikipedia")
        wiki_langs_and_titles = list(filter(None, map(self.check_wikipedia_url, urls)))

        for lang, title in wiki_langs_and_titles:
            wiki_summary = self.get_wikipedia_article_summary(title, lang)
            if wiki_summary == None:
                continue
            if self.validate_with_claude(wiki_summary, title_and_authors):
                self.add_wiki_url_to_database(session, id, title, lang)
                self.insert_into_pg_database(session, id, wiki_summary + WIKI_TAG)
                return
        
        # if we didn't find a wikipedia article that summarizes book, use LLM to summarize book via content
        try:
            # this should get the cached parser from our inherited TxtWriter
            parser = TxtWriter.ParserFactory.ParserFactory.parsers[job.url]
            book_content = parser.unicode_content()
        except KeyError as kerr:
            error ("SummaryWriter: Couldn't Access Text: %s" % kerr)
            return
        except UnicodeError as uerr:
            error ("SummaryWriter: Bad Text Content: %s" % uerr)
            return
        try:
            content_summary = self.summarise_book(book_content, title_and_authors)
        except Exception as unkerr:
            error ("SummaryWriter: AI Request Failed: %s" % unkerr)
            return
        for sign in AI_BAD:
            if sign in content_summary:
                error ("SummaryWriter: AI Error, Skipping Writing for %d. Summary: %s" % (id, content_summary))
                return
        
        self.insert_into_pg_database(session, id, content_summary + LLM_TAG)
    
    def insert_into_pg_database(self, session, id, db_summary):
        try: 
            attribute = session.query(Attribute).where(and_(Attribute.fk_attriblist == 520, Attribute.fk_books == id)).first()
            if attribute != None:
                attribute.text = db_summary
                session.commit()
            else:
                book = session.query(Book).where(Book.pk == id).first()
                book.attributes.append(Attribute(fk_attriblist=520, text=db_summary, nonfiling=0))
            info ("SummaryWriter: created summary: %d" % id)

        except DatabaseError as dberr:
            exception ('SummaryWriter: could not add summary to database: %s' % (dberr))


    def add_wiki_url_to_database(self, session, id, wiki_title, wiki_lang):
        caption = "Wikipedia page about this book: "
        marctext = caption + f"https://{wiki_lang}.wikipedia.org/wiki/{wiki_title}"
        try:
            for attribute in session.query(Attribute).where(and_(Attribute.fk_attriblist == 500, Attribute.fk_books == id)):
                if self.check_wikipedia_url(attribute.text) != None:
                    attribute.text = marctext
                    session.commit()
                    info("SummaryWriter: Replaced Wikipedia URL in database")
                    return
            book = session.query(Book).where(Book.pk == id).first()
            book.attributes.append(Attribute(fk_attriblist=500, nonfiling=len(caption), text=marctext))
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
    
    def check_wikipedia_url(self, url):
        lang_match = re.search(r'https?://([a-z]{2,3})\.wikipedia\.org', url)
        if not lang_match:
            return None
        lang = lang_match.group(1)

        if lang != self.langcode and lang != "en":
            return None
        
        title_match = re.search(r'/wiki/(.+)$', url.strip())
        if not title_match:
            return None
        page_title = unquote(title_match.group(1))

        if any(pattern in page_title for pattern in AVOID_WIKI):
            return None

        return (lang, title_match.group(1)) # return lang and wiki url title for mediawiki api



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

    
    def count_tokens(self, text, encoding_name='cl100k_base'):
        """Count the number of tokens in a text."""
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))


    def get_first_chunk(self, text, max_token_size, encoding_name="cl100k_base"):
        """Extract first chunk of text up to max_token_size tokens."""
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)
        first_chunk_tokens = tokens[:max_token_size]
        return encoding.decode(first_chunk_tokens)


    def summarise_beginning_of_book(self, title_and_author, text):
        """Generate two-paragraph summary from book's opening portion using GPT. To be used for long books."""
        system_prompt = self.beginning.system_prompt

        user_instruction = self.beginning.main_prompt
        user_instruction["content"] = user_instruction["content"].replace("title_and_author", title_and_author)
        
        assistant_reply = self.beginning.assistant_reply
        book_content = {"role": "user", "content": f"START OF BOOK BEGINNING: \n{text}\nEND OF BOOK BEGINNING"}

        messages = [system_prompt, user_instruction, assistant_reply, book_content]
        response = openai_client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
        return response.choices[0].message.content


    def summarise_entire_book(self, title_and_author, text):
        """Generate two-paragraph summary from entire book using GPT. To be used for short books."""
        system_prompt = self.full.system_prompt

        user_instruction = self.full.main_prompt
        user_instruction["content"] = user_instruction["content"].replace("title_and_author", title_and_author)

        assistant_reply = self.full.assistant_reply
        book_content = {"role": "user", "content": f"START OF BOOK: \n{text}\nEND OF BOOK"}

        messages = [system_prompt, user_instruction, assistant_reply, book_content]
        response = openai_client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
        return response.choices[0].message.content
    
    def get_book_content(self, url):
        """Return book text with Gutenberg header and footer removed."""
        try:
            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; GutenbergContent/1.0; +https://github.com)'},
                timeout=10
            )
            response.raise_for_status()
            return self.remove_gutenberg_wrapper(response.text)
        except requests.RequestException as e:
            error(f"Error fetching PG Book text: {e}")
            return None
        
    def remove_gutenberg_wrapper(self, text):
        """Remove Gutenberg header and footer from book text."""
        lines = text.split('\n')
        start_index = 0
        end_index = len(lines)

        for i, line in enumerate(lines):
            if line.startswith("*** START OF"):
                start_index = i + 1
            elif line.startswith("*** END OF"):
                end_index = i
                break

        return '\n'.join(lines[start_index:end_index]).strip()


    def summarise_book(self, book_content, title):
        """Generate formatted summary for book, using full text or opening portion based on length."""
        chunk_size = 24000
        print("Summarising:", title)

        if self.count_tokens(book_content) > chunk_size:
            beginning_of_book = self.get_first_chunk(book_content, chunk_size)
            summary = self.summarise_beginning_of_book(title, beginning_of_book)
        else:
            summary = self.summarise_entire_book(title, book_content)

        return summary