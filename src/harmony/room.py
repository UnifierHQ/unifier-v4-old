from user import User
from messageable import Messageable

class Room(Messageable):
    def __init__(self, bridge, name, display_name, emoji, servers):
        super().__init__(bridge, True)
        self.__bridge = bridge
        self.__name = name
        self.__display_name = display_name
        self.__emoji = emoji
        self.__servers = servers

    @property
    def name(self):
        return self.__name

    @property
    def display_name(self):
        return self.__display_name

    @property
    def emoji(self):
        return self.__emoji

    @property
    def servers(self):
        return self.__servers
