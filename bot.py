#!/usr/bin/env python
import json
import logging
import sys

from discord.ext import commands


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
handler.setLevel(config['LOGGING']['LEVEL']['CONSOLE'])
logger.addHandler(handler)

# bot
logger.info('Creating bot object ...')
bot = commands.Bot(command_prefix=config['COMMAND_PREFIX'], description=config['BOT_DESCRIPTION'])
logger.info('Setup complete')


@bot.event
async def on_message(message):
    """
    TODO
    """
    await bot.process_commands(message)
    if message.content.startswith(config['COMMAND_PREFIX']):
        logger.debug('Command "{}" from "{}"'.format(message.content, message.author.name))
    if 'bot' in message.content.lower():
        logger.debug('Bot in message: "{}" by "{}"'.format(message.content, message.author.name))


@bot.command(name='test', help='test')
async def command_test():
    """
    TODO
    """
    await bot.say('test')


if __name__ == '__main__':
    try:
        logger.info('Starting run loop ...')
        bot.loop.run_until_complete(bot.start(config['BOT_TOKEN']))
    except KeyboardInterrupt:
        logger.warning('Logging out ...')
        bot.loop.run_until_complete(bot.logout())
        logger.warning('Logged out')
    finally:
        logger.warning('Closing ...')
        bot.loop.close()
        logger.info('Done')
