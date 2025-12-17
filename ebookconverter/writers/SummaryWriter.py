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

from sqlalchemy import and_

from libgutenberg.GutenbergDatabase import DatabaseError
from libgutenberg.Logger import exception, error, info
from libgutenberg.Models import Attribute
from ebookmaker.writers import TxtWriter
from ebookconverter.writers.Prompts import BeginningBook, FullBook

from openai import OpenAI
import tiktoken

class Writer (TxtWriter.Writer):
    """ Summary Writer Class. """

    def __init__(self):
        super (Writer, self).__init__ ()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.non_text_ids = [76962,50,65,127,576,4656,10802,11220] # ideally there should be a way to automatically recognize
                                                                   # when a newly added PG item is text-based or not
        self.ai_bad = ['It appears%%', 'It seems%%', '%%no content provided%%', '%%no content has been provided%%']
        self.beginning = BeginningBook()
        self.full = FullBook()

    def build(self, job):
        '''Write summary to database.'''
        id = job.dc.project_gutenberg_id
        if id in self.non_text_ids:
            info ("SummaryWriter: Non-Text Job, Skipping Writing for %d" % id)
            return
        
        try:
            parser = TxtWriter.ParserFactory.ParserFactory.parsers[job.url] # this should get the cached parser from our inherited TxtWriter
            book_content = parser.unicode_content()
        except KeyError as kerr:
            error ("SummaryWriter: Couldn't Access Text: %s" % kerr)
            return
        except UnicodeError as uerr:
            error ("SummaryWriter: Bad Text Content: %s" % uerr)
            return
        
        summary = self.summarise_book(book_content, job.dc.make_pretty_title())
        for sign in self.ai_bad:
            if sign in summary:
                error ("SummaryWriter: AI Error, Skipping Writing for %d. Summary: %s" % (id, summary))
                return

        try: 
            session = job.dc.get_my_session()
            attribute = session.query(Attribute).where(and_(Attribute.fk_attriblist == 520, Attribute.fk_books == id)).first()
            attribute.text = summary
            session.commit()
            info ("SummaryWriter: created summary: %d" % id)

        except DatabaseError as dberr:
            exception ('SummaryWriter: could not add summary to database: %s' % (dberr))



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


    def format_summary(self, summary):
        """Format summary for SQL insertion by replacing markdown, removing newlines, and escaping quotes."""
        # fixing common oddities sometimes returned by LLM
        formatted = summary.replace('*', '"').replace('_', '"').replace('"""', '"').replace('""', '"')
        # removing new lines because gutenberg website can't display newlines in HTML (unfortunately)
        formatted = formatted.replace("\n", " ")
        # add sql requirement to escape single quotes with an additional single quote
        formatted = formatted.replace("'", "''")
        return formatted


    def summarise_beginning_of_book(self, title_and_author, text):
        """Generate two-paragraph summary from book's opening portion using GPT. To be used for long books."""
        system_prompt = self.beginning.system_prompt

        user_instruction = self.beginning.main_prompt
        user_instruction["content"] = user_instruction["content"].replace("title_and_author", title_and_author)
        
        assistant_reply = self.beginning.assistant_reply
        book_content = {"role": "user", "content": f"START OF BOOK BEGINNING: \n{text}\nEND OF BOOK BEGINNING"}

        messages = [system_prompt, user_instruction, assistant_reply, book_content]
        response = self.openai_client.chat.completions.create(model="gpt-5", messages=messages)
        return response.choices[0].message.content


    def summarise_entire_book(self, title_and_author, text):
        """Generate two-paragraph summary from entire book using GPT. To be used for short books."""
        system_prompt = self.full.system_prompt

        user_instruction = self.full.main_prompt
        user_instruction["content"] = user_instruction["content"].replace("title_and_author", title_and_author)

        assistant_reply = self.full.assistant_reply
        book_content = {"role": "user", "content": f"START OF BOOK: \n{text}\nEND OF BOOK"}

        messages = [system_prompt, user_instruction, assistant_reply, book_content]
        response = self.openai_client.chat.completions.create(model="gpt-5", messages=messages)
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

        return self.format_summary(summary)


    def insert_summary_sql(self, book_id, summary): # unused for now since switch to ORM
        """Append SQL INSERT statement for book summary to output file."""
        note = " (This is an automatically generated summary.)"
        sql = f"insert into attributes (fk_books,fk_attriblist,text,nonfiling) values ({book_id},520,'{summary}{note}',0);"

        return sql