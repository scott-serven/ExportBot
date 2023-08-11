import re
from modules.exporter.markdown_tokenizer import MarkdownTokenizer
from modules.exporter.channel_exporter import ChannelExporter


exporter = ChannelExporter(None, None, './output')
filename = exporter.copy_asset_locally('12345678', 'https://cdn.discordapp.com/emojis/908035004255334410.webp?size=96&quality=lossless')
print("filename:", filename)
