from threading import Thread
from time import sleep

import schedule


class Scheduler(Thread):

    def __init__(self, util, NEW_APPS_SLEEP_TIME, KILLBOARD_SLEEP_TIME):
        self.util = util
        self.util.logger.debug('Configuring scheduler')
        schedule.every(NEW_APPS_SLEEP_TIME).seconds.do(self.check_apps)
        schedule.every(KILLBOARD_SLEEP_TIME).seconds.do(self.killboard)

    def check_apps(self):
        self.util.logger.info('Scheduler: check_apps()')
        res = self.util.check_apps(from_scheduler=True)
        if res and res != 'Error!':
            self.util.bot.send_message(self.util.config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT'], res)

    def killboard(self):
        self.util.logger.info('Scheduler: killboard()')
        res = self.util.check_killboard(from_scheduler=True)
        if res and res != 'Error!':
            self.util.bot.send_message(self.util.config['PRIVATE_COMMAND_CHANNELS']['ACTIVITY'], res)

    def run(self):
        while True:
            schedule.run_pending()
            sleep(1)
