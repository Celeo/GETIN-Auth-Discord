#!/usr/bin/env python3
import json
import logging
import sys
import time

from pycord import Pycord

from util import Util
from scheduler import Scheduler


__version__ = '2.0.6'

with open('config.json') as f:
    config = json.load(f)


NEW_APPS_SLEEP_TIME = 900  # 15 minutes
SYNC_SLEEP_TIME = 3600  # 1 hour
KILLBOARD_SLEEP_TIME = 86400  # 1 day
ACTIVITY_TIME_DAYS = 30  # (roughly) 1 month
WORMBRO_CORP_ID = 98134538
WRONG_CHANNEL_MESSAGE = 'This command cannot be used from this channel'

logger = logging.getLogger('getin-auth-discord')
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

bot = Pycord(
    config['TOKEN'],
    user_agent='GETIN-Auth-Discord (github.com/Celeo/GETIN-Auth-Discord, {__version__})',
    logging_level=config['LOGGING']['LEVEL']['PYCORD']
)
util = Util(
    bot,
    config,
    logger,
    ACTIVITY_TIME_DAYS,
    WORMBRO_CORP_ID
)
scheduler = Scheduler(
    util,
    NEW_APPS_SLEEP_TIME,
    SYNC_SLEEP_TIME,
    KILLBOARD_SLEEP_TIME
)


@bot.command('source')
def command_source(data):
    bot.send_message(
        data['d']['channel_id'],
        'https://github.com/EVE-GETIN/GETIN-Auth-Discord by Celeo (EVE: Celeo Servasse) and WizBoom (EVE: Alex Kommorov)'
    )


@bot.command('schedule')
def command_schedule(data):
    message = f'''Schedule:
#
Check for new applications every {NEW_APPS_SLEEP_TIME // 60} minutes
Sync membership every {SYNC_SLEEP_TIME // 60} minutes
Check for killboard activity every {KILLBOARD_SLEEP_TIME // 3600} hours
'''
    bot.send_message(data['d']['channel_id'], message)


@bot.command('sync')
def command_sync(data):
    c = data['d']['channel_id']
    if not c == config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']:
        bot.send_message(c, WRONG_CHANNEL_MESSAGE)
        return
    try:
        bot.send_message(c, util.sync())
    except Exception as e:
        logger.error('Exception in !sync: ' + str(e))
        bot.send_message(c, 'An error occurred in the processing of that command')


@bot.command('apps')
def command_apps(data):
    c = data['d']['channel_id']
    if not c == config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT']:
        bot.send_message(c, WRONG_CHANNEL_MESSAGE)
        return
    try:
        bot.send_message(c, util.check_apps())
    except Exception as e:
        logger.error('Exception in !check_apps: ' + str(e))
        bot.send_message(c, 'An error occurred in the processing of that command')


@bot.command('subscribe')
def command_subscribe(data):
    try:
        message_channel = data['d']['channel_id']
        if message_channel in config['SUBSCRIBE_WHITELISTED_CHANNELS']:
            bot.send_message(message_channel, util.subscribe(data))
        else:
            bot.send_message(message_channel, WRONG_CHANNEL_MESSAGE)
    except Exception as e:
        logger.error('Exception in !subscribe: ' + str(e))
        bot.send_message(message_channel, 'An error occurred in the processing of that command')


@bot.command('unsubscribe')
def command_unsubscribe(data):
    try:
        message_channel = data['d']['channel_id']
        if message_channel in config['SUBSCRIBE_WHITELISTED_CHANNELS']:
            bot.send_message(message_channel, util.unsubscribe(data))
        else:
            bot.send_message(message_channel, WRONG_CHANNEL_MESSAGE)
    except Exception as e:
        logger.error('Exception in !unsubscribe: ' + str(e))
        bot.send_message(message_channel, 'An error occurred in the processing of that command')


@bot.command('whitelist')
def command_whitelist(data):
    try:
        message_channel = data['d']['channel_id']
        if message_channel in config['PRIVATE_COMMAND_CHANNELS']['ACTIVITY_MODERATION']:
            bot.send_message(message_channel, util.whitelist(data))
        else:
            bot.send_message(message_channel, WRONG_CHANNEL_MESSAGE)
    except Exception as e:
        logger.error('Exception in !whitelist: ' + str(e))
        bot.send_message(message_channel, 'An error occurred in the processing of that command')

@bot.command('unwhitelist')
def command_unwhitelist(data):
    try:
        message_channel = data['d']['channel_id']
        if message_channel in config['PRIVATE_COMMAND_CHANNELS']['ACTIVITY_MODERATION']:
            bot.send_message(message_channel, util.unwhitelist(data))
        else:
            bot.send_message(message_channel, WRONG_CHANNEL_MESSAGE)
    except Exception as e:
        logger.error('Exception in !unwhitelist: ' + str(e))
        bot.send_message(message_channel, 'An error occurred in the processing of that command')

@bot.command('query')
def command_query(data):
    try:
        message_channel = data['d']['channel_id']
        if message_channel in config['PRIVATE_COMMAND_CHANNELS']['ACTIVITY_MODERATION']:
            bot.send_message(message_channel, util.query(data))
        else:
            bot.send_message(message_channel, WRONG_CHANNEL_MESSAGE)
    except Exception as e:
        logger.error('Exception in !query: ' + str(e))
        bot.send_message(message_channel, 'An error occurred in the processing of that command')


@bot.command('help')
def command_help(data):
    message = '''```GETIN-Auth Discord bot

  !apps            Check apps
  !sync            Member sync
  !source          Get bot source
  !schedule        Show update schedule
  !subscribe       Subscribes to certain channels
  !unsubscribe     Unsubscribes from channels
  !help            Shows this message
  !whitelist       Whitelist a player for the killboard check
  !unwhitelist     Remove a player from the killboard check whitelist
  !query           Query the database. Possible queries: reddit, char
```'''
    bot.send_message(data['d']['channel_id'], message)


logger.info('Connecting to the socket')
bot.connect_to_websocket()
while not bot.connected:
    time.sleep(1)
logger.info('Connected')
time.sleep(3)
bot.set_status('do !help')
logger.info('Starting scheduled events')
scheduler.run()
logger.info('Started')
logger.info('Going into run loop')
bot.keep_running()
logger.warning('Run loop exited; bot no longer running')
