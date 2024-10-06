from utils.platform_base import PlatformBase

class Platforms:
    def __init__(self):
        self.__platforms = {}
        self.__enabled = []

    @property
    def available(self):
        return list(self.__platforms.keys())

    @property
    def enabled(self):
        return self.__enabled

    async def add_platform(self, platform: str, obj: PlatformBase):
        if platform in self.__platforms.keys():
            raise ValueError(f"platform {platform} is already available")

        self.__platforms.update({platform: obj})

    def get_platform(self, platform: str):
        if not platform in self.__platforms.keys():
            raise ValueError(f"platform {platform} is not available")
        if not platform in self.__enabled:
            raise ValueError(f"platform {platform} is not enabled")

        return self.__platforms[platform]

    async def enable_platform(self, platform: str):
        if not platform in self.__platforms.keys():
            raise ValueError(f"platform {platform} is not available")
        if platform in self.__enabled:
            raise ValueError(f"platform {platform} is already enabled")

        self.__enabled.append(platform)

    async def disable_platform(self, platform: str):
        if not platform in self.__platforms.keys():
            raise ValueError(f"platform {platform} is not available")
        if not platform in self.__enabled:
            raise ValueError(f"platform {platform} is not enabled")

        self.__enabled.remove(platform)
