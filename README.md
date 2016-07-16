# GETIN-HR Discord bot

This is a Discord bot that hooks into the GETIN-HR web application to run checks and validations on a schedule and give updates to recruiters from Discord.

## Installing

Note: due to the async nature of Discord.py, this project requires Python 3.5.

Download from my Git server, install the Python prerequisites, and copy and edit the configuration:

```bash
$ git clone https://git.celeodor.com/Celeo/GETIN-HR-Discord.git
$ cd GETIN-HR-Discord
$ virtualenv env
$ . env/bin/activate
$ pip install -r requirements.txt
$ cp hr/config.json.example hr/config.json
```

Edit `hr/config.json`, supplying your Discord bot token and private channel name and ID in addition to the URL of the web app.

```bash
$ python bot.py
```
