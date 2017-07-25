# GETIN-HR Discord bot

This is a Discord bot that hooks into the GETIN-HR web application to run checks and validations on a schedule and give updates to recruiters from Discord.

## Installing

Note: This project requires Python 3.6+.

```bash
$ git clone https://github.com/Celeo/GETIN-Auth-Discord
$ cd GETIN-Auth-Discord
$ virtualenv env
$ . env/bin/activate
$ pip install -r requirements.txt
$ cp config.json.example config.json
```

Fill in the configuration.

```bash
$ python bot.py
```
