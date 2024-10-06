import room
from host import Host
import ujson as json
import threading
import asyncio
import logging
from aiomultiprocess import Worker
from user import User
from platforms import Platforms
from message import MessageFeatures

class AutoSaveDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = 'data.json'
        self.__save_lock = False

        # Ensure necessary keys exist
        self.update({'rooms': {}, 'emojis': [], 'nicknames': {}, 'blocked': {}, 'banned': {}, 'moderators': [],
                     'avatars': {}, 'experiments': {}, 'experiments_info': {}, 'colors': {}, 'external_bridge': [],
                     'modlogs': {}, 'trusted': [], 'report_threads': {}, 'fullbanned': [], 'exp': {}, 'settings': {},
                     'invites': {}, 'underattack': [], 'rooms_count': {}})
        self.threads = []

        # Load data
        self.load_data()

    @property
    def save_lock(self):
        return self.__save_lock

    @save_lock.setter
    def save_lock(self, save_lock):
        if self.__save_lock:
            raise RuntimeError('already locked')
        self.__save_lock = save_lock

    def load_data(self):
        try:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
            self.update(data)
        except FileNotFoundError:
            pass  # If the file is not found, initialize an empty dictionary

    def save(self):
        if self.__save_lock:
            return
        with open(self.file_path, 'w') as file:
            json.dump(self, file, indent=4)
        return

    def cleanup(self):
        for thread in self.threads:
            thread.join()
        count = len(self.threads)
        self.threads.clear()
        return count

    def save_data(self):
        if self.__save_lock:
            return
        thread = threading.Thread(target=self.save)
        thread.start()
        self.threads.append(thread)

class Harmony:
    def __init__(self, bot, host_platform, host_platform_obj):
        self.__host = bot
        self.__host_platform = host_platform
        self.__host_public = Host(self.__host, host_platform)
        self.__data = AutoSaveDict() # this should be kept private to prevent tampering
        self.__platforms = Platforms()

        # add host platform
        self.__platforms.add_platform(self.__host_platform, host_platform_obj)

    @property
    def platforms(self):
        return self.__platforms

    @property
    def host(self):
        return self.__host_public

    @property
    def host_platform(self):
        return self.__host_platform

    async def _send_bridge_platform(self, target, platform, content, user: User = None,
                                    specials: MessageFeatures = None):
        if not platform in self.__platforms.enabled:
            raise ValueError(f"platform {platform} is not enabled")

        support = self.__platforms.get_platform(platform)

        embeds = []
        if len(specials.embeds) > 0:
            embeds = await support.to_embeds(specials.embeds)

        files = []
        if len(specials.attachments) > 0:
            files = await support.to_files(specials.attachments)

        threads = []

        for server in target.servers[platform]:
            if support.multicore:
                # noinspection PyTypeChecker
                threads.append(
                    Worker(
                        target=support.send,
                        args=(
                            target, platform, content, user, embeds, files
                        ),
                        kwargs={
                            "server": server
                        }
                    )
                )
                threads[len(threads) - 1].start()
            else:
                threads.append(
                    asyncio.create_task(
                        support.send(target, platform, content, user, embeds, files, server=server)
                    )
                )

        results = []
        if support.multicore:
            for thread in threads:
                results.append(await thread.join())
        else:
            results = await asyncio.gather(*threads)

        return results

    async def _send_bot_platform(self, target, platform, content, specials: MessageFeatures = None):
        if not platform in self.__platforms.enabled:
            raise ValueError(f"platform {platform} is not enabled")

        support = self.__platforms.get_platform(platform)
        await support.send(target, content, specials)

    async def send_bridge(self, target, content, user: User = None, specials: MessageFeatures = None):
        """Send a message to the room associated with the channel."""
        content = str(content)

        if not target.can_message:
            raise ValueError("cannot message this destination")

        if not target.is_room:
            raise ValueError("target must be a room")

        if specials is None:
            specials = MessageFeatures()

    async def send_bot(self, target, content, specials):
        """Send a message to a user or channel as the bot."""
        content = str(content)

        if not target.can_message:
            raise ValueError("cannot message this destination")

        if target.is_room:
            raise ValueError("target must not be a room")
