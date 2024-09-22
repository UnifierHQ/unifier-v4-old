"""
Unifier - A sophisticated Discord bot uniting servers and platforms
Copyright (C) 2023-present  UnifierHQ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import nextcord
from nextcord.ext import commands
import traceback
import re
from utils import log, ui, restrictions as r
import math
import random
import string
import emoji as pymoji
import time

restrictions = r.Restrictions()

def timetoint(t):
    try:
        return int(t)
    except:
        pass
    if not type(t) is str:
        t = str(t)
    total = 0
    if t.count('d')>1 or t.count('w')>1 or t.count('h')>1 or t.count('m')>1 or t.count('s')>1:
        raise ValueError('each identifier should never recur')
    t = t.replace('n','n ').replace('d','d ').replace('w','w ').replace('h','h ').replace('m','m ').replace('s','s ')
    times = t.split()
    for part in times:
        if part.endswith('d'):
            multi = int(part[:-1])
            total += (86400 * multi)
        elif part.endswith('w'):
            multi = int(part[:-1])
            total += (604800 * multi)
        elif part.endswith('h'):
            multi = int(part[:-1])
            total += (3600 * multi)
        elif part.endswith('m'):
            multi = int(part[:-1])
            total += (60 * multi)
        elif part.endswith('s'):
            multi = int(part[:-1])
            total += multi
        else:
            raise ValueError('invalid identifier')
    return total

class Config(commands.Cog, name=':construction_worker: Config'):
    """Config is an extension that lets Unifier admins configure the bot and server moderators set up Unified Chat in their server.

    Developed by Green and ItsAsheer"""

    def __init__(self,bot):
        self.bot = bot
        if not hasattr(self.bot, 'bridged_emojis'):
            if not 'emojis' in list(self.bot.db.keys()):
                self.bot.db.update({'emojis':[]})
                self.bot.db.save_data()
            self.bot.bridged_emojis = self.bot.db['emojis']
        self.bot.admins = self.bot.config['admin_ids']
        self.bot.moderators = self.bot.admins + self.bot.db['moderators']
        if not hasattr(self.bot, 'trusted_group'):
            self.bot.trusted_group = self.bot.db['trusted']
        restrictions.attach_bot(self.bot)
        self.logger = log.buildlogger(self.bot.package, 'upgrader', self.bot.loglevel)

    def can_manage(self, user, room):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            try:
                room = self.bot.bridge.get_invite(room)['room']
            except:
                return False

        roominfo = self.bot.bridge.get_room(room)
        if not roominfo:
            return False

        if roominfo['meta']['private']:
            return (
                    user.guild_permissions.manage_channels and user.guild.id == roominfo['meta']['private_meta']['server']
            ) or (
                    user.id in self.bot.moderators or
                    user.id in self.bot.admins or
                    user.id == self.bot.owner
            )
        else:
            return (
                    user.id in self.bot.admins or
                    user.id == self.bot.owner
            )

    def can_moderate(self, user, room):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            try:
                room = self.bot.bridge.get_invite(room)['room']
            except:
                return False

        roominfo = self.bot.bridge.get_room(room)
        if not roominfo:
            return False

        if roominfo['meta']['private']:
            return (
                    user.guild_permissions.ban_members and user.guild.id == roominfo['meta']['private_meta']['server']
            ) or (
                    user.id in self.bot.moderators or
                    user.id in self.bot.admins or
                    user.id == self.bot.owner
            )
        else:
            return (
                    user.id in self.bot.admins or
                    user.id == self.bot.owner
            )

    def can_join(self, user, room):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            try:
                self.bot.bridge.get_invite(room)
                return True
            except:
                return False

        roominfo = self.bot.bridge.get_room(room)
        if not roominfo:
            return False

        if roominfo['meta']['private']:
            return (
                    user.guild.id in roominfo['meta']['private_meta']['allowed'] or
                    user.guild.id == roominfo['meta']['private_meta']['server']
            )
        else:
            return True

    def is_user_admin(self,user_id):
        try:
            if user_id in self.bot.config['admin_ids']:
                return True
            else:
                return False
        except:
            traceback.print_exc()
            return False

    def is_room_restricted(self, room, db):
        try:
            if db['rooms'][room]['meta']['restricted']:
                return True
            else:
                return False
        except:
            traceback.print_exc()
            return False

    def is_room_locked(self, room, db):
        try:
            if db['rooms'][room]['meta']['locked']:
                return True
            else:
                return False
        except:
            traceback.print_exc()
            return False

    async def roomslist(self, ctx, private):
        show_restricted = False
        show_locked = False

        if ctx.author.id in self.bot.admins:
            show_restricted = True
            show_locked = True
        elif ctx.author.id in self.bot.moderators:
            show_locked = True

        panel = 0
        limit = 8
        page = 0
        match = 0
        namematch = False
        descmatch = False
        was_searching = False
        roomname = ''
        query = ''
        msg = None
        interaction = None
        ignore_mod = True

        while True:
            embed = nextcord.Embed(color=self.bot.colors.unifier)
            maxpage = 0
            components = ui.MessageComponents()

            if panel == 0:
                was_searching = False
                search_roomlist = self.bot.bridge.rooms
                roomlist = []
                for search_room in search_roomlist:
                    # yes, this logic is messy.
                    # but it doesn't overwrite the origin server thing so i'm keeping it for now
                    if private:
                        if not self.bot.db['rooms'][search_room]['meta']['private']:
                            continue
                        elif not self.bot.bridge.can_access_room(search_room, ctx.author, ignore_mod=ignore_mod):
                            continue
                    else:
                        if self.bot.db['rooms'][search_room]['meta']['private']:
                            continue
                        elif not show_restricted and self.is_room_restricted(search_room, self.bot.db):
                            continue
                        elif not show_locked and self.is_room_locked(search_room, self.bot.db):
                            continue
                    roomlist.append(search_room)

                maxpage = math.ceil(len(roomlist) / limit) - 1
                if interaction:
                    if page > maxpage:
                        page = maxpage
                embed.title = (
                    f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms' if not private
                    else f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} private rooms'
                )
                embed.description = 'Choose a room to view its info!'
                selection = nextcord.ui.StringSelect(
                    max_values=1, min_values=1, custom_id='selection', placeholder='Room...'
                )

                for x in range(limit):
                    index = (page * limit) + x
                    if index >= len(roomlist):
                        break
                    try:
                        # redundant try-except block
                        name = roomlist[index]
                    except:
                        break
                    display_name = (
                            self.bot.db['rooms'][name]['meta']['display_name'] or name
                    )
                    description = (
                            self.bot.db['rooms'][name]['meta']['description'] or 'This room has no description.'
                    )
                    emoji = (
                        '\U0001F527' if self.is_room_restricted(roomlist[index], self.bot.db) else
                        '\U0001F512' if self.is_room_locked(roomlist[index], self.bot.db) else
                        '\U0001F310'
                    ) if not self.bot.db['rooms'][name]['meta']['emoji'] else self.bot.db['rooms'][name]['meta'][
                        'emoji']

                    embed.add_field(
                        name=f'{emoji} '+(
                            f'{display_name} (`{name}`)' if self.bot.db['rooms'][name]['meta']['display_name'] else
                            f'`{display_name}`'
                        ),
                        value=description,
                        inline=False
                    )
                    selection.add_option(
                        label=display_name,
                        emoji=emoji,
                        description=description,
                        value=name
                    )

                if len(embed.fields) == 0:
                    embed.add_field(
                        name='No rooms',
                        value='There\'s no rooms here!',
                        inline=False
                    )
                    selection.add_option(
                        label='placeholder',
                        value='placeholder'
                    )
                    selection.disabled = True

                components.add_rows(
                    ui.ActionRow(
                        selection
                    ),
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.blurple,
                            label='Previous',
                            custom_id='prev',
                            disabled=page <= 0 or selection.disabled,
                            emoji=self.bot.ui_emojis.prev
                        ),
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.blurple,
                            label='Next',
                            custom_id='next',
                            disabled=page >= maxpage or selection.disabled,
                            emoji=self.bot.ui_emojis.next
                        ),
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.green,
                            label='Search',
                            custom_id='search',
                            emoji=self.bot.ui_emojis.search,
                            disabled=selection.disabled
                        )
                    )
                )

                if ctx.author.id in self.bot.moderators and private:
                    components.add_row(
                        ui.ActionRow(
                            nextcord.ui.Button(
                                style=nextcord.ButtonStyle.gray,
                                label='Show all rooms' if ignore_mod else 'Hide inaccessible rooms',
                                custom_id='viewall'
                            )
                        )
                    )
            elif panel == 1:
                was_searching = True
                search_roomlist = list(self.bot.db['rooms'].keys())

                def search_filter(query, query_cmd):
                    if match == 0:
                        return (
                                (
                                        query.lower() in (
                                            self.bot.db['rooms'][query_cmd]['meta']['display_name'] or query_cmd
                                        )
                                ) and namematch or
                                (
                                    query.lower() in self.bot.db['rooms'][query_cmd]['meta']['description'].lower()
                                    if self.bot.db['rooms'][query_cmd]['meta']['description'] else False
                                ) and descmatch
                        )
                    elif match == 1:
                        return (
                                (((
                                          query.lower() in (
                                              self.bot.db['rooms'][query_cmd]['meta']['display_name'] or query_cmd
                                          )
                                  ) and namematch) or not namematch) and
                                ((
                                     query.lower() in self.bot.db['rooms'][query_cmd]['meta']['description'].lower()
                                     if self.bot.db['rooms'][query_cmd]['meta']['description'] else False
                                 ) and descmatch or not descmatch)
                        )

                roomlist = []
                for search_room in search_roomlist:
                    # yes, this logic is messy.
                    # but it doesn't overwrite the origin server thing so i'm keeping it for now
                    if private:
                        if not self.bot.db['rooms'][search_room]['meta']['private']:
                            continue
                        elif not self.bot.bridge.can_access_room(search_room, ctx.author, ignore_mod=ignore_mod):
                            continue
                    else:
                        if self.bot.db['rooms'][search_room]['meta']['private']:
                            continue
                        elif not show_restricted and self.is_room_restricted(search_room, self.bot.db):
                            continue
                        elif not show_locked and self.is_room_locked(search_room, self.bot.db):
                            continue
                    roomlist.append(search_room)

                embed.title = f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms / search'
                embed.description = 'Choose a room to view its info!'

                if len(roomlist) == 0:
                    maxpage = 0
                    embed.add_field(
                        name='No rooms',
                        value='There are no rooms matching your search query.',
                        inline=False
                    )
                    selection = nextcord.ui.StringSelect(
                        max_values=1, min_values=1, custom_id='selection', placeholder='Room...', disabled=True
                    )
                    selection.add_option(
                        label='No rooms'
                    )
                else:
                    maxpage = math.ceil(len(roomlist) / limit) - 1
                    selection = nextcord.ui.StringSelect(
                        max_values=1, min_values=1, custom_id='selection', placeholder='Room...'
                    )

                    roomlist = await self.bot.loop.run_in_executor(None, lambda: sorted(
                        roomlist,
                        key=lambda x: x.lower()
                    ))

                    for x in range(limit):
                        index = (page * limit) + x
                        if index >= len(roomlist):
                            break
                        room = roomlist[index]
                        display_name = (
                                self.bot.db['rooms'][room]['meta']['display_name'] or room
                        )
                        emoji = (
                            '\U0001F527' if self.is_room_restricted(roomlist[index], self.bot.db) else
                            '\U0001F512' if self.is_room_locked(roomlist[index], self.bot.db) else
                            '\U0001F310'
                        ) if not self.bot.db['rooms'][room]['meta']['emoji'] else self.bot.db['rooms'][room]['meta'][
                            'emoji']
                        roomdesc = (
                            self.bot.db['rooms'][room]['meta']['description']
                            if self.bot.db['rooms'][room]['meta']['description'] else 'This room has no description.'
                        )
                        embed.add_field(
                            name=f'{emoji} ' + (
                                f'{display_name} (`{room}`)' if self.bot.db['rooms'][room]['meta']['display_name'] else
                                f'`{display_name}`'
                            ),
                            value=roomdesc,
                            inline=False
                        )
                        selection.add_option(
                            label=display_name,
                            description=roomdesc if len(roomdesc) <= 100 else roomdesc[:-(len(roomdesc) - 97)] + '...',
                            value=room,
                            emoji=emoji
                        )

                embed.description = f'Searching: {query} (**{len(roomlist)}** results)'
                maxcount = (page + 1) * limit
                if maxcount > len(roomlist):
                    maxcount = len(roomlist)
                embed.set_footer(
                    text=(
                            f'Page {page + 1} of {maxpage + 1} | {page * limit + 1}-{maxcount} of {len(roomlist)}' +
                            ' results'
                    )
                )

                components.add_row(
                    ui.ActionRow(
                        selection
                    )
                )

                components.add_row(
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.blurple,
                            label='Previous',
                            custom_id='prev',
                            disabled=page <= 0,
                            emoji=self.bot.ui_emojis.prev
                        ),
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.blurple,
                            label='Next',
                            custom_id='next',
                            disabled=page >= maxpage,
                            emoji=self.bot.ui_emojis.next
                        ),
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.green,
                            label='Search',
                            custom_id='search',
                            emoji=self.bot.ui_emojis.search
                        )
                    )
                )
                components.add_row(
                    ui.ActionRow(
                        nextcord.ui.Button(
                            custom_id='match',
                            label=(
                                'Matches any of' if match == 0 else
                                'Matches both'
                            ),
                            style=(
                                nextcord.ButtonStyle.green if match == 0 else
                                nextcord.ButtonStyle.blurple
                            ),
                            emoji=(
                                '\U00002194' if match == 0 else
                                '\U000023FA'
                            )
                        ),
                        nextcord.ui.Button(
                            custom_id='name',
                            label='Room name',
                            style=nextcord.ButtonStyle.green if namematch else nextcord.ButtonStyle.gray
                        ),
                        nextcord.ui.Button(
                            custom_id='desc',
                            label='Room description',
                            style=nextcord.ButtonStyle.green if descmatch else nextcord.ButtonStyle.gray
                        )
                    )
                )
                components.add_row(
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.gray,
                            label='Back',
                            custom_id='back',
                            emoji=self.bot.ui_emojis.back
                        )
                    )
                )
            elif panel == 2:
                embed.title = (
                    f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms / search / {roomname}'
                    if was_searching else
                    f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms / {roomname}'
                )
                display_name = (
                        self.bot.db['rooms'][roomname]['meta']['display_name'] or roomname
                )
                description = (
                        self.bot.db['rooms'][roomname]['meta']['description'] or 'This room has no description.'
                )
                emoji = (
                    '\U0001F527' if self.is_room_restricted(roomname, self.bot.db) else
                    '\U0001F512' if self.is_room_locked(roomname, self.bot.db) else
                    '\U0001F310'
                ) if not self.bot.db['rooms'][roomname]['meta']['emoji'] else self.bot.db['rooms'][roomname]['meta'][
                    'emoji']
                if self.bot.db['rooms'][roomname]['meta']['display_name']:
                    embed.description = f'# **{emoji} {display_name}**\n`{roomname}`\n\n{description}'
                else:
                    embed.description = f'# **{emoji} `{display_name}`**\n{description}'
                stats = await self.bot.bridge.roomstats(roomname)
                embed.add_field(name='Statistics', value=(
                        f':homes: {stats["guilds"]} servers\n' +
                        f':green_circle: {stats["online"]} online, :busts_in_silhouette: {stats["members"]} members\n' +
                        f':speech_balloon: {stats["messages"]} messages sent today'
                ))
                components.add_rows(
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.blurple,
                            label='View room rules',
                            custom_id='rules',
                        )
                    ),
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.gray,
                            label='Back',
                            custom_id='back',
                            emoji=self.bot.ui_emojis.back
                        )
                    )
                )
            elif panel == 3:
                embed.title = (
                    f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms / search / {roomname} / rules'
                    if was_searching else
                    f'{self.bot.ui_emojis.rooms} {self.bot.user.global_name or self.bot.user.name} rooms / {roomname} / rules'
                )
                index = 0
                text = ''
                if roomname in list(self.bot.db['rules'].keys()):
                    rules = self.bot.db['rules'][roomname]
                else:
                    rules = []
                for rule in rules:
                    if text == '':
                        text = f'1. {rule}'
                    else:
                        text = f'{text}\n{index}. {rule}'
                    index += 1
                if len(rules) == 0:
                    text = (
                            'The room admins haven\'t added rules for this room yet.\n' +
                            'Though, do remember to use common sense and refrain from doing things that you shouldn\'t do.'
                    )
                embed.description = text
                components.add_rows(
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.gray,
                            label='Back',
                            custom_id='back',
                            emoji=self.bot.ui_emojis.back
                        )
                    )
                )

            if panel == 0:
                embed.set_footer(text=f'Page {page + 1} of {maxpage + 1}')
            if not msg:
                msg = await ctx.send(embed=embed, view=components, reference=ctx.message, mention_author=False)
            else:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=components)
            embed.clear_fields()

            def check(interaction):
                return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

            try:
                interaction = await self.bot.wait_for('interaction', check=check, timeout=60)
            except:
                try:
                    await msg.edit(view=None)
                except:
                    pass
                break
            if interaction.type == nextcord.InteractionType.component:
                if interaction.data['custom_id'] == 'selection':
                    roomname = interaction.data['values'][0]
                    panel = 2
                    page = 0
                elif interaction.data['custom_id'] == 'back':
                    panel -= 1
                    if panel < 0 or panel == 1 and not was_searching:
                        panel = 0
                    page = 0
                elif interaction.data['custom_id'] == 'rules':
                    panel += 1
                elif interaction.data['custom_id'] == 'prev':
                    page -= 1
                elif interaction.data['custom_id'] == 'next':
                    page += 1
                elif interaction.data['custom_id'] == 'search':
                    modal = nextcord.ui.Modal(title='Search...', auto_defer=False)
                    modal.add_item(
                        nextcord.ui.TextInput(
                            label='Search query',
                            style=nextcord.TextInputStyle.short,
                            placeholder='Type something...'
                        )
                    )
                    await interaction.response.send_modal(modal)
                elif interaction.data['custom_id'] == 'match':
                    match += 1
                    if match > 1:
                        match = 0
                elif interaction.data['custom_id'] == 'name':
                    namematch = not namematch
                    if not namematch and not descmatch:
                        namematch = True
                elif interaction.data['custom_id'] == 'desc':
                    descmatch = not descmatch
                    if not namematch and not descmatch:
                        descmatch = True
                elif interaction.data['custom_id'] == 'viewall':
                    ignore_mod = not ignore_mod
            elif interaction.type == nextcord.InteractionType.modal_submit:
                panel = 1
                query = interaction.data['components'][0]['components'][0]['value']
                namematch = True
                descmatch = True
                match = 0
                page = 0

    @commands.command(hidden=True,description='Adds a moderator to the instance.')
    @restrictions.admin()
    async def addmod(self,ctx,*,userid):
        try:
            userid = int(userid)
        except:
            try:
                userid = int(userid.replace('<@','',1).replace('!','',1).replace('>','',1))
            except:
                return await ctx.send(f'{self.bot.ui_emojis.error} Not a valid user!')
        user = self.bot.get_user(userid)
        if user==None:
            return await ctx.send(f'{self.bot.ui_emojis.error} Not a valid user!')
        if userid in self.bot.db['moderators']:
            return await ctx.send(f'{self.bot.ui_emojis.error} This user is already a moderator!')
        if self.is_user_admin(userid) or user.bot:
            return await ctx.send('are you fr')
        self.bot.db['moderators'].append(userid)
        self.bot.moderators.append(userid)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        mod = f'{user.name}#{user.discriminator}'
        if user.discriminator=='0':
            mod = f'@{user.name}'
        await ctx.send(f'{self.bot.ui_emojis.success} **{mod}** is now a moderator!')

    @commands.command(hidden=True,aliases=['remmod','delmod'],description='Removes a moderator from the instance.')
    @restrictions.admin()
    async def removemod(self,ctx,*,userid):
        try:
            userid = int(userid)
        except:
            try:
                userid = int(userid.replace('<@','',1).replace('!','',1).replace('>','',1))
            except:
                return await ctx.send(f'{self.bot.ui_emojis.error} Not a valid user!')
        user = self.bot.get_user(userid)
        if user==None:
            return await ctx.send(f'{self.bot.ui_emojis.error} Not a valid user!')
        if not userid in self.bot.db['moderators']:
            return await ctx.send(f'{self.bot.ui_emojis.error} This user is not a moderator!')
        if self.is_user_admin(userid):
            return await ctx.send('are you fr')
        self.bot.db['moderators'].remove(userid)
        self.bot.moderators.remove(userid)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        mod = f'{user.name}#{user.discriminator}'
        if user.discriminator=='0':
            mod = f'@{user.name}'
        await ctx.send(f'{self.bot.ui_emojis.success} **{mod}** is no longer a moderator!')

    @commands.command(hidden=True, aliases=['newroom'],description='Creates a new room.')
    @restrictions.can_create()
    @restrictions.not_banned()
    async def make(self,ctx,*,room=None):
        roomtype = 'private'
        dry_run = False

        if room:
            if room.startswith('-dry-run'):
                if room == '-dry-run':
                    room = None
                dry_run = ctx.author.id == self.bot.owner

        if room:
            room = room.lower().replace(' ','-')
            if not bool(re.match("^[A-Za-z0-9_-]*$", room)):
                return await ctx.send(
                    f'{self.bot.ui_emojis.error} Room names may only contain alphabets, numbers, dashes, and underscores.'
                )

        interaction = None
        if ctx.author.id in self.bot.admins or ctx.author.id == self.bot.config['owner']:
            if not self.bot.config['enable_private_rooms']:
                roomtype = 'public'
            else:
                components = ui.MessageComponents()
                components.add_rows(
                    ui.ActionRow(
                        nextcord.ui.StringSelect(
                            options=[
                                nextcord.SelectOption(
                                    value='private',
                                    label='Private',
                                    description='Make a room just for me and my buddies.',
                                    emoji='\U0001F512'
                                ),
                                nextcord.SelectOption(
                                    value='public',
                                    label='Public',
                                    description='Make a room for everyone to talk in.',
                                    emoji='\U0001F310'
                                )
                            ],
                            custom_id='selection'
                        )
                    ),
                    ui.ActionRow(
                        nextcord.ui.Button(
                            style=nextcord.ButtonStyle.gray,
                            label='Cancel',
                            custom_id='cancel'
                        )
                    )
                )
                msg = await ctx.send(f'{self.bot.ui_emojis.warning} Please select the room type.',view=components)

                def check(interaction):
                    return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

                try:
                    interaction = await self.bot.wait_for('interaction', check=check, timeout=60)
                    if interaction.data['custom_id'] == 'cancel':
                        return await interaction.response.edit_message(
                            content=f'{self.bot.ui_emojis.error} Aborted.', view=None
                        )
                    else:
                        roomtype = interaction.data['values'][0]
                except:
                    return await msg.edit(content=f'{self.bot.ui_emojis.error} Timed out.', view=None)

        if not self.bot.config['enable_private_rooms'] and roomtype == 'private':
            return await ctx.send(f'{self.bot.ui_emojis.error} Private Rooms are disabled.')

        if not room or roomtype=='private':
            for _ in range(10):
                room = roomtype + '-' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
                if not room in self.bot.bridge.rooms:
                    break
            if room in self.bot.bridge.rooms:
                if interaction:
                    return await interaction.response.edit_message(
                        content=f'{self.bot.ui_emojis.error} Could not generate a unique room name in 10 tries.'
                    )
                return await ctx.send(f'{self.bot.ui_emojis.error} Could not generate a unique room name in 10 tries.')

        if room in list(self.bot.db['rooms'].keys()):
            if interaction:
                return await interaction.response.edit_message(
                    content=f'{self.bot.ui_emojis.error} This room already exists!'
                )
            return await ctx.send(f'{self.bot.ui_emojis.error} This room already exists!')
        try:
            roomdata = self.bot.bridge.create_room(
                room, private=roomtype=='private', dry_run=dry_run, origin=ctx.guild.id
            )
        except self.bot.bridge.TooManyRooms:
            if interaction:
                return await interaction.response.edit_message(
                    content=f'{self.bot.ui_emojis.error} You cannot create any more Private Rooms. The limit is '+
                            f'{self.bot.config["private_rooms_limit"]}.',
                    view=None
                )
            return await ctx.send(
                f'{self.bot.ui_emojis.error} You cannot create any more Private Rooms. The limit is '+
                f'{self.bot.config["private_rooms_limit"]}.'
            )

        dry_run_text = ''
        if dry_run:
            dry_run_text = f'\n```js\n{roomdata}```\n-# {self.bot.ui_emojis.warning} This is a dry run.'

        if interaction:
            return await interaction.response.edit_message(
                content=f'{self.bot.ui_emojis.success} Created **{roomtype}** room `{room}`!{dry_run_text}',
                view=None
            )
        await ctx.send(f'{self.bot.ui_emojis.success} Created **{roomtype}** room `{room}`!{dry_run_text}')

    @commands.command(name='create-invite', hidden=True, description='Creates an invite.')
    @restrictions.not_banned()
    async def create_invite(self, ctx, room, expiry='7d', max_usage=0):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if not self.bot.db['rooms'][room]['meta']['private']:
            return await ctx.send(f'{self.bot.ui_emojis.error} This is a public room.')
        if len(self.bot.db['rooms'][room]['meta']['private_meta']['invites']) >= 20:
            return await ctx.send(
                f'{self.bot.ui_emojis.error} You\'ve reached the limit for invites. Delete some first, then try again.'
            )

        infinite_enabled = ''
        if self.bot.config['permanent_invites']:
            infinite_enabled = ' ' + 'Use `inf` instead for permanent invites.' # concatenated for future localization

        if expiry == 'inf':
            if not self.bot.config['permanent_invites']:
                return await ctx.send(f'{self.bot.ui_emojis.error} Permanent invites are not enabled on this instance.')
            expiry = 0
        else:
            try:
                expiry = timetoint(expiry)
            except:
                return await ctx.send(
                    f'{self.bot.ui_emojis.error} This is not a valid duration string. Try something like `7d` or `24h`.'
                )
            if expiry > 604800:
                return await ctx.send(
                    f'{self.bot.ui_emojis.error} Invites cannot last longer than 7 days.{infinite_enabled}'
                )
            expiry += time.time()
        invite = self.bot.bridge.create_invite(room, max_usage, expiry)
        try:
            await ctx.author.send(
                f'Invite code: `{invite}`\nServers can use `{self.bot.command_prefix}join {invite}` to join your room.'
            )
        except:
            return await ctx.send(
                f'{self.bot.ui_emojis.warning} Invite was created, but it could not be DMed. Turn your DMs on, then '+
                f'run `{self.bot.command_prefix}invites` to view your invite.'
            )
        await ctx.send(f'{self.bot.ui_emojis.success} Invite was created, check your DMs!')

    @commands.command(name='delete-invite', hidden=True, description='Deletes an invite.')
    @restrictions.not_banned()
    async def delete_invite(self, ctx, invite):
        invite = invite.lower()
        if not self.can_manage(ctx.author, invite):
            raise restrictions.NoRoomManagement()
        try:
            self.bot.bridge.delete_invite(invite)
        except self.bot.bridge.InviteNotFoundError:
            return await ctx.send(f'{self.bot.ui_emojis.error} Could not find invite.')
        await ctx.send(f'{self.bot.ui_emojis.success} Invite was deleted.')

    @commands.command(hidden=True, description='Views your room\'s invites.')
    @restrictions.not_banned()
    async def invites(self, ctx, room):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if not self.bot.db['rooms'][room]['meta']['private']:
            return await ctx.send(f'{self.bot.ui_emojis.error} This is a public room.')

        invites = self.bot.db['rooms'][room]['meta']['private_meta']['invites']

        embed = nextcord.Embed(
            title=f'Invites for `{room}`',
        )

        success = 0
        for invite in invites:
            invite_data = self.bot.bridge.get_invite(invite)
            if not invite_data:
                continue
            embed.add_field(
                name=f'`{invite}`',
                value=(
                    'Unlimited usage' if invite_data['remaining'] == 0 else
                    f'Remaining uses: {invite_data["remaining"]}'
                )+'\nExpiry: '+(
                    'never' if invite_data["expire"] == 0 else f'<t:{round(invite_data["expire"])}:R>'
                )
            )
            success += 1

        embed.description = f'{success}/20 invites created'
        try:
            await ctx.author.send(embed=embed)
        except:
            return await ctx.send(f'{self.bot.ui_emojis.error} Could not DM invites. Please turn your DMs on.')
        await ctx.send(f'{self.bot.ui_emojis.success} Invites have been DMed.')

    @commands.command(hidden=True, description='Renames a room.')
    @restrictions.not_banned()
    async def rename(self, ctx, room, newroom):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        newroom = newroom.lower()
        if not room.lower() in list(self.bot.db['rooms'].keys()):
            return await ctx.send(f'{self.bot.ui_emojis.error} This room does not exist!')
        if not bool(re.match("^[A-Za-z0-9_-]*$", newroom)):
            return await ctx.send(f'{self.bot.ui_emojis.error} Room names may only contain alphabets, numbers, dashes, and underscores.')
        if newroom in list(self.bot.db['rooms'].keys()):
            return await ctx.send(f'{self.bot.ui_emojis.error} This room already exists!')
        if self.bot.db['rooms'][room]['meta']['private']:
            return await ctx.send(f'{self.bot.ui_emojis.error} You cannot rename private rooms.')
        self.bot.db['rooms'].update({newroom: self.bot.db['rooms'][room]})
        self.bot.db['rooms'].pop(room)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send(f'{self.bot.ui_emojis.success} Room renamed!')

    @commands.command(name='display-name', hidden=True, description='Sets room display name.')
    @restrictions.not_banned()
    async def display_name(self, ctx, room, *, name=''):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if len(name) == 0:
            if not self.bot.db['rooms'][room]['meta']['display_name']:
                return await ctx.send(f'{self.bot.ui_emojis.error} There is no display name to reset for this room.')
            self.bot.db['rooms'][room]['meta']['display_name'] = None
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            return await ctx.send(f'{self.bot.ui_emojis.success} Display name removed.')
        elif len(name) > 32:
            return await ctx.send(
                f'{self.bot.ui_emojis.error} Display name is too long. Please keep it within 32 characters.'
            )
        self.bot.db['rooms'][room]['meta']['display_name'] = name
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send(f'{self.bot.ui_emojis.success} Updated display name to `{name}`!')

    @commands.command(hidden=True,description='Sets room description.')
    @restrictions.not_banned()
    async def roomdesc(self,ctx,room,*,desc=''):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if len(desc)==0:
            if not self.bot.db['rooms'][room]['meta']['description']:
                return await ctx.send(f'{self.bot.ui_emojis.error} There is no description to reset for this room.')
            self.bot.db['rooms'][room]['meta']['description'] = None
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            return await ctx.send(f'{self.bot.ui_emojis.success} Description removed.')
        self.bot.db['rooms'][room]['meta']['description'] = desc
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send(f'{self.bot.ui_emojis.success} Updated description!')

    @commands.command(hidden=True, description='Sets room emoji.')
    @restrictions.not_banned()
    async def roomemoji(self, ctx, room, *, emoji=''):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if len(emoji) == 0:
            if not self.bot.db['rooms'][room]['meta']['emoji']:
                return await ctx.send(f'{self.bot.ui_emojis.error} There is no emoji to reset for this room.')
            self.bot.db['rooms'][room]['meta']['emoji'] = None
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            return await ctx.send(f'{self.bot.ui_emojis.success} Emoji removed.')
        if not pymoji.is_emoji(emoji):
            return await ctx.send(f'{self.bot.ui_emojis.error} This is not a valid emoji.')
        self.bot.db['rooms'][room]['meta']['emoji'] = emoji
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send('Updated emoji!')

    @commands.command(
        hidden=True,
        description='Restricts/unrestricts a room. Only admins will be able to collect to this room when restricted.'
    )
    @restrictions.admin()
    async def restrict(self,ctx,room):
        room = room.lower()
        if not room in list(self.bot.db['rooms'].keys()):
            return await ctx.send(f'{self.bot.ui_emojis.error} This room does not exist!')
        if self.bot.db['rooms'][room]['meta']['private']:
            return await ctx.send(f'{self.bot.ui_emojis.error} Private rooms cannot be restricted.')
        if self.bot.db['rooms'][room]['meta']['restricted']:
            self.bot.db['rooms'][room]['meta']['restricted'] = False
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            await ctx.send(f'{self.bot.ui_emojis.success} Unrestricted `{room}`!')
        else:
            self.bot.db['rooms'][room]['meta']['restricted'] = True
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            await ctx.send(f'{self.bot.ui_emojis.success} Restricted `{room}`!')

    @commands.command(
        hidden=True,
        description='Locks/unlocks a room. Only moderators and admins will be able to chat in this room when locked.'
    )
    @restrictions.moderator()
    async def lock(self,ctx,room):
        room = room.lower()
        if not room in list(self.bot.db['rooms'].keys()):
            return await ctx.send(f'{self.bot.ui_emojis.error} This room does not exist!')
        if not self.bot.db['rooms'][room]['meta']['private'] and not ctx.author.id in self.bot.admins:
            return await ctx.send(f'{self.bot.ui_emojis.error} You cannot manage public rooms.')
        if self.bot.db['rooms'][room]['meta']['locked']:
            self.bot.db['rooms'][room]['meta']['locked'] = False
            await ctx.send(f'{self.bot.ui_emojis.success} Unlocked `{room}`!')
        else:
            self.bot.db['rooms'][room]['meta']['locked'] = True
            await ctx.send(f'{self.bot.ui_emojis.success} Locked `{room}`!')
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())

    @commands.command(description='Disbands a room.')
    async def disband(self, ctx, room):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.warning} Disband `{room}`?',
            description='Once the room is disbanded, it\'s gone forever!',
            color=self.bot.colors.warning
        )
        view = ui.MessageComponents()
        view.add_row(
            ui.ActionRow(
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.red,
                    label='Disband',
                    custom_id='disband'
                ),
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.gray,
                    label='Cancel',
                    custom_id='cancel'
                )
            )
        )
        msg = await ctx.send(embed=embed, view=view)
        view.clear_items()
        view.row_count = 0
        view.add_row(
            ui.ActionRow(
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.red,
                    label='Disband',
                    custom_id='disband',
                    disabled=True
                ),
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.gray,
                    label='Cancel',
                    custom_id='cancel',
                    disabled=True
                )
            )
        )

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        try:
            interaction = await self.bot.wait_for('interaction',check=check,timeout=60)
        except:
            return await msg.edit(view=view)

        if interaction.data['custom_id'] == 'cancel':
            return await interaction.response.edit_message(view=view)

        self.bot.db['rooms'].pop(room)
        embed.title = f'{self.bot.ui_emojis.success} Disbanded `{room}`'
        embed.description = 'The room was disbanded successfully.'
        embed.colour = self.bot.colors.success
        await interaction.response.edit_message(embed=embed,view=None)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())

    @commands.command(aliases=['link','connect','federate','bridge'],description='Connects the channel to a given room.')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @restrictions.not_banned()
    async def bind(self,ctx,*,room=''):
        invite = False
        roominfo = self.bot.bridge.get_room(room.lower())

        if not roominfo:
            invite = True
            try:
                roominfo = self.bot.bridge.get_room(
                    self.bot.bridge.get_invite(room.lower())['room']
                )
            except:
                raise restrictions.UnknownRoom()

        if not invite:
            room = room.lower()
            if not room in self.bot.bridge.rooms:
                raise restrictions.UnknownRoom()

            if not self.can_join(ctx.author, room):
                raise restrictions.NoRoomJoin()
            roomname = room
        else:
            roomname = self.bot.bridge.get_invite(room.lower())['room']

        text = []
        for i in range(len(roominfo['meta']['rules'])):
            text.append(f'{i+1}. '+roominfo['meta']['rules'][i])
        text = '\n'.join(text)

        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.loading} Checking if channel is already connected...',
            description='We\'re checking if this channel is already connected. Give us a moment...',
            color=self.bot.colors.warning
        )
        msg = await ctx.send(embed=embed)

        duplicate = self.bot.bridge.check_duplicate(ctx.channel)
        if duplicate:
            embed.colour = self.bot.colors.error
            embed.title = f'{self.bot.ui_emojis.error} Already connected'
            embed.description = (
                f'This channel is already connected to `{duplicate}`!\nRun `{self.bot.command_prefix}unbind '+
                f'{duplicate}` to disconnect the channel.'
            )
            return await msg.edit(embed=embed)

        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.rooms} Join {roominfo["meta"]["display_name"] or roomname}?',
            description=(f'{text}\n\nBy joining this room, you and your members agree to these rules.\n'+
                         'This message will be pinned (if possible) for better accessibility to the rules.'
                         ),
            color=self.bot.colors.warning
        )
        embed.set_footer(text='Failure to follow room rules may lead to user or server restrictions.')

        components = ui.MessageComponents()
        components.add_row(
            ui.ActionRow(
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.green,
                    label='Accept & bind',
                    custom_id='accept',
                    emoji=f'{self.bot.ui_emojis.success}'
                ),
                nextcord.ui.Button(
                    style=nextcord.ButtonStyle.gray,
                    label='Cancel',
                    custom_id='cancel',
                    emoji=f'{self.bot.ui_emojis.error}'
                )
            )
        )

        await msg.edit(embed=embed,view=components)

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        try:
            interaction = await self.bot.wait_for('interaction',check=check,timeout=60)

            if interaction.data['custom_id'] == 'cancel':
                await interaction.response.edit_message(view=None)
                raise Exception()
        except:
            embed.title = f'{self.bot.ui_emojis.error} Server did not agree to room rules.'
            embed.colour = self.bot.colors.error
            return await msg.edit(embed=embed,view=None)

        await msg.edit(view=None)
        await interaction.response.defer(ephemeral=False, with_message=True)

        webhook = None

        try:
            roomname = room
            if invite:
                roomname = self.bot.bridge.get_invite(room.lower())['room']
                await self.bot.bridge.accept_invite(ctx.author, room.lower())

            webhook = await ctx.channel.create_webhook(name='Unifier Bridge')
            await self.bot.bridge.join_room(ctx.author,roomname,ctx.channel,webhook_id=webhook.id)
        except Exception as e:
            if webhook:
                try:
                    await webhook.delete()
                except:
                    pass

            embed.title = f'{self.bot.ui_emojis.error} Failed to connect.'

            if type(e) is self.bot.bridge.InviteNotFoundError:
                embed.title = f'{self.bot.ui_emojis.error} Invite is invalid.'
            elif type(e) is self.bot.bridge.RoomBannedError:
                embed.title = f'{self.bot.ui_emojis.error} You are banned from this room.'

            embed.colour = self.bot.colors.error
            await msg.edit(embed=embed)
            await interaction.delete_original_message()

            if not type(e) is self.bot.bridge.InviteNotFoundError:
                raise
        else:
            embed.title = f'{self.bot.ui_emojis.success} Connected to room!'
            embed.colour = self.bot.colors.success
            await msg.edit(embed=embed)
            try:
                await msg.pin()
            except:
                pass
            await interaction.edit_original_message(content=f'{self.bot.ui_emojis.success} You\'re now connected! Say hi!')

    @commands.command(aliases=['unlink','disconnect'],description='Disconnects the server from a given room.')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    async def unbind(self,ctx,room=None):
        if not room:
            room = self.bot.bridge.check_duplicate(ctx.channel)
            if not room:
                return await ctx.send(f'{self.bot.ui_emojis.error} This channel is not connected to a room.')
        data = self.bot.bridge.get_room(room.lower())
        if not data:
            raise restrictions.UnknownRoom()

        hook_deleted = True
        try:
            hooks = await ctx.guild.webhooks()
            if f'{ctx.guild.id}' in list(data.keys()):
                hook_ids = data[f'{ctx.guild.id}']
            else:
                hook_ids = []
            for webhook in hooks:
                if webhook.id in hook_ids:
                    await webhook.delete()
                    break
        except:
            hook_deleted = False

        await self.bot.bridge.leave_room(ctx.guild, room)

        if hook_deleted:
            await ctx.send(f'{self.bot.ui_emojis.success} Channel has been unbinded.')
        else:
            await ctx.send(f'{self.bot.ui_emojis.warning} Channel has been unbinded, but the webhook could not be deleted.')

    @commands.command(description='Kicks a server from the room.')
    @restrictions.not_banned()
    async def roomkick(self, ctx, room, guild):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_moderate(ctx.author, room):
            raise restrictions.NoRoomModeration()

        data = self.bot.bridge.get_room(room.lower())

        platform = None
        for check_platform in data.keys():
            if check_platform == 'meta':
                continue
            if f'{guild}' in data[check_platform].keys():
                platform = check_platform
                break

        if not platform:
            return await ctx.send(f'{self.bot.ui_emojis.error} This server isn\'t connected to this room.')

        server_name = None
        try:
            if platform == 'discord':
                guild_obj = self.bot.get_guild(int(guild))
                server_name = guild_obj.name
            else:
                support = self.bot.platforms[platform]
                guild_obj = support.get_server(guild)
                server_name = support.name(guild_obj)

            hooks = await guild_obj.webhooks()
            if guild in list(data.keys()):
                hook_ids = data[guild]
            else:
                hook_ids = []
            for webhook in hooks:
                if webhook.id in hook_ids:
                    await webhook.delete()
                    break
        except:
            pass
        data[platform].pop(guild)
        self.bot.bridge.update_room(room, data)

        if not server_name:
            server_name = '[unknown server]'

        await ctx.send(f'{self.bot.ui_emojis.success} Server {server_name} was kicked from the room.')

    @commands.command(description='Bans a server from the room.')
    @restrictions.not_banned()
    async def roomban(self, ctx, room, guild):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_moderate(ctx.author, room):
            raise restrictions.NoRoomModeration()

        data = self.bot.bridge.get_room(room.lower())

        platform = None
        for check_platform in data.keys():
            if check_platform == 'meta':
                continue
            if f'{guild}' in data[check_platform].keys():
                platform = check_platform
                break

        if not platform:
            return await ctx.send(f'{self.bot.ui_emojis.error} This server isn\'t connected to this room.')

        server_name = None
        try:
            if platform == 'discord':
                guild_obj = self.bot.get_guild(int(guild))
                server_name = guild_obj.name
            else:
                support = self.bot.platforms[platform]
                guild_obj = support.get_server(guild)
                server_name = support.name(guild_obj)

            hooks = await guild_obj.webhooks()
            if guild in list(data.keys()):
                hook_ids = data[guild]
            else:
                hook_ids = []
            for webhook in hooks:
                if webhook.id in hook_ids:
                    await webhook.delete()
                    break
        except:
            pass
        data[platform].pop(guild)

        if not guild in data['meta']['banned']:
            data['meta']['banned'].append(guild)

        self.bot.bridge.update_room(room, data)

        if not server_name:
            server_name = '[unknown server]'

        await ctx.send(f'{self.bot.ui_emojis.success} Server {server_name} was kicked from the room.')

    @commands.command(description='Maps channels to rooms in bulk.', aliases=['autobind'])
    @restrictions.admin()
    async def map(self, ctx):
        channels = []
        channels_enabled = []
        namelist = []

        # get using async because this property may take a while to get if there's lots of rooms
        public_rooms = await self.bot.loop.run_in_executor(None, lambda: self.bot.bridge.public_rooms)

        embed = nextcord.Embed(title=f'{self.bot.ui_emojis.loading} Checking bindable channels...',
                               description='This may take a while.',
                               color=self.bot.colors.warning)
        msg = await ctx.send(embed=embed)
        hooks = await ctx.guild.webhooks()
        for channel in ctx.guild.text_channels:
            duplicate = False
            for roomname in list(public_rooms):
                # Prevent duplicate binding
                try:
                    hook_id = self.bot.bridge.get_room(roomname)['discord'][f'{ctx.guild.id}'][0]
                except:
                    continue
                for hook in hooks:
                    if hook.id == hook_id and hook.channel_id==channel.id:
                        duplicate = True
                        break
            if duplicate:
                continue
            roomname = re.sub(r'[^a-zA-Z0-9_-]', '', channel.name).lower()
            if len(roomname) < 3:
                roomname = str(channel.id)
            if roomname in namelist:
                continue
            namelist.append(roomname)
            try:
                if len(self.bot.db['rooms'][roomname]['discord'][f'{ctx.guild.id}']) >= 1:
                    continue
            except:
                pass
            perms = channel.permissions_for(ctx.guild.me)
            if perms.manage_webhooks and perms.send_messages and perms.read_messages and perms.read_message_history:
                channels.append(channel)
                if len(channels_enabled) < 10:
                    channels_enabled.append(channel)
            if len(channels) >= 25:
                break

        interaction = None
        restricted = False
        locked = False
        while True:
            text = ''
            for channel in channels_enabled:
                roomname = re.sub(r'[^a-zA-Z0-9_-]', '', channel.name).lower()
                if len(roomname) < 3:
                    roomname = str(channel.id)
                if text=='':
                    text = f'#{channel.name} ==> **{roomname}**' + (
                        ' (__New__)' if not roomname in self.bot.db['rooms'].keys() else '')
                else:
                    text = f'{text}\n#{channel.name} ==> **{roomname}**' + (
                        ' (__New__)' if not roomname in self.bot.db['rooms'].keys() else '')
            embed = nextcord.Embed(
                title=f'{self.bot.ui_emojis.rooms} Map channels',
                description=f'The following channels will be mapped.\nIf the channel does not exist, they will be created automatically.\n\n{text}',
                color=self.bot.colors.unifier
            )

            view = ui.MessageComponents()
            selection = nextcord.ui.StringSelect(
                max_values=10 if len(channels) > 10 else len(channels),
                placeholder='Channels...',
                custom_id='selection'
            )

            for channel in channels:
                selection.add_option(
                    label=f'#{channel.name}',
                    value=str(channel.id),
                    default=channel in channels_enabled
                )

            view.add_rows(
                ui.ActionRow(
                    selection
                ),
                ui.ActionRow(
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.gray,
                        label='Select first 10' if len(channels) > 10 else 'Select all',
                        custom_id='selectall'
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.gray,
                        label='Deselect all',
                        custom_id='deselect'
                    )
                ),
                ui.ActionRow(
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.green,
                        label='Bind',
                        custom_id='bind'
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.blurple,
                        label='Bind (create as restricted)',
                        custom_id='bind_restricted'
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.blurple,
                        label='Bind (create as locked)',
                        custom_id='bind_locked'
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.red,
                        label='Cancel',
                        custom_id='cancel'
                    )
                ) if ctx.author.id in self.bot.admins else ui.ActionRow(
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.green,
                        label='Bind',
                        custom_id='bind'
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.red,
                        label='Cancel',
                        custom_id='cancel'
                    )
                )
            )

            if interaction:
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await msg.edit(embed=embed, view=view)

            def check(interaction):
                return interaction.user.id==ctx.author.id and interaction.message.id==msg.id

            try:
                interaction = await self.bot.wait_for('interaction', check=check, timeout=60)
                if interaction.data['custom_id']=='cancel':
                    raise RuntimeError()
            except:
                return await msg.edit(view=ui.MessageComponents())

            if interaction.data['custom_id'].startswith('bind'):
                await msg.edit(embed=embed, view=ui.MessageComponents())
                await interaction.response.defer(with_message=True)
                if 'restricted' in interaction.data['custom_id']:
                    restricted = True
                elif 'locked' in interaction.data['custom_id']:
                    locked = True
                break
            elif interaction.data['custom_id']=='selection':
                channels_enabled = []
                for value in interaction.data['values']:
                    channel = self.bot.get_channel(int(value))
                    channels_enabled.append(channel)
            elif interaction.data['custom_id']=='selectall':
                channels_enabled = []
                for channel in channels:
                    channels_enabled.append(channel)
                    if len(channels_enabled) >= 10:
                        break
            elif interaction.data['custom_id'] == 'deselect':
                channels_enabled = []

        for channel in channels_enabled:
            roomname = re.sub(r'[^a-zA-Z0-9_-]', '', channel.name).lower()
            if len(roomname) < 3:
                roomname = str(channel.id)
            if not roomname in self.bot.db['rooms'].keys():
                self.bot.bridge.create_room(roomname)
                if restricted:
                    self.bot.db['rooms'][roomname]['meta']['restricted'] = True
                elif locked:
                    self.bot.db['rooms'][roomname]['meta']['locked'] = True
            webhook = await channel.create_webhook(name='Unifier Bridge')
            await self.bot.bridge.join_room(ctx.author,roomname,ctx.channel.id,webhook_id=webhook.id)

        await interaction.edit_original_message(
            content=f'{self.bot.ui_emojis.success} Channels are now connected! Say hi!')

    @commands.command(description='Displays room rules for the specified room.')
    async def rules(self,ctx,*,room=''):
        room = room.lower()
        if self.is_room_restricted(room,self.bot.db) and not self.is_user_admin(ctx.author.id):
            return await ctx.send(':eyes:')
        if room=='' or not room:
            room = 'main'

        if not room in list(self.bot.db['rooms'].keys()):
            return await ctx.send(f'{self.bot.ui_emojis.error} This isn\'t a valid room. Run `{self.bot.command_prefix}rooms` for a full list of rooms.')

        index = 0
        text = ''
        if room in list(self.bot.db['rooms'].keys()):
            rules = self.bot.db['rooms'][room]['meta']['rules']
            if len(rules)==0:
                return await ctx.send(f'{self.bot.ui_emojis.error} The admins haven\'t added rules yet. Though, make sure to always use common sense.')
        else:
            return await ctx.send(f'{self.bot.ui_emojis.error} The admins haven\'t added rules yet. Though, make sure to always use common sense.')
        for rule in rules:
            if text=='':
                text = f'1. {rule}'
            else:
                text = f'{text}\n{index}. {rule}'
            index += 1
        embed = nextcord.Embed(title=f'{self.bot.ui_emojis.rooms} Room rules',description=text,color=self.bot.colors.unifier)
        embed.set_footer(text='Failure to follow room rules may result in user or server restrictions.')
        await ctx.send(embed=embed)

    @commands.command(hidden=True,description="Adds a rule to a given room.")
    @restrictions.not_banned()
    async def addrule(self,ctx,room,*,rule):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        if len(self.bot.db['rooms'][room]['meta']['rules']) >= 25:
            return await ctx.send(f'{self.bot.ui_emojis.error} You can only have up to 25 rules in a room!')
        self.bot.db['rooms'][room]['meta']['rules'].append(rule)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send(f'{self.bot.ui_emojis.success} Added rule!')

    @commands.command(hidden=True,description="Removes a given rule from a given room.")
    @restrictions.not_banned()
    async def delrule(self,ctx,room,*,rule):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_manage(ctx.author, room):
            raise restrictions.NoRoomManagement()

        try:
            rule = int(rule)
            if rule <= 0:
                raise ValueError()
        except:
            return await ctx.send(f'{self.bot.ui_emojis.error} Rule must be a number higher than 0.')
        self.bot.db['rooms'][room]['meta']['rules'].pop(rule-1)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        await ctx.send(f'{self.bot.ui_emojis.success} Removed rule!')

    @commands.command(name='reply-layout', description="Sets the reply layout.")
    @commands.has_guild_permissions(manage_channels=True)
    async def reply_layout(self, ctx):
        layout = self.bot.bridge.get_reply_style(ctx.guild.id)
        embed = nextcord.Embed(
            title='Reply layout',
            description='Current layout: '+(
                'Stylish\n\nA colored button will appear at the bottom of the message.' if layout==0
                else 'Familiar\n\nSome text will be added on top of the message.'
            )
        )
        components = ui.MessageComponents()
        components.add_row(
            ui.ActionRow(
                nextcord.ui.StringSelect(
                    options=[
                        nextcord.SelectOption(
                            label='Stylish',
                            value='0',
                            default=layout == 0,
                            description='A colored button will appear at the bottom of the message.'
                        ),
                        nextcord.SelectOption(
                            label='Familiar',
                            value='1',
                            default=layout == 1,
                            description='Some text will be added on top of the message.'
                        )
                    ]
                )
            )
        )

        msg = await ctx.send(embed=embed,view=components)

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        while True:
            try:
                interaction = await self.bot.wait_for('interaction',check=check,timeout=60)
            except:
                return await msg.edit(view=None)

            layout = int(interaction.data['values'][0])
            self.bot.bridge.set_reply_style(ctx.guild.id, layout)
            embed.description='Current layout: ' + (
                'Stylish\n\nA colored button will appear at the bottom of the message.' if layout == 0
                else 'Familiar\n\nSome text will be added on top of the message.'
            )
            components = ui.MessageComponents()
            components.add_row(
                ui.ActionRow(
                    nextcord.ui.StringSelect(
                        options=[
                            nextcord.SelectOption(
                                label='Stylish',
                                value='0',
                                default=layout == 0,
                                description='A colored button will appear at the bottom of the message.'
                            ),
                            nextcord.SelectOption(
                                label='Familiar',
                                value='1',
                                default=layout == 1,
                                description='Some text will be added on top of the message.'
                            )
                        ]
                    )
                )
            )
            await interaction.response.edit_message(embed=embed,view=components)

    @commands.command(hidden=True,description="Allows given user's webhooks to be bridged.")
    @restrictions.admin()
    async def addbridge(self,ctx,*,userid):
        try:
            userid = int(userid.replace('<@','',1).replace('!','',1).replace('>','',1))
            user = self.bot.get_user(userid)
            if not user or userid==self.bot.user.id:
                raise ValueError()
            if userid in self.bot.db['external_bridge']:
                return await ctx.send(f'{self.bot.ui_emojis.error} This user is already in the whitelist!')
        except:
            return await ctx.send(f'{self.bot.ui_emojis.error} Invalid user!')
        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.warning} Allow @{user.name} to bridge?',
            description='This will allow messages sent via webhooks created by this user to be bridged through Unifier.',
            color=self.bot.colors.warning
        )
        components = ui.MessageComponents()
        components.add_rows(
            ui.ActionRow(
                nextcord.ui.Button(label='Allow bridge',style=nextcord.ButtonStyle.green,custom_id='allow'),
                nextcord.ui.Button(label='Cancel',style=nextcord.ButtonStyle.gray)
            )
        )
        msg = await ctx.send(embed=embed,view=components)

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=30.0)
        except:
            return await msg.edit(view=None)
        await interaction.response.edit_message(view=None)
        if not interaction.data['custom_id']=='allow':
            return
        self.bot.db['external_bridge'].append(userid)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        return await ctx.send(f'# {self.bot.ui_emojis.success} Linked bridge to Unifier network!\nThis user\'s webhooks can now bridge messages through Unifier!')

    @commands.command(hidden=True,description='Prevents given user\'s webhooks from being bridged.')
    @restrictions.admin()
    async def delbridge(self, ctx, *, userid):
        try:
            userid = int(userid.replace('<@', '', 1).replace('!', '', 1).replace('>', '', 1))
            user = self.bot.get_user(userid)
            if not user:
                raise ValueError()
            if not userid in self.bot.db['external_bridge']:
                return await ctx.send(f'{self.bot.ui_emojis.error} This user isn\'t in the whitelist!')
        except:
            return await ctx.send(f'{self.bot.ui_emojis.error} Invalid user!')
        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.warning} Remove @{user.name} from bridge?',
            description='This will stop this user\'s webhooks from bridging messages.',
            color=self.bot.colors.warning
        )
        components = ui.MessageComponents()
        components.add_row(
            ui.ActionRow(
                nextcord.ui.Button(label='Revoke bridge', style=nextcord.ButtonStyle.red, custom_id='allow'),
                nextcord.ui.Button(label='Cancel', style=nextcord.ButtonStyle.gray)
            )
        )
        msg = await ctx.send(embed=embed, view=components)

        def check(interaction):
            return interaction.message.id == msg.id and interaction.user.id == ctx.author.id

        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=30.0)
        except:
            return await msg.edit(view=None)
        await interaction.response.edit_message(view=None)
        if not interaction.data['custom_id'] == 'allow':
            return
        self.bot.db['external_bridge'].remove(userid)
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
        return await ctx.send(
            f'# {self.bot.ui_emojis.success} Unlinked bridge from Unifier network!\nThis user\'s webhooks can no longer bridge messages through Unifier.')

    @commands.command(aliases=['public-rooms'], description='Shows a list of public rooms.')
    @commands.guild_only()
    async def rooms(self,ctx):
        await self.roomslist(ctx, False)

    @commands.command(name='private-rooms', description='Shows a list of public rooms.')
    @commands.guild_only()
    async def private_rooms(self, ctx):
        await self.roomslist(ctx, True)

    @commands.command(aliases=['guilds'], description='Lists all servers connected to a given room.')
    @commands.guild_only()
    async def servers(self, ctx, *, room='main'):
        room = room.lower()
        if not room in self.bot.bridge.rooms:
            raise restrictions.UnknownRoom()

        if not self.can_join(ctx.author, room):
            raise restrictions.NoRoomJoin()

        try:
            data = self.bot.db['rooms'][room]
        except:
            return await ctx.send(
                f'{self.bot.ui_emojis.error} This isn\'t a valid room. Run `{self.bot.command_prefix}rooms` for a full list of rooms.')
        text = ''
        for platform in data.keys():
            if platform == 'meta':
                continue
            for guild_id in data[platform]:
                try:
                    if platform == 'discord':
                        name = self.bot.get_guild(int(guild_id)).name
                    else:
                        support = self.bot.platforms[platform]
                        name = support.name(support.server(guild_id))
                except:
                    continue
                if len(text) == 0:
                    text = f'- {name} (`{guild_id}`, {platform})'
                else:
                    text = f'{text}\n- {name} (`{guild_id}`, {platform})'
        embed = nextcord.Embed(
            title=f'{self.bot.ui_emojis.rooms} Servers connected to `{room}`', description=text,
            color=self.bot.colors.unifier
        )
        await ctx.send(embed=embed)

    @commands.command(description='Enables or disables usage of server emojis as Global Emojis.')
    @commands.has_permissions(manage_guild=True)
    async def toggle_emoji(self,ctx):
        if ctx.guild.id in self.bot.bridged_emojis:
            self.bot.bridged_emojis.remove(ctx.guild.id)
            await ctx.send(f'{self.bot.ui_emojis.success} All members can now no longer use your emojis!')
        else:
            self.bot.bridged_emojis.append(ctx.guild.id)
            await ctx.send(f'{self.bot.ui_emojis.success} All members can now use your emojis!')
        self.bot.db['emojis'] = self.bot.bridged_emojis
        await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())

    @commands.command(description='Displays or sets custom avatar.')
    async def avatar(self,ctx,*,url=''):
        desc = f'You have no avatar! Run `{self.bot.command_prefix}avatar <url>` or set an avatar in your profile settings.'
        try:
            if f'{ctx.author.id}' in list(self.bot.db['avatars'].keys()):
                avurl = self.bot.db['avatars'][f'{ctx.author.id}']
                desc = f'You have a custom avatar! Run `{self.bot.command_prefix}avatar <url>` to change it, or run `{self.bot.command_prefix}avatar remove` to remove it.'
            else:
                desc = f'You have a default avatar! Run `{self.bot.command_prefix}avatar <url>` to set a custom one.'
                avurl = ctx.author.avatar.url
        except:
            avurl = None
        if not url=='':
            avurl = url
        embed = nextcord.Embed(
            title='This is your UniChat avatar!',
            description=desc,
            color=self.bot.colors.unifier
        )
        author = f'{ctx.author.name}#{ctx.author.discriminator}'
        if ctx.author.discriminator == '0':
            author = f'@{ctx.author.name}'
        try:
            embed.set_author(name=author,icon_url=avurl)
            embed.set_thumbnail(url=avurl)
        except:
            return await ctx.send(f"{self.bot.ui_emojis.error} Invalid URL!")
        if url=='remove':
            if not f'{ctx.author.id}' in list(self.bot.db['avatars'].keys()):
                return await ctx.send('You don\'t have a custom avatar!')
            self.bot.db['avatars'].pop(f'{ctx.author.id}')
            return await ctx.send('Custom avatar removed!')
        if not url=='':
            embed.title = 'This is how you\'ll look!'
            embed.description = 'If you\'re satisfied, press the green button!'
        btns = ui.ActionRow(
            nextcord.ui.Button(style=nextcord.ButtonStyle.green, label='Apply', custom_id=f'apply', disabled=False),
            nextcord.ui.Button(style=nextcord.ButtonStyle.gray, label='Cancel', custom_id=f'cancel', disabled=False)
        )
        components = ui.MessageComponents()
        components.add_row(btns)
        if url=='':
            embed.set_footer(text=f'To change your avatar, run {self.bot.command_prefix}avatar <url>.')
            components = None
        msg = await ctx.send(embed=embed,view=components)
        if not url == '':
            def check(interaction):
                return interaction.message.id==msg.id and interaction.user.id==ctx.author.id

            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=30.0)
            except:
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                await msg.edit(view=components)
                return await ctx.send('Timed out.',reference=msg)
            if interaction.data['custom_id']=='cancel':
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                return await interaction.response.edit_message(view=components)
            btns.items[0].disabled = True
            btns.items[1].disabled = True
            components = ui.MessageComponents()
            components.add_row(btns)
            await msg.edit(view=components)
            self.bot.db['avatars'].update({f'{ctx.author.id}':url})
            await self.bot.loop.run_in_executor(None, lambda: self.bot.db.save_data())
            return await interaction.response.send_message(f'{self.bot.ui_emojis.success} Avatar successfully added!')

    async def cog_command_error(self, ctx, error):
        await self.bot.exhandler.handle(ctx, error)

def setup(bot):
    bot.add_cog(Config(bot))
