#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
RDFWriter.py

Copyright 2009,2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Builds RDF entry for ebook.

"""

import os.path

import rdflib
from rdflib import BNode, URIRef, Literal

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS, NSURI, Struct
from libgutenberg.Logger import info
from ebookmaker import writers

RNS = Struct ()

for (_prefix, _uri) in gg.NSMAP.items ():
    setattr (RNS, _prefix, rdflib.namespace.Namespace (_uri))

EXPORTED_NAMESPACES = 'cc dcam dcterms marcrel pgterms rdf rdfs'.split ()

rdflib.term.bind (NSURI.dcterms.IMT, gg.DCIMT)


class Writer (writers.BaseWriter):
    """ A class to write an RDF Bibrec. """


    def __init__ (self):
        super (Writer, self).__init__ ()
        self.graph = rdflib.Graph ()


    def build (self, job):
        """ Build RDF record for ebook. """

        info ("Making   %s" % job.outputfile)
        fn = os.path.join (job.outputdir, job.outputfile)

        # build tree
        self.from_dc (job.dc)

        with open (fn, "wb") as fp:
            self.serialize (fp)

        info ("Done     %s" % job.outputfile)


    def serialize (self, fp):
        """ Serialize RDF graph to xml. """

        g = self.graph

        for prefix in EXPORTED_NAMESPACES:
            g.namespace_manager.bind (prefix, gg.NSMAP[prefix])

        g.serialize (fp, format = "pretty-xml",
                     base = str (NS.pg), xml_base = str (NS.pg))


    def append (self, s, p, o):
        """ Helper. """

        self.graph.add ( (s, p, o) )


    def vocabulary (self, parent, rows, term_name, vocabulary_encoding_scheme):
        """ Add term from vocabulary to node. """

        for row in rows:
            resource = BNode () # rdf:Description
            self.append (resource, RNS.dcam.memberOf, vocabulary_encoding_scheme)
            self.append (resource, RNS.rdf.value, Literal (row))
            self.append (parent, term_name, resource)


    def datatype (self, parent, rows, term_name, datatype):
        """ Add term with datatype to node. """

        for row in rows:
            resource = BNode () # rdf:Description
            self.append (resource, RNS.rdf.value, Literal (row, datatype=datatype))
            self.append (parent, term_name, resource)


    def from_dc (self, dc):
        """ Create RDF graph from DublinCore struct. """

	# gbn 2017-01-29: Updated license
        # lic = URIRef ('http://www.gnu.org/licenses/gpl.html')
        lic = URIRef ('https://creativecommons.org/publicdomain/zero/1.0/')
        this_doc = URIRef ('')

        self.append (this_doc, RNS.cc.license, lic)
        self.append (this_doc, RNS.rdf.type,   RNS.cc.Work)
        self.append (this_doc, RNS.rdfs.comment, Literal (
            '''Archives containing the RDF files for *all* our books can be downloaded at
            https://www.gutenberg.org/wiki/Gutenberg:Feeds#The_Complete_Project_Gutenberg_Catalog'''
        ))


        # book node

        book = Literal (RNS.ebook[str (dc.project_gutenberg_id)])
        self.append (book, RNS.rdf.type, RNS.pgterms.ebook)


        # publisher, copyright and release date

        self.append (book, RNS.dcterms.publisher, Literal ('Project Gutenberg'))
        self.append (book, RNS.dcterms.license,   RNS.pg.license)
        self.append (book, RNS.dcterms.issued,    Literal (dc.release_date))
        self.append (book, RNS.dcterms.rights,    Literal (dc.rights))
        self.append (book, RNS.pgterms.downloads, Literal (dc.downloads))


        # authors
        # for a list of relator codes see:
        # http://www.loc.gov/loc.terms/relators/

        for author in dc.authors:
            # make author node
            a = RNS.pgagents[str (author.id)]
            self.append (a, RNS.rdf.type, RNS.pgterms.agent)
            self.append (a, RNS.pgterms.name, Literal (author.name))
            if author.birthdate:
                self.append (a, RNS.pgterms.birthdate, Literal (author.birthdate))
            if author.deathdate:
                self.append (a, RNS.pgterms.deathdate, Literal (author.deathdate))

            # aliases
            for alias in author.aliases:
                self.append (a, RNS.pgterms.alias, Literal (alias.alias))

            # web pages
            for webpage in author.webpages:
                p = URIRef (webpage.url)
                self.append (p, RNS.dcterms.description, Literal (webpage.description))
                self.append (a, RNS.pgterms.webpage, p)

            # append author node to book node
            if author.marcrel == 'aut' or author.marcrel == 'cre':
                self.append (book, RNS.dcterms.creator, a)
            else:
                self.append (book, RNS.marcrel[str (author.marcrel)], a)


        # titles, notes

        marc2dc = {
            '240': RNS.dcterms.alternative,
            '245': RNS.dcterms.title,
            '246': RNS.dcterms.alternative,
            '500': RNS.dcterms.description,
            '505': RNS.dcterms.tableOfContents,
            }

        for marc in dc.marcs:
            try:
                pred = marc2dc[marc.code]
                self.append (book, pred, Literal (marc.text))

                if pred == RNS.dcterms.title:
                    dc.title = marc.text

            except KeyError:
                # other  marc code
                self.append (book, RNS.pgterms[str ('marc' + marc.code)], Literal (marc.text))


        # languages (datatype)

        self.datatype (book, [language.id for language in dc.languages],
                       RNS.dcterms.language, RNS.dcterms.RFC4646)

        # subjects (vocabulary)

        self.vocabulary (book, [subject.subject for subject in dc.subjects],
                         RNS.dcterms.subject, RNS.dcterms.LCSH)

        # LoCC (vocabulary)

        self.vocabulary (book, [locc.id for locc in dc.loccs],
                         RNS.dcterms.subject, RNS.dcterms.LCC)

        # categories (vocabulary)

        self.vocabulary (book, dc.categories,
                         RNS.dcterms.type, RNS.dcterms.DCMIType)

        # bookshelves (vocabulary)

        self.vocabulary (book, [bs.bookshelf for bs in dc.bookshelves],
                         RNS.pgterms.bookshelf, RNS.pgterms.Bookshelf)

        # files

        for file_ in dc.files + dc.generated_files:
            # file node
            f = URIRef (RNS.pg[str (file_.url)])
            self.append (f, RNS.rdf.type, RNS.pgterms.file)

            # two-way link to ebook node
            self.append (book, RNS.dcterms.hasFormat, f)
            self.append (f, RNS.dcterms.isFormatOf,
                         URIRef (RNS.ebook[str (dc.project_gutenberg_id)]))

            # extent, modified
            self.append (f, RNS.dcterms.extent,   Literal (file_.extent))
            self.append (f, RNS.dcterms.modified, Literal (file_.modified))

            # mediatype (vocabulary)
            # note: avoid <built-in method format of Namespace>
            self.vocabulary (f, file_.mediatypes, RNS.dcterms['format'], RNS.dcterms.IMT)
