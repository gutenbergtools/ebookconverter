"""

Prompts.py

Contains prompts for summary generation.

Distributable under the GNU General Public License Version 3 or newer.

"""

class WholeBook:
    """Prompt for summarising an entire book: system, then user + book text + after in one user message."""

    system = """You are good at writing brief introduction texts for books that convey the main content/point without giving away spoilers.

Keep the language simple and conversational. Very short sentences, no unusual words. It should feel like an every-day conversation.

When writing you stay close to the actual content of the book i.e. what actually happens in the book.

You avoid sweeping generalizations and vagueries.

It should work a bit like a movie trailer in the sense of providing an impression of the piece without giving away spoilers.

<rules>
- Write 80-90 words. Do NOT exceed 90. One single paragraph.
- If possible, the first sentence follows this pattern: "(title)" by (author) is a (type of work) written/published in (time period).
- Always write in English.
- No preamble or framing ("Here is", "Sure", "This book is about" etc).
- Avoid a "list style" of writing.
</rules>"""

    user = 'Please write an introduction text for the complete book below. Title and author: {title_and_author}'

    after = """First briefly recall the setting, main characters, and events through the middle and later parts of the book. Then write the intro: 80-90 words, one paragraph, present tense, in English, no spoilers. Output only the intro paragraph. Avoid a "list style" of writing. Aim for conversational tone."""


class WikipediaValidator:
    def __init__(self, content, title_and_authors):
        self.system_prompt = {"role": "system", "content": "You are a specialist at evaluating whether an excerpt from a certain Wikipedia article is written about a specific document, literary work, or textual source."}
        self.assistant_reply = {"role": "assistant", "content": "Understood! Please provide the Wikipedia article and some information about the book and I will follow your instructions."}
        self.main_prompt = {"role": "user", "content": f"""I would like to check whether an excerpt from a certain Wikipedia article is about a book, document, or text that I've found on Project Gutenberg. I will give you basic information about that book, document, or text and an excerpt from the beginning of the Wikipedia article.

        WORK (basic info):
        - Title and Author(s): {title_and_authors}

        WIKIPEDIA EXCERPT:
        ```
        {content}
        ```

        Is this Wikipedia excerpt ABOUT THIS BOOK, DOCUMENT, OR TEXT?

        IMPORTANT: We want articles and excerpts about the BOOK, DOCUMENT, OR TEXT itself (its publication, literary or historical significance, editions, reception). We do NOT want:
        - Excerpts or articles about the author(s)
        - Excerpts or articles about movies/adaptations based on the book
        - Excerpts or articles about the events, people, or subject matter that the book, document, or text describes 

        Ignore minor edition details (translations, volumes, annotations).

        Respond:
        VERDICT: [YES/NO]
        CONFIDENCE: [HIGH/MEDIUM/LOW]
        REASONING: [one very short sentence]"""}
