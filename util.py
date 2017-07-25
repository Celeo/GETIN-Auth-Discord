from datetime import datetime, timedelta
import sqlite3
import re
import json

import requests


class Util:

    def __init__(self, bot, config, logger, ACTIVITY_TIME_DAYS, WORMBRO_CORP_ID):
        self.bot = bot
        self.config = config
        self.logger = logger
        self.ACTIVITY_TIME_DAYS = ACTIVITY_TIME_DAYS
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
                return None
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
            return None
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

    def is_main_valid(self, character):
        """Checks if the character name is valid

        Args:
            character (str): character name

        Returns:
            boolean: is main valid?
        """
        connection = sqlite3.connect('../getin-auth/data.db')
        cursor = connection.cursor()
        cursor.execute("SELECT character_name FROM member WHERE lower(character_name) = ?", (character.lower(), ))
        data = cursor.fetchall()
        entries = True
        if not data:
            entries = False

        connection.close()
        return entries

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

        activity_whitelist = [e['NAME'] for e in self.config['ACTIVITY_WHITELIST']]
        for index, name in enumerate(mains):
            if name in activity_whitelist:
                for index in range(len(self.config['ACTIVITY_WHITELIST'])):
                    char = self.config['ACTIVITY_WHITELIST'][index]
                    if name == char["NAME"]:
                        if char['EXPIRY TIME'] < self.ACTIVITY_TIME_DAYS * -1:
                            # permanent
                            self.logger.info(name + ' is permanently on the whitelist! Continuing ...')
                        else:
                            """
                            Not permanent
                            Remove from whitelist
                            """
                            if char['EXPIRY TIME'] - 1 < self.ACTIVITY_TIME_DAYS * -1:
                                self.config['ACTIVITY_WHITELIST'].pop(index)
                                self.logger.info(name + ' has been removed from the whitelist! Continuing ...')
                            else:
                                self.config['ACTIVITY_WHITELIST'][index]['EXPIRY TIME'] -= 1
                                self.logger.info(name + ' has gotten 1 day reduced from his / her whitelist time, but remains on it! Continuing ...')
                        break

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
                if j['corporation_id'] == self.WORMBRO_CORP_ID:
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
                'User-Agent': 'Maintainer: ' + self.config['ZKILL_USER_AGENT']
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

        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

        noKillsList.sort()
        paste_contents = '\n'.join(noKillsList)
        self.bot.send_message(self.config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT'], '**' + datetime.utcnow().strftime('%Y-%m-%d %H:%M' + '**'))

        n = 1994
        # split the string
        paste_list = paste_contents.split('\n')
        split_entry = ''
        for entry in paste_list:
            if len(split_entry + entry) >= n:
                self.bot.send_message(self.config['PRIVATE_COMMAND_CHANNELS']['RECRUITMENT'], '```' + split_entry + '```')
                split_entry = ''
            else:
                split_entry += entry + '\n'

        return '```' + split_entry + '```'

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
            group_list = []
            for role_node in self.config['SUBSCRIBE_ROLES']:
                if role_node['NAME'] in server_role_names:
                    role_node_id = Util.get_role_id(server_roles, role_node['NAME'])
                    if (role_node_id in member_roles) != is_subscribing:
                        group_list.append(role_node['NAME'] + ' (' + role_node['TYPE'] + '): ' + role_node['DESCRIPTION'] + '\n')
            if group_list:
                group_list.sort()
                stringGroup = ''
                for group in group_list:
                    stringGroup += group
                return '```NAME (TYPE): DESCRIPTION\n\n' + stringGroup + '```'
            else:
                return f'```No other groups to {str_action_direction_now}```'
        # role management request
        role_join_name = ' '.join(args).lower()
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

    def whitelist(self, data):
        argument_amount = 3
        message = data['d']['content']

        if len(message.split(' ')[1:]) == 0:
            whitelist = []
            # return the whitelist
            for j in self.config['ACTIVITY_WHITELIST']:
                whitelistString = j['NAME'] + ' ('
                if j['EXPIRY TIME'] < (self.ACTIVITY_TIME_DAYS * -1):
                    whitelistString += 'PERMANENT): '
                elif j['EXPIRY TIME'] <= 0:
                    continue
                else:
                    whitelistString += str(j['EXPIRY TIME']) + ' days left): '
                whitelist.append(whitelistString + j['DESCRIPTION'])
            whitelist.sort()
            if whitelist:
                return '**Whitelist\n**```' + '\n'.join(whitelist) + '```'
            else:
                return '**Whitelist\n**```No one in the whitelist!' + '```'

        args = message.split(' ', 1)[1]
        arg_list = args.split('|')
        arg_list = [e.strip() for e in arg_list]
        # check if there are enough arguments
        if len(arg_list) < argument_amount:
            return 'Too few arguments!'
        elif len(arg_list) > argument_amount:
            return 'Too many arguments!'

        main = arg_list[0]
        if not self.is_main_valid(main):
            return main + ' is not a valid main!'

        whitelist_lower = [e['NAME'].lower() for e in self.config['ACTIVITY_WHITELIST']]
        if main.lower() in whitelist_lower:
            return main + ' is already in the whitelist!'

        description = arg_list[1]
        time = arg_list[2]
        try:
            int(time)
        except ValueError:
            return time + ' is not a number!'

        timeNumber = int(time)

        jsonObject = {
            'NAME': main,
            'DESCRIPTION': description,
            'EXPIRY TIME': timeNumber
        }

        return_string = '**Added entry**\n```Name: ' + main + '\nDescription: ' + description + '\nExpiry time (in days): '
        if timeNumber <= 0:
            jsonObject['EXPIRY TIME'] = (self.ACTIVITY_TIME_DAYS * -1) - 1
            return_string += 'PERMANENT' + '```'
        else:
            return_string += str(timeNumber) + '```'

        self.config['ACTIVITY_WHITELIST'].append(jsonObject)
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

        return return_string
