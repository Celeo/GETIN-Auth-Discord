from datetime import datetime, timedelta
import sqlite3
import re

import requests
from prettytable import PrettyTable


class Util:

    def __init__(self, bot, config, logger, ACTIVITY_TIME_DAYS, ACTIVITY_WHITELIST, WORMBRO_CORP_ID):
        self.bot = bot
        self.config = config
        self.logger = logger
        self.ACTIVITY_TIME_DAYS = ACTIVITY_TIME_DAYS
        self.ACTIVITY_WHITELIST = ACTIVITY_WHITELIST
        self.WORMBRO_CORP_ID = WORMBRO_CORP_ID

    def sync(self):
        """Makes an API request to the server to sync membership"""
        try:
            r = requests.get(self.config['URL_ROOT'] + 'sync', headers={'REST-SECRET': self.config['API_SECRET']}, verify=False)
            if not r.status_code == 200:
                raise Exception('Status code was {}, not 200'.format(r.status_code))
            js = r.json()
            if not js['existing_members'] and not js['new_members'] and not js['left_members']:
                message = 'No membership changes'
                self.logger.info(message)
                return message
            return 'Existing members added to roster: {}\nAccepted applicants: {}\nCharacters who left the corp: {}'.format(
                ', '.join(js['existing_members'] or ('None', )),
                ', '.join(js['new_members'] or ('None', )),
                ', '.join(js['left_members'] or ('None', ))
            )
        except Exception as e:
            self.logger.error('Exception syncing membership: ' + str(e))
            return 'Error!'

    def check_apps(self):
        """Makes an API request to the server to check applications

        Returns:
            str: message to post in chat
        """
        try:
            r = requests.get(self.config['URL_ROOT'] + 'apps', headers={'REST-SECRET': self.config['API_SECRET']}, verify=False)
            if not r.status_code == 200:
                raise Exception('Status code was {}, not 200'.format(r.status_code))
            js = r.json()
            if js:
                return 'New applications: ' + ', '.join(js)
            else:
                return 'No new applications'
        except Exception as e:
            self.logger.error('Exception in schedule_new_apps: ' + str(e))
            return 'Error!'

    def get_last_month(self):
        """Utility method to return the timestamp for killboard range

        Returns:
            int: timestamp
        """
        return (datetime.utcnow() - timedelta(days=self.ACTIVITY_TIME_DAYS)).strftime('%Y%m%d%H') + '00'

    def get_database_mains(self):
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

    def get_database_alts(self, main):
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

    def get_character_id(self, main):
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

    def convert_to_zkill_date(self, esiDate):
        """Converts EvE ESI date to EvE Zkillboard date

        Args:
            esiDate (str): date in ESI format

        Returns:
            string: zkillboard date format
        """
        zkillDate = re.sub(r'[^0-9]', '', esiDate[:-4])
        return zkillDate

    def check_killboard(self):
        """Makes API calls to zKB to check killboard activity

        Returns:
            str: message to post in chat
        """
        self.logger.info('Starting killboard check ...')
        noKillsList = []
        mains = self.get_database_mains()
        if not mains:
            self.logger.warning('No mains in the database!')
            return None
        for index, name in enumerate(mains):
            if name in self.ACTIVITY_WHITELIST:
                continue

            # check if person has been in corp for a month
            charID = self.get_character_id(name)
            if len(charID) <= 0:
                self.logger.warning("No character ID found for " + name)
                continue
            corpHistoryURL = 'https://esi.tech.ccp.is/latest/characters/' + str(charID[0]) + '/corporationhistory/?datasource=tranquility'
            corpHistory = requests.get(corpHistoryURL)
            corpHistoryJSON = corpHistory.json()
            hasBeenInCorp = False
            for j in corpHistoryJSON:
                if j[0]['corporation_id'] == self.WORMBRO_CORP_ID:
                    if self.convert_to_zkill_date(j['start_date']) < self.get_last_month():
                        hasBeenInCorp = True
                        break
            if not hasBeenInCorp:
                self.logger.info(name + ' hasn\'t been in corp for a month! Continuing ...')
                continue

            alts = self.get_database_alts(name)
            alts.sort(key=int)
            request_url = 'https://zkillboard.com/api/characterID/'
            found = False
            for i in range(len(alts)):
                if not alts[i]:
                    self.logger.warning('No valid IDs found for character linked to {}'.format(name))
                    continue
                if i > 0:
                    request_url += ','
                request_url += str(alts[i])
                found = True
            if not found:
                self.logger.warning('No valid IDs for found character linked to {}'.format(name))
                continue
            request_url += '/startTime/{}/limit/1/'.format(self.get_last_month())
            self.logger.info('Making killboard request to {}'.format(request_url))
            r = requests.get(request_url, headers={
                'Accept-Encoding': 'gzip',
                'User-Agent': 'Maintainer: ' + self.config['PASTEBIN_USER_AGENT']
            })
            if r.status_code != 200:
                self.logger.error('Got status code {} from {}'.format(r.status_code, request_url))
                continue
            data = r.json()
            if not data:
                self.logger.info('{} has no kills, adding to list'.format(name))
                noKillsList.append(name)
        if not noKillsList:
            self.logger.info('All characters had recent kills')
            return None
        paste_contents = '\n'.join(noKillsList)
        self.logger.info('Data being posted to pastebin: ' + paste_contents.replace('\n', ', '))
        r = requests.post('http://pastebin.com/api/api_post.php', data={
            'api_dev_key': self.config['PASTEBIN_SECRET'],
            'api_paste_expire_date': '1D',
            'api_option': 'paste',
            'api_paste_private': '1',
            'api_paste_code': paste_contents
        })
        if not r.status_code == 200:
            raise Exception('POST to pastebin failed with status code {}. Contents of paste: {}'.format(r.status_code, paste_contents))
        pastebin_link = r.text.replace('https://pastebin.com/', 'https://pastebin.com/raw/')
        self.logger.info('Pastebin link is ' + pastebin_link)
        return pastebin_link

    @classmethod
    def get_role_id(cls, roles, name):
        return [e['id'] for e in roles if e['name'] == name][0]

    def _handle_subscription(self, data, is_subscribing):
        str_action_direction_now = 'subscribed to' if is_subscribing else 'unsubscribed from'
        str_action_direction_past = 'subscribed to' if is_subscribing else 'unsubscribed from'
        message = data['d']['content']
        args = message.split(' ')[1:]
        # note: this locks the bot to being for single-server use only (per bot account)
        guild_id = self.bot.get_connected_guilds()[0]['id']
        server_roles = self.bot.get_all_guild_roles(guild_id)
        server_role_names = [r['name'] for r in server_roles]
        member_id = data['d']['author']['id']
        member_roles = self.bot.get_guild_member_by_id(guild_id, member_id)['roles']
        if not args:
            # return current groups request
            group_list = PrettyTable()
            group_list.field_names = ['Name', 'Description', 'Type']
            any_valid_roles = False
            for role_node in self.config['SUBSCRIBE_ROLES']:
                if role_node['NAME'] in server_role_names:
                    role_node_id = Util.get_role_id(server_roles, role_node['NAME'])
                    if (role_node_id in member_roles) != is_subscribing:
                        any_valid_roles = True
                        group_list.add_row([role_node['NAME'], role_node['DESCRIPTION'], role_node['TYPE']])
            if any_valid_roles:
                return '```' + group_list.get_string(sortby='Name') + '```'
            else:
                return f'```No other groups to {str_action_direction_now}```'
        # role management request
        role_join_name = args[0].lower()
        for role_node in self.config['SUBSCRIBE_ROLES']:
            if role_node['NAME'].lower() == role_join_name:
                if role_node['NAME'] in server_role_names:
                    role_node_id = Util.get_role_id(server_roles, role_node['NAME'])
                    if (role_node_id in member_roles) == is_subscribing:
                        return '<@{}>, you\'re already {} {}'.format(data['d']['author']['id'], str_action_direction_past, role_node['NAME'])
                    else:
                        if is_subscribing:
                            self.bot.add_member_roles(guild_id, member_id, [role_node_id])
                        else:
                            self.bot.remove_member_roles(guild_id, member_id, [role_node_id])
                        return '<@{}>, you\'re now {} {}'.format(data['d']['author']['id'], str_action_direction_past, role_node['NAME'])
        return '<@{}>, I can\'t find "{}"'.format(data['d']['author']['id'], role_join_name)

    def subscribe(self, data):
        return self._handle_subscription(data, True)

    def unsubscribe(self, data):
        return self._handle_subscription(data, False)