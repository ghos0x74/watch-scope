# Watch Scope
This is a tool for crawling bug bounty platforms and watch programs scopes, if there is any changes it will notify you (Discord/Telegram)

## Installation

- Note : this program works with mongodb so you need to install it.<br />

clone the repository and install required packages by using this commands.
``` bash
git clone https://github.com/ghos0x74/watch-scope.git
cd watch-scope
pip install -r requirements.txt
 ```
 ## Usage
  ### Method 1 (using Docker): 
  - Note : edit config and crontab file with your own values.
  ``` bash
docker-compose up -d
 ```
 ### Method 2 :
Edit config file and Change `Webhook`, `Telegram/Discord` variables with your own values.
- Note: If you want to use Telegram, change the value of `telegram` to `True` and `discord` to `False` and then change the value of `chat_id` with your own telegram chat-id
``` bash
python3 main.py
 ```
 ### Method 3 :
 
 send to Discord
 ```bash
 python3 main.py -p all -w <your discord webhook> --discord
 ```
 send to Telegram
 ```bash
 python3 main.py -p all -w <your bot TOKEN> -id <your chat-id> --telegram
 ```
 or if you just want to update database
 ```bash
 python3 main.py -p all --update
 ```
 if you want to specify the platforms you can use `-p` or `--platform` switches
```bash
python3 main.py -p hackerone,bugcrowd --update
```
