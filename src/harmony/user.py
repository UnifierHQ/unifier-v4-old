from messageable import Messageable
from typing import Union

class User(Messageable):
    def __init__(self, bridge, user_id: Union[int, str], username: str = None, display_name: str = None):
        super().__init__(bridge, False)
        self.__id = user_id
        self.__username = username
        self.__display_name = display_name

    @property
    def id(self):
        return self.__id

    @property
    def username(self):
        return self.__username

    @property
    def display_name(self):
        # user's display name is either their display name or their username
        return self.__display_name or self.__username

class SystemUser(User):
    def __init__(self, bridge):
        super().__init__(bridge, bridge.host.id, bridge.host.name, bridge.host.display_name)
        self.__can_message = False
