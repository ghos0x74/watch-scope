# Watch Scope
This is a tool for crawling bug bounty platforms and watch programs scopes, if there is any changes it will notify you (Discord/Telegram)

## Installation

clone the repository and install required packages by using this commands.
``` bash
git clone https://github.com/ghos0x74/watch-scope.git
cd watch-scope
pip install -r requirements.txt
 ```
 ## Usage
 ### Method 1 :
Edit config file and Change `Webhook`, `Telegram/Discord` variables with your own values.
- Note: If you want to use Telegram, change the value of `telegram` to `True` and `discord` to `False` and then change the value of `chat_id` with your own telegram chat-id
``` bash
python3 watch-scope.py
 ```
 ### Method 2 :
 
 send to discord
 ```bash
 python3 watch-scope.py --discord --webhook <your discord webhook>
 ```
 ```bash
 python3 watch-scope.py --telegram --webhook <your bot TOKEN> --chat_id <your chat-id>
 ```
 or if you just want to update database
 ```bash
 python3 watch-scope.py --update
 ```
