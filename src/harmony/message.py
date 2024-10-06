from typing import Union

class MessageSource:
    def __init__(self, platform: str, server: Union[int, str], channel: Union[int, str]):
        self.__platform = platform
        self.__server = server
        self.__channel = channel

    @property
    def platform(self):
        return self.__platform

    @property
    def server(self):
        return self.__server

    @property
    def channel(self):
        return self.__channel

class Attachment:
    def __init__(self, fp: Union[bytes, str], filename: str = None, spoiler: bool = False):
        if isinstance(fp, str):
            with open(fp, "rb") as f:
                fp = f.read()

        self.fp = fp
        self.filename = filename
        self.spoiler = spoiler

class MessageFeatures:
    def __init__(self, embeds: Union[list, object] = None, attachments: Union[list, object] = None,
                 reply: Union[int, str] = None):
        if not isinstance(embeds, list):
            embeds = [embeds]
        if not isinstance(attachments, list):
            attachments = [attachments]

        self.embeds = embeds or []
        self.attachments = attachments or []
        self.reply = reply

class Message:
    def __init__(self, message_id: Union[int, str, None], children: dict, source: Union[MessageSource, dict]):
        if isinstance(source, dict):
            source = MessageSource(**source)

        self.__id = message_id
        self.__children = children
        self.__source = source
        self.__orphan = message_id is None

    @property
    def id(self):
        return self.__id

    @property
    def children(self):
        return self.__children

    @property
    def source(self):
        return self.__source

    @property
    def orphan(self):
        return self.__orphan

    async def fetch_id(self, server_id: Union[int, str], platform: str = None):
        if server_id == self.__source.server:
            return self.__id

        # platform isn't really needed, only for minor speedups
        if platform:
            return self.__children[platform][server_id]

        for platform in self.__children:
            if server_id in self.__children[platform]:
                return self.__children[platform][server_id]

        return None
