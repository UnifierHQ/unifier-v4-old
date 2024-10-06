from messageable import Messageable
from typing import Union

class Channel(Messageable):
    def __init__(self, bridge, channel_id: Union[int, str], name: str = None):
        super().__init__(bridge, False)
        self.__id = channel_id
        self.__name = name

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name
