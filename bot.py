#!/usr/bin/env python
import json
import logging
import sys
import asyncio

import discord
from discord.ext import commands
import requests


# config
with open('config.json') as f:
    config = json.load(f)

# logging
logger = logging.getLogger('discord')
logger.setLevel(config['LOGGING']['LEVEL']['ALL'])
formatter = logging.Formatter(style='{', fmt='{asctime} [{levelname}] {message}', datefmt='%Y-%m-%d %H:%M:%S')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(config['LOGGING']['LEVEL']['CONSOLE'])
logger.addHandler(handler)
handler = logging.FileHandler(config['LOGGING']['FILE'])
handler.setFormatter(formatter)
handler.setLevel(config['LOGGING']['LEVEL']['FILE'])
logger.addHandler(handler)

# bot
logger.info('Creating bot object ...')
bot = commands.Bot(command_prefix=config['COMMAND_PREFIX'], description=config['DESCRIPTION'])
logger.info('Getting private channel reference ...')
logger.info('Setup complete')


@bot.event
async def on_message(message):
    """
    Logs attempes to use the bot.

    Args:
        message (discord.Message) - message sent in the channel

    Returns:
        None
    """
    if message.author == bot.user:
        return
    if message.content.startswith(config['COMMAND_PREFIX']):
        logger.info('Command "{}" from "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
    if 'bot' in message.content.lower():
        logger.info('Bot in message: "{}" by "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
    await bot.process_commands(message)


@bot.command(
    name='author',
    aliases=['source'],
    brief='Get bot source',
    help='Returns the author and source code repository URL of this bot'
)
async def command_source():
    """
    TODO
    """
    await bot.say('Celeodor (EVE: Celeo Servasse), https://git.celeodor.com/Celeo/GETIN-HR-Discord')


@bot.command(
    name='schedule',
    brief='Show update schedule',
    help='Shows the schedule by which the bot accesses the web app to update member data',
    pass_context=True
)
async def command_schedule(context):
    """
    TODO
    """
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
        await bot.say('This command cannot be used from this channel')
        logger.info('"{}" used command "schedule" in "{}"'.format(context.message.user.name, context.messsage.channel.name))
        return
    await bot.say('Command not implemented')


@bot.command(
    name='check',
    brief='Check a member\'s status',
    help='Checks the status of a member in the corporation or an applicant in the web app',
    pass_context=True
)
async def command_check(context, target: str=None):
    """
    TODO
    """
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
        await bot.say('This command cannot be used from this channel')
        logger.info('"{}" used command "check" in "{}"'.format(context.message.user.name, context.messsage.channel.name))
        return
    if not target:
        await bot.say('{} check [name]'.format(config['COMMAND_PREFIX']))
        return
    await bot.say('Command not implemented')


@bot.command(
    name='sync',
    brief='Member sync',
    help='Calls the web app to sync membership information',
    pass_context=True
)
async def command_sync(context):
    """
    TODO
    """
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
        await bot.say('This command cannot be used from this channel')
        logger.info('"{}" used command "sync" in "{}"'.format(context.message.user.name, context.messsage.channel.name))
        return
    await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNEL']['ID']))
    await bot.say(sync())


def sync():
    """
    TODO
    """
    try:
        r = requests.get(config['URL_ROOT'] + 'sync', headers={'REST-SECRET': config['API_SECRET']}, verify=False)
        if not r.status_code == 200:
            raise Exception('Status code was {}, not 200'.format(r.status_code))
        js = r.json()
        if not js['existing_members'] and not js['new_members'] and not js['left_members']:
            message = 'No membership changes'
            logger.info(message)
            return message
        message = 'Existing members added to roster: {}\nAccepted applicants: {}\nCharacters who left the corp: {}'.format(
            ', '.join(js['existing_members'] or 'None'),
            ', '.join(js['new_members'] or 'None'),
            ', '.join(js['left_members'] or 'None')
        )
        return message
    except Exception as e:
        print('Exception syncing membership: ' + str(e))
        return 'Error!'


async def schedule_sync():
    """
    TODO
    """
    while True:
        logger.info('Sleeping for 1 hour ...')
        await asyncio.sleep(3600)
        await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNEL']['ID']))
        logger.info('Syncing membership ...')
        await bot.send_message(discord.Object(id=config['PRIVATE_COMMAND_CHANNEL']['ID']), sync())


async def schedule_new_apps():
    """
    TODO
    """
    while True:
        logger.info('Sleeping for 1 hour ...')
        await asyncio.sleep(3600)
        logger.info('Checking for new applications ...')
        # TODO
        logger.info('No new applications')


async def schedule_invalid_keys():
    """
    TODO
    """
    while True:
        logger.info('Sleeping for 2 hours ...')
        await asyncio.sleep(7200)
        logger.info('Checking for invalid keys ...')
        # TODO
        logger.info('No invalid keys')


if __name__ == '__main__':
    try:
        logger.info('Scheduling background tasks ...')
        bot.loop.create_task(schedule_sync())
        bot.loop.create_task(schedule_new_apps())
        bot.loop.create_task(schedule_invalid_keys())
        logger.info('Starting run loop ...')
        bot.loop.run_until_complete(bot.start(config['TOKEN']))
    except KeyboardInterrupt:
        logger.warning('Logging out ...')
        bot.loop.run_until_complete(bot.logout())
        logger.warning('Logged out')
    finally:
        logger.warning('Closing ...')
        bot.loop.close()
        logger.info('Done')
