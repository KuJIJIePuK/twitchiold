"""
The MIT License (MIT)

Copyright (c) 2017-2021 TwitchIO

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import abc
import time
from asyncio import sleep

from .cooldowns import RateBucket
from .errors import *


class IRCLimiterMapping:
    def __init__(self):
        self.buckets = {}

    def get_bucket(self, channel: str, method: str) -> RateBucket:
        try:
            bucket = self.buckets[channel]
        except KeyError:
            bucket = RateBucket(method=method)
            self.buckets[channel] = bucket

        if bucket.method != method:
            bucket.method = method
            bucket.limit = bucket.MODLIMIT if method == "mod" else bucket.IRCLIMIT
            self.buckets[channel] = bucket

        return bucket


limiter = IRCLimiterMapping()


class Messageable(abc.ABC):

    __slots__ = ()

    @abc.abstractmethod
    def _fetch_channel(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _fetch_websocket(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _fetch_message(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _bot_is_mod(self):
        raise NotImplementedError

    def check_bucket(self, channel):
        mod = self._bot_is_mod()

        if mod:
            bucket = limiter.get_bucket(channel=channel, method="mod")
        else:
            bucket = limiter.get_bucket(channel=channel, method="irc")

        now = time.time()
        bucket.update()

        if bucket.limited:
            raise IRCCooldownError(
                f"IRC Message rate limit reached for channel <{channel}>."
                f" Please try again in {bucket._reset - now:.2f}s"
            )

    def check_content(self, content: str):
        if len(content) > 500:
            raise InvalidContent("Content must not exceed 500 characters.")

    async def send(self, content: str):
        """|coro|

        Send a message to the destination associated with the dataclass.

        Destination will either be a channel or user.

        Parameters
        ------------
        content: str
            The content you wish to send as a message. The content must be a string.

        Raises
        --------
        InvalidContent
            Invalid content.
        """
        entity = self._fetch_channel()
        ws = self._fetch_websocket()

        self.check_content(content)
        self.check_bucket(channel=entity.name)

        try:
            name = entity.channel.name
        except AttributeError:
            name = entity.name

        if entity.__messageable_channel__:
            await ws.send(f"PRIVMSG #{name} :{content}\r\n")
        else:
            await ws.send(f"PRIVMSG #jtv :/w {entity.name} {content}\r\n")

    async def followers(self, time = 0, delay = 0):
        await sleep(delay)
        await self.send(f'.followers {time}')

    async def followersoff(self, delay = 0):
        await sleep(delay)
        await self.send(f'.followersoff')

    async def ban(self, user = '', reason = '', delay = 0):
        await sleep(delay)
        if not reason.startswith(' '):
            reason = f' {reason}'
        await self.send(f'.ban {user}{reason}')

    async def unban(self, user = '', delay = 0):
        await sleep(delay)
        await self.send(f'.unban {user}')

    async def timeout(self, user = '', time = 0, reason = '',delay = 0):
        await sleep(delay)
        if not reason.startswith(' '):
            reason = f' {reason}'
        await self.send(f'.timeout {user} {time}{reason}')

    async def untimeout(self, user = '', delay = 0):
        await sleep(delay)
        await self.send(f'.untimeout {user}')

    async def delete(self, m_id = '', delay = 0):
        await sleep(delay)
        await self.send(f'.delete {m_id}')

    async def me(self, content = '', delay = 0):
        await sleep(delay)
        await self.send(f'.me {content}')

    async def clear(self, delay = 0):
        await sleep(delay)
        await self.send(f'.clear')

    async def emoteonly(self, delay = 0):
        await sleep(delay)
        await self.send(f'.emoteonly')

    async def emoteonlyoff(self, delay = 0):
        await sleep(delay)
        await self.send(f'.emoteonlyoff')

    async def r9kbeta(self, delay = 0):
        await sleep(delay)
        await self.send(f'.r9kbeta')

    async def r9kbetaoff(self, delay = 0):
        await sleep(delay)
        await self.send(f'.r9kbetaoff')

    async def slow(self, time = 0, delay = 0):
        await sleep(delay)
        await self.send(f'.slow {time}')

    async def slowoff(self, delay = 0):
        await sleep(delay)
        await self.send(f'.slowoff')

    async def subscribers(self, delay = 0):
        await sleep(delay)
        await self.send(f'.subscribers')

    async def subscribersoff(self, delay = 0):
        await sleep(delay)
        await self.send(f'.subscribersoff')


    async def reply(self, content: str):
        """|coro|


        Send a message in reply to the user who sent a message in the destination
        associated with the dataclass.

        Destination will be the context of which the message/command was sent.

        Parameters
        ------------
        content: str
            The content you wish to send as a message. The content must be a string.

        Raises
        --------
        InvalidContent
            Invalid content.
        """
        entity = self._fetch_channel()
        ws = self._fetch_websocket()
        message = self._fetch_message()

        self.check_content(content)
        self.check_bucket(channel=entity.name)

        try:
            name = entity.channel.name
        except AttributeError:
            name = entity.name

        if entity.__messageable_channel__:
            await ws.reply(message.id, f"PRIVMSG #{name} :{content}\r\n")
        else:
            await ws.send(f"PRIVMSG #jtv :/w {name} {content}\r\n")
