import re

from modules.exporter.channel_exporter import ChannelExporter
from modules.exporter.markdown_tokenizer import MarkdownTokenizer

"""
Rules
  * There may not be any overlapping of markdown elements.  For example, an italics marker cannot begin
    within a header or link, and extend to outside the link.  In that scenario, the * character would be
    rendered as-is and not translated.
"""

HEADER1_PATTERN = re.compile('(^|\n)#\s(?P<title>.*)(\n|$)', flags=re.MULTILINE)
HEADER2_PATTERN = re.compile('(^|\n)##\s(?P<title>.*)(\n|$)', flags=re.MULTILINE)
HEADER3_PATTERN = re.compile('(^|\n)###\s(?P<title>.*)(\n|$)', flags=re.MULTILINE)
BOLD_PATTERN = re.compile('\*\*(?P<bold>.+)\*\*', flags=re.DOTALL)


def header_markdown_to_html(markdown: str) -> str:
    markdown = HEADER1_PATTERN.sub('<h1>\g<2></h1>', markdown)
    markdown = HEADER2_PATTERN.sub('<h2>\g<2></h2>', markdown)
    markdown = HEADER3_PATTERN.sub('<h3>\g<2></h3>', markdown)
    return markdown

def bold_markdown_to_html(markdown: str) -> str:
    markdown = BOLD_PATTERN.sub('<b>\g<1></b>', markdown)
    return markdown

def markdown_to_html(markdown: str) -> str:

    markdown = header_markdown_to_html(markdown)
    markdown = bold_markdown_to_html(markdown)
    return markdown



markdown = \
"""
> pre formatted
> multi
> line quote
> 
> ends on empty line?
> 
> before
> > single quote line
> after
"""
tokenizer = MarkdownTokenizer(markdown)
tokenizer.tokenize()
for token in tokenizer.tokens:
    print(f'--{token.token_type}--')
    print(token.value)
    print('')
