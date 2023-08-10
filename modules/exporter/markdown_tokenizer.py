import re
from enum import Enum


class MarkdownTokenType(Enum):

    HEADER1 = 'header1'
    HEADER2 = 'header2'
    HEADER3 = 'header3'
    AT_USER = 'at_user'
    AT_ROLE = 'at_role'
    CHANNEL_LINK = 'channel_link'
    EMOJI = 'emoji'
    TEXT = 'text'
    CODE_BLOCK = 'code_block'
    CODE_TEXT = 'code_text'
    LINK = 'link'
    TEXT_LINK = 'text_link'


class Token:

    def __init__(self, token_type, value):
        self.token_type: MarkdownTokenType = token_type
        self.value: str = value


class MarkdownTokenizer:
    """
    When we translate messages into HTML, those messages may contain text with HTML characters such as < > &.  For
    text, we just want to escape those characters to &lt; &gt; and &amp;.  However, we don't want escaping to
    occur in code blocks, links, or in the HTML we may generate for certain elements during translation.

    The solution is to split the messages into tokens that can be individually parsed without trying to account for
    the parsing of other types of elements.
    """

    CODE_BLOCK_SEQUENCE: str = '```'
    CODE_TEXT_SEQUENCE: str = '`'

    AT_USER_PATTERN: re.Pattern = re.compile('^<@\d+>')
    AT_ROLE_PATTERN: re.Pattern = re.compile('^<@&\d+>')
    CHANNEL_LINK_PATTERN: re.Pattern = re.compile('^<#\d+>')
    EMOJI_PATTERN: re.Pattern = re.compile('^<a?:[a-zA-Z0-9_-]+:\d+>')
    HEADER_PATTERN: re.Pattern = re.compile('^(?P<header>#{1,3}) (?P<value>.+)$', re.MULTILINE)
    LINK_PATTERN: re.Pattern = re.compile('^(?P<link>https?://[^\s]+)(\s|$)', re.IGNORECASE)
    ODD_LINK_PATTERN: re.Pattern = re.compile('^<(?P<link>https?://[^>]+)>', re.IGNORECASE)  # discord does something weird with certain links where it puts gt/lt around them
    TEXT_LINK_PATTERN: re.Pattern = re.compile(r'\[(?P<text>[^\]]+)\]\((?P<link>[^\)]+)\)')

    def __init__(self, markdown):
        self.markdown: str = markdown
        self.tokens: list[Token] = []
        self.idx: int = 0
        self.curr_token: str = ''
        self.token_found: bool = False

    def capture_curr_token(self) -> None:
        if len(self.curr_token) > 0:
            self.tokens.append(Token(MarkdownTokenType.TEXT, self.curr_token))
            self.curr_token = ''

    def get_code_block_token(self) -> None:
        self.capture_curr_token()
        self.idx += len(self.CODE_BLOCK_SEQUENCE)  # skip over escape sequence
        index: int = self.markdown[self.idx::].find(self.CODE_BLOCK_SEQUENCE)
        token = Token(MarkdownTokenType.CODE_BLOCK, self.markdown[self.idx:self.idx+index])
        self.tokens.append(token)
        self.idx += index + len(self.CODE_BLOCK_SEQUENCE)
        self.token_found = True

    def get_code_text_token(self) -> None:
        self.capture_curr_token()
        self.idx += len(self.CODE_TEXT_SEQUENCE)  # skip over escape sequence
        index: int = self.markdown[self.idx::].find(self.CODE_TEXT_SEQUENCE)
        token = Token(MarkdownTokenType.CODE_TEXT, self.markdown[self.idx:self.idx+index])
        self.tokens.append(token)
        self.idx += index + len(self.CODE_TEXT_SEQUENCE)
        self.token_found = True

    def get_at_user_token(self) -> None:
        match: re.Match = self.AT_USER_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.AT_USER, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_at_role_token(self) -> None:
        match: re.Match = self.AT_ROLE_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.AT_ROLE, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_channel_link_token(self) -> None:
        match: re.Match = self.CHANNEL_LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.CHANNEL_LINK, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_emoji_token(self) -> None:
        match: re.Match = self.EMOJI_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.EMOJI, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_link_token(self) -> None:
        match: re.Match = self.LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.LINK, match['link']))
            self.idx += len(match['link'])
            self.token_found = True

    def get_odd_link_token(self) -> None:
        match: re.Match = self.ODD_LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.LINK, match['link']))
            self.idx += len(match['link']) + 2
            self.token_found = True

    def get_text_link_token(self) -> None:
        match: re.Match = self.TEXT_LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.TEXT_LINK, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_header_token(self) -> None:
        """
        Headers can only occur at the start of a new line
        :return:
        """
        if self.idx > 0 and self.markdown[self.idx-1] != '\n':
            return

        header_match = self.HEADER_PATTERN.search(self.markdown[self.idx::])
        if header_match:
            token = None
            value = header_match['value']
            match header_match['header']:
                case '#': token = Token(MarkdownTokenType.HEADER1, value)
                case '##': token = Token(MarkdownTokenType.HEADER2, value)
                case '###': token = Token(MarkdownTokenType.HEADER3, value)
            if token is not None:
                self.capture_curr_token()
                self.tokens.append(token)
                self.idx += len(header_match['header']) + 1 + len(value)
                self.token_found = True

    def append_to_curr_token(self):
        """
        If we didn't find any other tokens for the current character, keep track of that and it'll
        eventually turn into a TEXT token
        :return:
        """
        if self.idx < len(self.markdown):
            self.curr_token += self.markdown[self.idx]
            self.idx += 1

    def tokenize(self) -> None:
        self.tokens = []
        self.curr_token = ''
        while self.idx < len(self.markdown):
            char = self.markdown[self.idx]
            self.token_found: bool = False
            match char:
                case self.CODE_TEXT_SEQUENCE:
                    if self.markdown[self.idx:self.idx+3] == self.CODE_BLOCK_SEQUENCE:
                        self.get_code_block_token()
                    else:
                        self.get_code_text_token()
                case '#':
                    if not self.get_header_token():
                        self.append_to_curr_token()
                case '<':
                    self.get_at_user_token()
                    self.get_at_role_token()
                    self.get_channel_link_token()
                    self.get_emoji_token()
                    self.get_odd_link_token()
                case '[':
                    self.get_text_link_token()
                case 'h' | 'H':
                    self.get_link_token()

            if not self.token_found:
                self.append_to_curr_token()
        self.capture_curr_token()
