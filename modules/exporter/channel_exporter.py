import os
import re
import urllib.parse

import discord
import requests
from zipfile import ZipFile, ZIP_BZIP2

from .markdown_tokenizer import MarkdownTokenizer, MarkdownTokenType


class ChannelExporter:
    """
    Limitations:
      * Does not drill into threads
      * Does not do code formatting
    """

    def __init__(self, bot: discord.Client, channel: discord.TextChannel, output_dir: str):
        self.bot: discord.Client = bot
        self.channel: discord.TextChannel = channel
        self.output_dir: str = output_dir
        self.messages: list[discord.Message] = []
        self.document_filename = 'index.html'
        self.thread_id_map: {int, discord.Thread} = {}
        with open("modules/templates/export_doc.html", "r") as f:  # TODO use current path as reference
            self.doc_template = ''.join(f.readlines())

    def get_thread_document_filename(self, thread_id) -> str:
        """
        Return a consistently named filename for a thread html file so we can ensure links
        go to the same filename we save thread documents under
        :param thread_id:
        :return: a filename that represents the html file for thread contents
        """
        return f'thread_{thread_id}_index.html'

    def create_output_dirs(self) -> None:
        if not os.path.isdir(self.output_dir):
            os.mkdir(f"{self.output_dir}")
        if not os.path.isdir(f"{self.output_dir}/assets/"):
            os.mkdir(f"{self.output_dir}/assets/")

    def copy_asset_locally(self, asset_id: str, url: str, alt_url: str = None) -> str:
        ext: str = ''
        parsed_url = urllib.parse.urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        if '.' in filename:
            ext = '.' + filename.split('.')[-1]

        local_filename = f"{self.output_dir}/assets/{asset_id}{ext}"
        html_relative_filename = f"./assets/{asset_id}{ext}"
        if not os.path.isfile(local_filename):
            print("downloading asset: ", url)
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            for url in [url, alt_url]:
                if url is not None:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        with open(local_filename, "wb") as f:
                            f.write(response.content)
                            break
        return html_relative_filename

    def escape_html(self, markdown: str) ->str:
        markdown = markdown.replace('<', '&lt;')
        markdown = markdown.replace('>', '&gt;')
        markdown = markdown.replace('&', '&amp;')
        markdown = markdown.replace('\n', '<br>')
        return markdown

    def markdown_to_html(self, markdown: str) -> str:
        markdown = re.sub('\*\*(?P<text>[^\*]*)\*\*', '<b>\g<1></b>', markdown, flags=re.MULTILINE)
        markdown = re.sub('\*(?P<text>[^\*]*)\*', '<i>\g<1></i>', markdown, flags=re.MULTILINE)
        markdown = re.sub('__(?P<text>[^_]*)__', '<span style="font-decoration:underline">\g<1></span>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'\[(?P<text>[^\]]+)\]\((?P<link>[^\)]+)\)', '<a href="\g<2>">\g<1></a>', markdown)
        return markdown

    async def get_all_messages(self) -> None:
        print('get_all_messages: ', type(self.channel), self.channel)
        async for message in self.channel.history(limit=None):
            self.messages.append(message)
        self.messages.reverse()

    def at_user_markdown_to_username(self, markdown: str) -> str:
        match: re.Match = re.search('<@(?P<userid>\d+)>', markdown)
        user: discord.User = self.bot.get_user(int(match.groups()[0]))
        if user:
            return user.name
        else:
            return 'unknown user'

    def at_role_markdown_to_name(self, markdown: str) -> str:
        match: re.Match = re.search('<@&(?P<role_id>\d+)>', markdown)
        role: any = self.channel.guild.get_role(int(match.groups()[0]))
        if role:
            return role.name
        else:
            return 'unknown role'

    def channel_link_to_name(self, markdown: str) -> str:
        match: re.Match = re.search('<#(?P<channel>\d+)>', markdown)
        channel: any = self.bot.get_channel(int(match.groups()[0]))
        if channel:
            return channel.name
        else:
            return 'unknown channel'

    async def emoji_markdown_to_html(self, markdown) -> str:
        """
        Limitation: Can't load emoji from a server that this bot is not a member of
        :param markdown:
        :return:
        """
        match: re.Match = re.search('<a?:[^:]+:(?P<emoji_id>\d+)>', markdown)
        result = ''
        if match:
            emoji_id = match['emoji_id']
            emoji: str | None | discord.Emoji | discord.PartialEmoji = self.bot.get_emoji(int(emoji_id))
            asset_filename: str | None = None
            if type(emoji) == discord.Emoji or type(emoji) == discord.PartialEmoji:
                asset_filename = self.copy_asset_locally(str(emoji.id), emoji.url)
            elif emoji is None:
                asset_filename = self.copy_asset_locally(emoji_id, f'https://cdn.discordapp.com/emojis/{emoji_id}.webp?size=96&quality=lossless')  # download directly to get emoji for other servers

            if asset_filename:
                result = f'<img src="{asset_filename}">'
            else:
                result = markdown
        return result

    def newline_to_break(self, value):
        return value.replace('\n', '<br>')

    async def parse_masked_link(self, text_link) -> (str, str):
        """
        masked links are markdown links in the format of [link text](link url)
        :param text_link:
        :return: tuple of the (text, link)
        """
        match: re.Match = re.search(r'\[(?P<text>[^\]]+)\]\((?P<link>[^\)]+)\)', text_link)
        if match:
            return await self.convert_message_content_to_html(match['text']), match['link']
        else:
            return '', ''

    async def convert_message_content_to_html(self, content: str) -> str:
        """
        Tokenizes and parses message content into HTML.
        :param message:
        :return:
        """
        markdown_tokenizer = MarkdownTokenizer(content)
        markdown_tokenizer.tokenize()

        html: str = ''
        for token in markdown_tokenizer.tokens:
            match token.token_type:
                case MarkdownTokenType.HEADER1:
                    html += f'<h1>{self.markdown_to_html(token.value)}</h1>'
                case MarkdownTokenType.HEADER2:
                    html += f'<h2>{self.markdown_to_html(token.value)}</h2>'
                case MarkdownTokenType.HEADER3:
                    html += f'<h3>{self.markdown_to_html(token.value)}</h3>'
                case MarkdownTokenType.AT_USER:
                    html += f'<span class="atText">@{self.at_user_markdown_to_username(token.value)}</span>'
                case MarkdownTokenType.AT_ROLE:
                    html += f'<span class="atRole">@{self.at_role_markdown_to_name(token.value)}</span>'
                case MarkdownTokenType.CHANNEL_LINK:
                    html += f'<span class="atText">#{self.channel_link_to_name(token.value)}</span>'
                case MarkdownTokenType.EMOJI:
                    html += f'<span class="emoji">{await self.emoji_markdown_to_html(token.value)}</span>'
                case MarkdownTokenType.CODE_TEXT:
                    html += f'<span class="codeText">{token.value}</span>'
                case MarkdownTokenType.CODE_BLOCK:
                    html += f'<div class="code"><code><pre>{self.newline_to_break(token.value)}</pre></code></div>'
                case MarkdownTokenType.TEXT:
                    html += self.newline_to_break(self.markdown_to_html(token.value))
                case MarkdownTokenType.LINK:
                    html += f'<a href="{token.value}">{token.value}</a>'
                case MarkdownTokenType.MASKED_LINK:
                    (text, link) = await self.parse_masked_link(token.value)
                    html += f'<a href="{link}">{text}</a>'
        return html

    def get_author_avatar(self, author: discord.User | None) -> str:
        avatar_url = author.avatar.url if author and author.avatar else 'https://cdn.discordapp.com/embed/avatars/0.png'
        return f'<img src="{avatar_url}">'

    def default_title_to_html(self, message: discord.Message) -> str:
        bot_html: str = ''
        if message.author.bot:
            bot_html = ' <span class="botTag">Bot</span>'
        username_style: str = ''
        if message.author.top_role and message.author.top_role.color.value != 0:
            username_style = f'style="color: {message.author.top_role.color};"'
        return \
            f"""
             <div class="title">
                 <span class="username" {username_style}>{message.author.name}</span>{bot_html} 
                 <span class="timestamp">{message.created_at.strftime("%Y-%m-%d %H:%M")}</span>
             </div>
             """

    def system_title_to_html(self, message: discord.Message) -> str:
        return \
            f"""
             <div class="title">
               <span class="systemMessage">{message.system_content}</span>
               <span class="timestamp">{message.created_at.strftime("%Y-%m-%d %H:%M")}</span>
             </div>
             """

    def convert_attachment_to_html(self, attachment: discord.Attachment) -> str:
        result = '<div class="attachment">'
        relative_filename = self.copy_asset_locally(str(attachment.id), attachment.proxy_url, attachment.url)
        match attachment.filename.split('.')[-1]:
            case "png" | "jpg" | "jpeg" | "gif":
                result += f'<a href="{relative_filename}"><img class="attachment" src="{relative_filename}"></a>'
            case "mp4":
                result += f'<video width="400" controls><source src="{relative_filename}"></video>'
            case _:
                # file download
                result += f'<a href="{relative_filename}">Download</a>'
        result += '</div>'
        return result

    def convert_attachments_to_html(self, message: discord.Message) -> str:
        result: str = ''
        for attachment in message.attachments:
            result += self.convert_attachment_to_html(attachment)
        return result

    def reaction_to_html(self, reaction: discord.Reaction) -> str:
        emoji: str | discord.Emoji | discord.PartialEmoji = reaction.emoji
        if type(emoji) is str:
            # if it's an emoji str reference, decode it
            match = re.search('<:[^:]+:(?P<emoji_id>.+)>', emoji)
            if match:
                emoji = self.bot.get_emoji(match[0])
        if type(emoji) is discord.Emoji or type(emoji) is discord.PartialEmoji:
            emoji = f'<img src="{self.copy_asset_locally(str(emoji.id), emoji.url)}">'

        return f"""
                <div class="reaction">
                    <span class="emoji">{emoji}</span> 
                    <span class="count">{reaction.count}</span>
                </div>
                """

    def convert_reactions_to_html(self, message: discord.Message) -> str:
        reactions: str = ''
        for reaction in message.reactions:
            reactions += self.reaction_to_html(reaction)
        return \
            f"""
            <div class="reactions">
              {reactions}
            </div>
            """

    def get_id_from_url(self, url) -> str:
        return url.split('/')[-2]

    async def convert_embed_to_html(self, embed: discord.Embed) -> str:
        result = '<div class="embed">'
        embed_color_style: str = ''
        if embed.colour:
            embed_color_style = f'style="background-color: {embed.colour}"'
        result += f'<div class="embedColorBar" {embed_color_style}></div>'
        result += '<div class="embedContent">'
        if embed.author:
            result += f'<div class="embedAuthor">' \
                      f'  <img src="{embed.author.icon_url}">' \
                      f'  <a href="{embed.author.url}">{embed.author.name}</a>' \
                      f'</div>'
        if embed.title:
            result += f'  <div class="embedTitle">{await self.convert_message_content_to_html(embed.title)}</div>'
        if embed.description:
            result += f'  <div class="embedDescription">{await self.convert_message_content_to_html(embed.description)}</div>'
        if embed.fields:
            for field in embed.fields:
                name_html: str = await self.convert_message_content_to_html(field.name)
                value_html: str = await self.convert_message_content_to_html(field.value)
                if field.inline:
                    result += f'<div class="fieldInline">'
                else:
                    result += f'<div class="field">'

                result += f'<span class="fieldName">{name_html}</span> <span class="fieldValue">{value_html}</span></div>'
        if embed.thumbnail.url:
            result += f'  <div class="embedThumbnail"><img src="{embed.thumbnail.url}"></div>'
        if embed.image.url:
            local_filename = self.copy_asset_locally(self.get_id_from_url(embed.image.url), embed.image.url, embed.image.proxy_url)
            result += f'  <div class="embedImage"><img src="{local_filename}"></div>'
        result += '</div>'
        result += '</div>'
        return result

    async def convert_embeds_to_html(self, message: discord.Message) -> str:
        result: str = ''
        for embed in message.embeds:
            result += await self.convert_embed_to_html(embed)
        return result

    async def convert_default_message_to_html(self, message: discord.Message, coalesce: bool = False) -> str:
        avatar: str = ''
        title: str = ''
        if not coalesce:
            avatar: str = self.get_author_avatar(message.author)
            title: str = self.default_title_to_html(message)
        html_content: str = await self.convert_message_content_to_html(message.content)

        reactions_content: str = ''
        if message.reactions and len(message.reactions) > 0:
            reactions_content = self.convert_reactions_to_html(message)

        attachment_content: str = ''
        if message.attachments and len(message.attachments) > 0:
            attachment_content = self.convert_attachments_to_html(message)

        embeds: str = ''
        if message.embeds and len(message.embeds) > 0:
            embeds = await self.convert_embeds_to_html(message)

        html: str = \
            f"""
            <div class="messageBlock {'' if coalesce else 'mt-20'}">
                <div class="avatar">
                    {avatar}
                </div>
                <div class="content">
                    {title}
                    <div>{html_content}</div>
                    {attachment_content}
                    {embeds}
                    {reactions_content}
                </div>
            </div>
            """
        if message.id in self.thread_id_map:
            html += await self.convert_thread_created_to_html(message)
        return html

    def convert_system_message_to_html(self, message: discord.Message) -> str:
        avatar: str = self.get_author_avatar(None)
        title: str = self.system_title_to_html(message)
        return \
            f"""
            <div class="messageBlock mt-20">
                <div class="avatar">
                    {avatar}
                </div>
                <div class="content">
                   {title}
                </div>
           </div>
           """

    async def convert_thread_created_to_html(self, message: discord.Message) -> str:
        thread = self.thread_id_map[message.id]
        print('Convert Message:', message, thread)
        return \
            f"""
            <div class="messageBlock">
                <div class="avatar">
                    {self.get_author_avatar(None)}
                </div>
                <div class="content">
                    <div class="threadLinkBlock">
                        <div class="threadLinkTitle">
                            <span>{thread.name}</span> 
                            <span><a href="{self.get_thread_document_filename(message.id)}">{thread.message_count} Messages &gt;</a>
                        </div>
                        <div class="threadLinkMessagePreview">
                        </div>
                    </div>
                </div>
            </div>   
            """

    async def convert_message_to_html(self, message: discord.Message, coalesce: bool = False) -> str:
        """
        Delegate to the appropriate HTML generator function based on the MessageType of the message
        :param message:
        :param coalesce:
        :return:
        """
        match message.type:
            case discord.MessageType.new_member:
                return self.convert_system_message_to_html(message)
            case discord.MessageType.thread_created:
                return await self.convert_thread_created_to_html(message)
            case _:
                return await self.convert_default_message_to_html(message, coalesce)

    def should_coalesce_messages(self, last_message: discord.Message | None, curr_message: discord.Message) -> bool:
        """
        A message posted by the same author as the prior message, within 5 minutes of that last message, won't
        repeat the avatar, and the messages should coalesce to appear as one post.
        :param last_message:
        :param curr_message:
        :return:
        """
        if curr_message.interaction:
            return False
        if not last_message:
            return False
        if last_message.author.id != curr_message.author.id:
            return False
        if last_message.created_at.day != curr_message.created_at.day:
            return False
        minutes_diff = (curr_message.created_at - last_message.created_at).total_seconds() // 60
        if minutes_diff > 5:
            return False
        return True

    async def convert_messages_to_html(self) -> None:
        html: str = ''
        last_message: discord.Message | None = None
        for message in self.messages:
            coalesce: bool = self.should_coalesce_messages(last_message, message)
            html += await self.convert_message_to_html(message, coalesce)
            last_message = message

        doc: str = self.doc_template.replace("{body}", html)
        with open(f"{self.output_dir}/{self.document_filename}", "w") as f:
            f.write(doc)

    def zip_contents(self) -> None:
        split_count: int = 0
        zipfile = ZipFile(f"{self.output_dir}/{self.channel.id}_{split_count}.zip", 'w', compresslevel=ZIP_BZIP2)
        for file in os.listdir(f'{self.output_dir}'):
            if file.split('.')[-1] == 'html':
                zipfile.write(f'{self.output_dir}/{file}', f'{file}')
                if os.path.getsize(f"{self.output_dir}/{self.channel.id}_{split_count}.zip") > 20000000:
                    split_count += 1
                    zipfile = ZipFile(f"{self.output_dir}/{self.channel.id}_{split_count}.zip", 'w', compresslevel=ZIP_BZIP2)

        zipfile.write(f"{self.output_dir}/assets/", "assets/")
        for file in os.listdir(f'{self.output_dir}/assets/'):
            zipfile.write(f'{self.output_dir}/assets/{file}', f'assets/{file}')
            if os.path.getsize(f"{self.output_dir}/{self.channel.id}_{split_count}.zip") > 20000000:
                split_count += 1
                zipfile = ZipFile(f"{self.output_dir}/{self.channel.id}_{split_count}.zip", 'w', compresslevel=ZIP_BZIP2)

    async def send_zips_to_channel(self) -> None:
        await self.channel.send("Backup of Channel Completed.  Zip(s) will be posted below.")
        for file in os.listdir(f'{self.output_dir}'):
            print('file', file, file.split('.')[-1])
            if file.split('.')[-1] == 'zip':
                print('send file')
                discord_file = discord.File(self.output_dir + '/' + file, filename=file)
                await self.channel.send(file=discord_file)

    async def export_threads(self) -> None:
        for thread_id in self.thread_id_map.keys():
            print('thread id', thread_id)
            thread = self.thread_id_map[thread_id]
            # print("Export Thread: ", thread.name, thread.id)
            thread_channel = thread
            converter = ChannelExporter(self.bot, thread_channel, self.output_dir)
            converter.document_filename = self.get_thread_document_filename(thread.id)
            await converter.get_all_messages()
            await converter.convert_messages_to_html()

    async def cache_thread_message_ids(self) -> None:
        """
        There is nothing on a message itself that indicates it started a thread, so we need to check if the
        message id matches a thread id.  We'll cache this upfront to avoid costly API calls to look this up
        per message being exported.
        :return:
        """
        async for thread in self.channel.archived_threads(limit=None):
            print('thread_archive: ', type(thread), thread)
            self.thread_id_map[thread.id] = thread

        for thread in self.channel.threads:
            self.thread_id_map[thread.id] = thread


    async def export(self) -> None:
        self.create_output_dirs()
        await self.cache_thread_message_ids()
        await self.get_all_messages()
        await self.convert_messages_to_html()
        await self.export_threads()
        self.zip_contents()
        # await self.send_zips_to_channel()
