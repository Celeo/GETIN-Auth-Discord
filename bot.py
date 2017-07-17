#!/usr/bin/env python3
import json
import logging
import sys
import asyncio
import sqlite3
from datetime import datetime, timedelta

import re
import discord
from discord.ext import commands
import requests


# config setup
with open('config.json') as f:
    config = json.load(f)

# constants
NEW_APPS_SLEEP_TIME = 900  # 15 minutes
SYNC_SLEEP_TIME = 3600  # 1 hour
INVALID_KEYS_SLEEP_TIME = 7200  # 2 hours
KILLBOARD_SLEEP_TIME = 86400  # 1 day
ACTIVITY_TIME_DAYS = 30
ACTIVITY_WHITELIST = [
    'Celeo Servasse',
    'Alex Kommorov'
]
WORMBRO_ID = 98134538

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
logger.info('Setup complete')


@bot.event
async def on_ready():
    """Event fired when the bot is ready."""
    logger.info('Logged in')
    await bot.change_status(game=discord.Game(name='Auth'))


@bot.command(
    name='author',
    aliases=['source'],
    brief='Get bot source',
    help='Returns the author and source code repository URL of this bot'
)
async def command_source():
    """Command - source"""
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
    """Command - schedule

    Args:
        context (discord.ext.commands.context.Context): the command's context
    """
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['NAME']:
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
    """Command - sync

    Args:
        context (discord.ext.commands.context.Context): the command's context
    """
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['NAME']:
            await bot.say('This command cannot be used from this channel')
            logger.info('"{}" used command "sync" in "{}"'.format(context.message.author.name, context.messsage.channel.name))
            return
        await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']))
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
    """Command - apps

    Args:
        context (discord.ext.commands.context.Context): the command's context
    """
    try:
        if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['NAME']:
            await bot.say('This command cannot be used from this channel')
            logger.info('"{}" used command "sync" in "{}"'.format(context.message.author.name, context.messsage.channel.name))
            return
        await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']))
        await bot.say(check_apps())
    except Exception as e:
        logger.error('Exception in !apps: ' + str(e))


async def schedule_sync():
    """Run-forever method to sync membership on a schedule"""
    while not bot.is_closed:
        await bot.wait_until_ready()
        try:
            await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']))
            logger.info('Syncing membership ...')
            result = sync()
            if not result == 'No membership changes':
                await bot.send_message(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']), 'Scheduled sync:\n\n' + result)
        except Exception as e:
            logger.error('Exception in schedule_sync(): ' + str(e))
        finally:
            logger.info('Sleeping for {} seconds ...'.format(SYNC_SLEEP_TIME))
            await asyncio.sleep(SYNC_SLEEP_TIME)


async def schedule_new_apps():
    """Run-forever method to check applications on a schedule"""
    while not bot.is_closed:
        await bot.wait_until_ready()
        try:
            await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']))
            logger.info('Checking for new applications ...')
            result = check_apps()
            if not result == 'No new applications':
                await bot.send_message(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']), result)
        except Exception as e:
            logger.error('Exception in schedule_new_apps(): ' + str(e))
        finally:
            logger.info('Sleeping for {} seconds ...'.format(NEW_APPS_SLEEP_TIME))
            await asyncio.sleep(NEW_APPS_SLEEP_TIME)


async def schedule_invalid_keys():
    """Run-forever method to check invalid API keys on a schedule"""
    while not bot.is_closed:
        await bot.wait_until_ready()
        try:
            await bot.send_typing(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']['ID']))
            logger.info('Checking for invalid keys ...')
            # TODO
            logger.info('No invalid keys')
        except Exception as e:
            logger.error('Exception in schedule_invalid_keys(): ' + str(e))
        finally:
            logger.info('Sleeping for {} seconds ...'.format(INVALID_KEYS_SLEEP_TIME))
            await asyncio.sleep(INVALID_KEYS_SLEEP_TIME)


async def schedule_killboard():
    """Run-forever method to check killboard activity on a schedule"""
    while not bot.is_closed:
        await bot.wait_until_ready()
        try:
            logger.info('Checking killboards ...')
            result = check_killboard()
            if result:
                logger.info('Sending link to activity channel')
                await bot.send_message(discord.Object(id=config['PRIVATE_COMMAND_CHANNELS']['ACTIVITY']['ID']), result)
        except Exception as e:
            logger.error('Exception in schedule_killboard(): ' + str(e))
        finally:
            logger.info('Sleeping for {} seconds'.format(KILLBOARD_SLEEP_TIME))
            await asyncio.sleep(KILLBOARD_SLEEP_TIME)


def sync():
    """Makes an API request to the server to sync membership"""
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


def check_apps():
    """Makes an API request to the server to check applications

    Returns:
        str: message to post in chat
    """
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


def get_last_month():
    """Utility method to return the timestamp for killboard range

    Returns:
        int: timestamp
    """
    return (datetime.utcnow() - timedelta(days=ACTIVITY_TIME_DAYS)).strftime('%Y%m%d%H') + '00'


def get_database_mains():
    """Gets the main characters from the database

    Returns:
        list: main character names
    """
    connection = sqlite3.connect('../getin-auth/data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT DISTINCT main FROM member WHERE status = "Accepted"')
    data = cursor.fetchall()
    connection.close()
    return [e[0] for e in data]


def get_database_alts(main):
    """Gets the main character's alts from the database

    Args:
        main (str): main character name

    Returns:
        list: alt character names
    """
    connection = sqlite3.connect('../getin-auth/data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT character_id FROM member WHERE main=? AND status = "Accepted" AND character_id != "NULL"', (main, ))
    data = cursor.fetchall()
    connection.close()
    return [e[0] for e in data]


def get_character_id(main):
    """Gets a character id from the database

    Args:
        main (str): character name

    Returns:
        list: character id
    """
    connection = sqlite3.connect('../getin-auth/data.db')
    cursor = connection.cursor()
    cursor.execute("SELECT character_id FROM member WHERE character_name=? AND character_id != 'NULL'", (main, ))
    data = cursor.fetchall()
    connection.close()
    return [e[0] for e in data]


def convert_to_zkill_date(esiDate):
    """Converts EvE ESI date to EvE Zkillboard date

    Args:
        esiDate (str): date in ESI format

    Returns:
        string: zkillboard date format
    """
    zkillDate = re.sub(r'[^0-9]', '', esiDate[:-4])
    return zkillDate


def check_killboard():
    """Makes API calls to zKB to check killboard activity

    Returns:
        str: message to post in chat
    """
    logger.info('Starting killboard check ...')
    noKillsList = []
    mains = get_database_mains()
    if not mains:
        logger.warning('No mains in the database!')
        return None
    for index, name in enumerate(mains):
        if name in ACTIVITY_WHITELIST:
            continue

        # check if person has been in corp for a month
        charID = get_character_id(name)
        if len(charID) <= 0:
            logger.warning("No character ID found for " + name)
            continue
        corpHistoryURL = 'https://esi.tech.ccp.is/latest/characters/' + str(charID[0]) + '/corporationhistory/?datasource=tranquility'
        corpHistory = requests.get(corpHistoryURL)
        corpHistoryJSON = corpHistory.json()
        hasBeenInCorp = False
        for j in corpHistoryJSON:
            if j[0]['corporation_id'] == WORMBRO_ID:
                if convert_to_zkill_date(j['start_date']) < get_last_month():
                    hasBeenInCorp = True
                    break
        if not hasBeenInCorp:
            logger.info(name + ' hasn\'t been in corp for a month! Continuing ...')
            continue

        alts = get_database_alts(name)
        alts.sort(key=int)
        request_url = 'https://zkillboard.com/api/characterID/'
        found = False
        for i in range(len(alts)):
            if not alts[i]:
                logger.warning('No valid IDs found for character linked to {}'.format(name))
                continue
            if i > 0:
                request_url += ','
            request_url += str(alts[i])
            found = True
        if not found:
            logger.warning('No valid IDs for found character linked to {}'.format(name))
            continue
        request_url += '/startTime/{}/limit/1/'.format(get_last_month())
        logger.info('Making killboard request to {}'.format(request_url))
        r = requests.get(request_url, headers={
            'Accept-Encoding': 'gzip',
            'User-Agent': 'Maintainer: ' + config['PASTEBIN_USER_AGENT']
        })
        if r.status_code != 200:
            logger.error('Got status code {} from {}'.format(r.status_code, request_url))
            continue
        data = r.json()
        if not data:
            logger.info(f'{name} has no kills, adding to list')
            noKillsList.append(name)
    if not noKillsList:
        logger.info('All characters had recent kills')
        return None
    paste_contents = '\n'.join(noKillsList)
    logger.info('Data being posted to pastebin: ' + paste_contents.replace('\n', ', '))
    r = requests.post('http://pastebin.com/api/api_post.php', data={
        'api_dev_key': config['PASTEBIN_SECRET'],
        'api_paste_expire_date': '1D',
        'api_option': 'paste',
        'api_paste_private': '1',
        'api_paste_code': paste_contents
    })
    if not r.status_code == 200:
        raise Exception(f'POST to pastebin failed with status code {r.status_code}. Contents of paste: {paste_contents}')
    pastebin_link = r.text.replace('https://pastebin.com/', 'https://pastebin.com/raw/')
    logger.info('Pastebin link is ' + pastebin_link)
    return pastebin_link


if __name__ == '__main__':
    try:
        logger.info('Scheduling background tasks ...')
        bot.loop.create_task(schedule_sync())
        bot.loop.create_task(schedule_new_apps())
        bot.loop.create_task(schedule_killboard())
        # bot.loop.create_task(schedule_invalid_keys())
        logger.info('Starting run loop ...')
        bot.run(config['TOKEN'])
    except KeyboardInterrupt:
        logger.warning('Logging out ...')
        bot.loop.run_until_complete(bot.logout())
        logger.warning('Logged out')
    except Exception as e:
        logger.error('Caught unknown error: ' + str(e))
    finally:
        logger.warning('Closing ...')
        bot.loop.close()
        logger.info('Done')
