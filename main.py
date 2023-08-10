import re
from modules.exporter.markdown_tokenizer import MarkdownTokenizer



markdown = """
The source code for the chessbot project itself is at:

https://github.com/scott-serven/Chess-Bot
<a:meow_code:1096933806503624754>
That code provides a Discord interface over the [python-chess](https://python-chess.readthedocs.io/en/latest/) library"""

markdown = r"<:inbox_tray:842140740943478847> **[Invite link](https://discord.com/oauth2/authorize?client_id=830530156048285716&permissions=66407488&scope=bot%20applications.commands)**"
markdown = re.sub(r'\[(?P<text>[^\]]+)\]\((?P<link>[^\)]+)\)', '<a href="\g<2>">\g<1></a>', markdown)
print(markdown)
#
# tokenizer = MarkdownTokenizer(markdown)
# tokenizer.tokenize()
#
# for token in tokenizer.tokens:
#     print("==token==", token.token_type)
#     print(token.value)
