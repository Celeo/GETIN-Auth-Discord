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
handler.setLevel(config['LOGGING']['LEVEL']['FILE'])
logger.addHandler(handler)

# bot
logger.info('Creating bot object ...')
bot = commands.Bot(command_prefix=config['COMMAND_PREFIX'], description=config['DESCRIPTION'])
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
    if message.content.startswith(config['COMMAND_PREFIX']):
        logger.debug('Command "{}" from "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
    if 'bot' in message.content.lower():
        logger.debug('Bot in message: "{}" by "{}" in "{}"'.format(message.content, message.author.name, message.channel.name))
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
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']:
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
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']:
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
    if not context.message.channel.name == config['PRIVATE_COMMAND_CHANNEL']:
        await bot.say('This command cannot be used from this channel')
        logger.info('"{}" used command "sync" in "{}"'.format(context.message.user.name, context.messsage.channel.name))
        return
    await bot.say('Command not implemented')


if __name__ == '__main__':
    try:
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
