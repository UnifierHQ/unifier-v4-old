class Host:
    def __init__(self, bridge, host, platform):
        self.__host = host
        self.__platform = platform
        self.__platform_support = bridge.platforms.get_platform(platform)

    @property
    def platform(self):
        return self.__platform

    @property
    def id(self):
        return self.__platform_support.bot_id()

    @property
    def name(self):
        return self.__platform_support.bot_name()

    @property
    def display_name(self):
        return self.__platform_support.bot_display_name() or self.__platform_support.bot_name()

    async def execute(self, *args, **kwargs):
        return await self.__platform_support.execute(*args, **kwargs)
