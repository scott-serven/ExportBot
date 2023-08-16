import re
from enum import Enum


class MarkdownTokenType(Enum):
    HEADER1 = "header1"
    HEADER2 = "header2"
    HEADER3 = "header3"
    AT_USER = "at_user"
    AT_ROLE = "at_role"
    CHANNEL_LINK = "channel_link"
    EMOJI = "emoji"
    TEXT = "text"
    CODE_BLOCK = "code_block"
    CODE_TEXT = "code_text"
    LINK = "link"
    MASKED_LINK = "masked_link"
    BLOCKQUOTE = "blockquote"
    UNORDERED_LIST_ITEM = 'unordered_list_item'


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

    AT_USER_PATTERN: re.Pattern = re.compile("^<@\d+>")
    AT_ROLE_PATTERN: re.Pattern = re.compile("^<@&\d+>")
    CHANNEL_LINK_PATTERN: re.Pattern = re.compile("^<#\d+>")
    EMOJI_PATTERN: re.Pattern = re.compile("^<a?:[a-zA-Z0-9_-]+:\d+>")
    HEADER_PATTERN: re.Pattern = re.compile("^(?P<header>#{1,3}) (?P<value>.+)(\n|$)", re.MULTILINE)
    LINK_PATTERN: re.Pattern = re.compile("^(?P<link>https?://[^\s]+)(\s|$)", re.IGNORECASE)
    ODD_LINK_PATTERN: re.Pattern = re.compile(
        "^<(?P<link>https?://[^>]+)>", re.IGNORECASE
    )  # discord does something weird with certain links where it puts gt/lt around them
    MASKED_LINK_PATTERN: re.Pattern = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<link>[^\)]+)\)")
    MULTILINE_BLOCKQUOTE_PATTERN: re.Pattern = re.compile(r'(^|\n)>>>\s(?P<quote>.+)$', re.DOTALL)
    SINGLE_BLOCKQUOTE_PATTERN: re.Pattern = re.compile(r'^> (?P<quote>.*)$', re.MULTILINE)
    CODE_BLOCK_PATTERN: re.Pattern = re.compile('^```\n?(?P<code>.+)```', re.DOTALL)
    CODE_TEXT_PATTERN: re.Pattern = re.compile('^`.+`', re.DOTALL)
    UNORDERED_BULLET_PATTERN: re.Pattern = re.compile('^(?P<spaces>(\s*))(\*|-) (?P<item>(.+))(\n|$)', re.MULTILINE)

    def __init__(self, markdown):
        self.markdown: str = markdown
        self.tokens: list[Token] = []
        self.idx: int = 0
        self.curr_token: str = ""
        self.token_found: bool = False

    def capture_curr_token(self) -> None:
        if len(self.curr_token) > 0:
            self.tokens.append(Token(MarkdownTokenType.TEXT, self.curr_token))
            self.curr_token = ""

    def capture_pattern_token(self, pattern: re.Pattern, token_type: MarkdownTokenType):
        match: re.Match = pattern.search(self.markdown[self.idx::])
        if match:
            print('token: ', token_type, match[0])
            self.capture_curr_token()
            self.tokens.append(Token(token_type, match[0]))
            self.idx += len(match[0])
            self.token_found = True

    def get_code_block_token(self) -> None:
        self.capture_pattern_token(self.CODE_BLOCK_PATTERN, MarkdownTokenType.CODE_BLOCK)

    def get_code_text_token(self) -> None:
        self.capture_pattern_token(self.CODE_TEXT_PATTERN, MarkdownTokenType.CODE_TEXT)

    def get_at_user_token(self) -> None:
        self.capture_pattern_token(self.AT_USER_PATTERN, MarkdownTokenType.AT_USER)

    def get_at_role_token(self) -> None:
        self.capture_pattern_token(self.AT_ROLE_PATTERN, MarkdownTokenType.AT_ROLE)

    def get_channel_link_token(self) -> None:
        self.capture_pattern_token(self.CHANNEL_LINK_PATTERN, MarkdownTokenType.CHANNEL_LINK)

    def get_emoji_token(self) -> None:
        self.capture_pattern_token(self.EMOJI_PATTERN, MarkdownTokenType.EMOJI)

    def get_link_token(self) -> None:
        match: re.Match = self.LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.LINK, match["link"]))
            self.idx += len(match["link"])
            self.token_found = True

    def get_odd_link_token(self) -> None:
        match: re.Match = self.ODD_LINK_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.LINK, match["link"]))
            self.idx += len(match["link"]) + 2
            self.token_found = True

    def get_masked_link_token(self) -> None:
        self.capture_pattern_token(self.MASKED_LINK_PATTERN, MarkdownTokenType.MASKED_LINK)

    def get_single_blockquote_token(self) -> None:
        match: re.Match = self.SINGLE_BLOCKQUOTE_PATTERN.search(self.markdown[self.idx::])
        if match:
            self.capture_curr_token()
            self.tokens.append(Token(MarkdownTokenType.BLOCKQUOTE, match['quote']))
            self.idx += len(match[0])
            if self.idx < len(self.markdown) and self.markdown[self.idx] == '\n':
                self.idx += 1
            self.token_found = True

    def get_multiline_blockquote_token(self) -> None:
        self.capture_pattern_token(self.MULTILINE_BLOCKQUOTE_PATTERN, MarkdownTokenType.BLOCKQUOTE)

    def get_unordered_list_token(self) -> None:
        self.capture_pattern_token(self.UNORDERED_BULLET_PATTERN, MarkdownTokenType.UNORDERED_LIST_ITEM)

    def get_header_token(self) -> None:
        """
        Headers can only occur at the start of a new line
        :return:
        """
        if self.idx > 0 and self.markdown[self.idx - 1] != "\n":
            return

        header_match = self.HEADER_PATTERN.search(self.markdown[self.idx::])
        if header_match:
            token = None
            value = header_match["value"]
            print('Header: ', value)
            match header_match["header"]:
                case "#":
                    token = Token(MarkdownTokenType.HEADER1, value)
                case "##":
                    token = Token(MarkdownTokenType.HEADER2, value)
                case "###":
                    token = Token(MarkdownTokenType.HEADER3, value)
            if token:
                self.capture_curr_token()
                self.tokens.append(token)
                self.idx += len(header_match["header"]) + 1 + len(value) + 1  # an extra +1 to exclude any newline
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
        self.curr_token = ""
        while self.idx < len(self.markdown):
            char = self.markdown[self.idx]
            last_char = ''
            if self.idx > 0:
                last_char = self.markdown[self.idx-1]
            self.token_found = False
            if last_char == '\n':
                self.get_unordered_list_token()
            match char:
                case '`':
                    if self.idx < len(self.markdown) - 2 and self.markdown[self.idx:self.idx+3] == '```':
                        self.get_code_block_token()
                    else:
                        self.get_code_text_token()
                case "#":
                    if not self.get_header_token():
                        self.append_to_curr_token()
                case "<":
                    if self.idx < len(self.markdown) - 1:
                        next_char = self.markdown[self.idx+1]
                        match next_char:
                            case '@':
                                self.get_at_user_token()
                                self.get_at_role_token()
                            case '#':
                                self.get_channel_link_token()
                            case ':':
                                self.get_emoji_token()
                            case _:
                                self.get_odd_link_token()
                case ">":
                    self.get_multiline_blockquote_token()
                    self.get_single_blockquote_token()
                case "[":
                    self.get_masked_link_token()
                case "h" | "H":
                    self.get_link_token()

            if not self.token_found:
                self.append_to_curr_token()
        self.capture_curr_token()
