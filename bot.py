#!/usr/bin/env python
import json
import logging
import sys
import asyncio

import discord
from discord.ext import commands
import requests


# config setup
with open('config.json') as f:
    config = json.load(f)

# logging setup
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

# bot setup
logger.info('Creating bot object ...')
bot = commands.Bot(command_prefix=config['COMMAND_PREFIX'], description=config['DESCRIPTION'])
logger.info('Getting private channel reference ...')
logger.info('Setup complete')


@bot.event
async def on_ready():
    logger.info('Logged in')
    await bot.change_status(game=discord.Game(name='Auth'))


@bot.event
async def on_message(message):
    """
    Logs attempes to use the bot.

    Args:
        message (discord.Message) - message sent in the channel

    Returns:
        None
    """
    try:
        if message.author == bot.user:
            return
        if message.content.startswith(config['COMMAND_PREFIX']):
            logger.info('Command "{}" from "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
        if 'bot' in message.content.lower():
            logger.info('Bot in message: "{}" by "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
        await bot.process_commands(message)
    except Exception as e:
        logger.error('Exception in on_message(): ' + str(e))


@bot.command(
    name='author',
    aliases=['source'],
    brief='Get bot source',
    help='Returns the author and source code repository URL of this bot'
)
async def command_source():
    try:
        await bot.say('Celeodor (EVE: Celeo Servasse), https://git.celeodor.com/Celeo/GETIN-HR-Discord')
    except Exception as e:
        logger.error('Exception in !author: ' + str(e))


@bot.command(
    name='schedule',
    brief='Show update schedule',
    help='Shows the schedule by which the bot accesses the web app to update member data',
    pass_context=True
)
async def command_schedule(context):
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
            await bot.say('This command cannot be used from this channel')
            logger.info('"{}" used command "schedule" in "{}"'.format(context.message.author.name, context.messsage.channel.name))
            return
        await bot.say('Syncing membership: every 1 hour\nChecking new apps: every 15 minutes\nChecking invalid keys: every 2 hours')
    except Exception as e:
        logger.error('Exception in !schedule: ' + str(e))


@bot.command(
    name='sync',
    brief='Member sync',
    help='Calls the web app to sync membership information',
    pass_context=True
)
async def command_sync(context):
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
            await bot.say('This command cannot be used from this channel')
            logger.info('"{}" used command "sync" in "{}"'.format(context.message.author.name, context.messsage.channel.name))
            return
        await bot.send_typing(bot.get_channel(str(config['PRIVATE_COMMAND_CHANNEL']['ID'])))
        await bot.say(sync())
    except Exception as e:
        logger.error('Exception in !sync: ' + str(e))


@bot.command(
    name='apps',
    brief='Check apps',
    help='Calls the web app to check for new applications',
    pass_context=True
)
async def command_apps(context):
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']['NAME']:
            await bot.say('This command cannot be used from this channel')
            logger.info('"{}" used command "sync" in "{}"'.format(context.message.author.name, context.messsage.channel.name))
            return
        await bot.send_typing(bot.get_channel(str(config['PRIVATE_COMMAND_CHANNEL']['ID'])))
        await bot.say(check_apps())
    except Exception as e:
        logger.error('Exception in !apps: ' + str(e))


def sync():
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
            ', '.join(js['existing_members'] or ('None', )),
            ', '.join(js['new_members'] or ('None', )),
            ', '.join(js['left_members'] or ('None', ))
        )
        return message
    except Exception as e:
        logger.error('Exception syncing membership: ' + str(e))
        return 'Error!'


async def schedule_sync():
    while True:
        try:
            logger.info('Sleeping for 1 hour ...')
            await asyncio.sleep(3600)
            await bot.send_typing(bot.get_channel(str(config['PRIVATE_COMMAND_CHANNEL']['ID'])))
            logger.info('Syncing membership ...')
            result = sync()
            if not result == 'No membership changes':
                await bot.send_message(bot.get_channel(str(config['PRIVATE_COMMAND_CHANNEL']['ID'])), 'Scheduled sync:\n\n' + result)
        except Exception as e:
            logger.error('Exception in schedule_sync(): ' + str(e))


def check_apps():
    try:
        r = requests.get(config['URL_ROOT'] + 'apps', headers={'REST-SECRET': config['API_SECRET']}, verify=False)
        if not r.status_code == 200:
            raise Exception('Status code was {}, not 200'.format(r.status_code))
        js = r.json()
        if js:
            return 'New applications: ' + ', '.join(js)
        else:
            return 'No new applications'
    except Exception as e:
        logger.error('Exception in schedule_new_apps: ' + str(e))
        return 'Error!'


async def schedule_new_apps():
    while True:
        try:
            logger.info('Sleeping for 15 minutes ...')
            await asyncio.sleep(900)
            logger.info('Checking for new applications ...')
            result = check_apps()
            if not result == 'No new applications':
                await bot.send_message(bot.get_channel(str(config['PRIVATE_COMMAND_CHANNEL']['ID'])), result)
        except Exception as e:
            logger.error('Exception in schedule_new_apps(): ' + str(e))


async def schedule_invalid_keys():
    while True:
        try:
            logger.info('Sleeping for 2 hours ...')
            await asyncio.sleep(7200)
            logger.info('Checking for invalid keys ...')
            # TODO
            logger.info('No invalid keys')
        except Exception as e:
            logger.error('Exception in schedule_invalid_keys(): ' + str(e))


if __name__ == '__main__':
    try:
        logger.info('Scheduling background tasks ...')
        bot.loop.create_task(schedule_sync())
        bot.loop.create_task(schedule_new_apps())
        # bot.loop.create_task(schedule_invalid_keys())
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
