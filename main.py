from discord_webhook import DiscordWebhook, DiscordEmbed
import config
import requests, pymongo, time, argparse
import urllib.parse,sys

def existdb(args,myclient):
    logger(args.silent,"[+] Checking for Database existence.")
    dbnames = myclient.list_database_names()
    if config.db in dbnames:
        logger(args.silent,"[+] Database Found.")
        return True
    logger(args.silent,"[-] Database Not Found.")

class Program:
    def __init__(self,name:str,data:object):
        self.name = name
        self.url = "https://raw.githubusercontent.com/Osb0rn3/bugbounty-targets/main/programs/{}.json".format(name)
        self.data = data

def logger(silent,message):
    if silent != True:
        print(message)

def listScope(scopes):
    scp = ""
    for s in scopes:
        scp = scp + s + "\n"
    return scp

def updateDatabase(args,program,mydb):
    try:
        for key in program.keys():
            logger(args.silent,"[+] Updating {} Database.".format(key))
            mycol = mydb[key]
            logger(args.silent,"[+] Removing previous collection.")
            mycol.drop()
            mycol.insert_many(program[key])
            logger(args.silent,"[+] {} Database Updated.".format(key))
    except Exception as e:
        logger(args.silent,"[-] {}".format(e))
        exit(1)
def push(args,platform,data,scopes=None,Type=None):

    if scopes:
        scp = listScope(scopes)

    if Type == "out":
        title = "New out of Scope"
    elif Type == "in":
        title = "New Scope Found."
    else:
        title = "New Program Found!"

    if args.discord:

        webhook = DiscordWebhook(args.webhook,rate_limit_retry=True)

        if len(data["thumbnail"]) > 256:
            data["thumbnail"] = "https://profile-photos.hackerone-user-content.com/variants/uzeafiqfy90rlkk6zzqdrfeminnl/1449098d8043bd63faa337ade3089242211e8d4c2ef8f32c232731e8ff0c3adb"

        embed = DiscordEmbed(title=title, description='```{}```'.format(scp), color='000000')
        embed.set_thumbnail(url=data["thumbnail"])
        embed.add_embed_field(name='Platform', value=platform,inline=False)
        embed.add_embed_field(name='Name', value=data["name"],inline=False)
        embed.add_embed_field(name='Type', value=data["type"],inline=False)
        embed.add_embed_field(name='Url', value=data["url"],inline=False)
        #if data["target_platform"] == "hackerone":
        #    embed.add_embed_field(name='instruction', value="{}".format(data["instruction"]),inline=False)
        embed.set_timestamp()
        webhook.add_embed(embed)
        response = webhook.execute()
        time.sleep(20)
        if response.status_code != 200:
            logger(args.silent,"[-] Cannot send to discord")
            exit(1)
        logger(args.silent,"[+] Sent to discord.")

    if args.telegram:
        webhook = args.webhook
        chat_id = args.chat_id
        message = urllib.parse.quote_plus(f'{title}\n———————————————\n🎯Scopes: {scp}———————————————\n> Platform {platform}\n———————————————\n> Name: {data["name"]}\n———————————————\n> Type {data["type"]}\n———————————————\nURL: {data["url"]}')
        requests.get(f"https://api.telegram.org/bot{webhook}/sendmessage?chat_id={chat_id}&text={message}")
        time.sleep(10)
        if requests.status_codes != 200:
            logger(args.silent,"[-] Cannot send to Telegram check chat_id and Webhook")
            exit(1)

def updateProgram(args,mycol,platform,data):
    logger(args.silent,"[+] Adding {} [{}] : to Database.".format(data["name"],platform))
    try:
        mycol.insert_one(data)
        logger(args.silent,"[+] Program Added.")
        push(args,platform,data,data["in_scope"])
    except Exception as e:
        logger(args.silent,"[-] {}".format(e))
        exit(1)

def updateScope(args,mycol,platform,data,scopes,Type):
    try:
        if Type == "in":
            logger(args.silent,"[+] Adding {}'s new in_scopes [{}] : to Database.".format(data["name"],platform))
            for scope in scopes:
                update = mycol.update_one({"handle":data["handle"]},{"$push":{"in_scope":str(scope)}})
            push(args,platform,data,scopes,"in")

        elif Type == "out":
            logger(args.silent,"[+] Adding {}'s new out_of_scopes [{}] : to Database.".format(data["name"],platform))
            for scope in scopes:
                update = mycol.update_one({"handle":data["handle"]},{"$push":{"out_of_scope":str(scope)}})
            push(args,platform,data,scopes,"out")

    except Exception as e:
        logger(args.silent,"[-] {}".format(e))
        
def check_old_data(args,platform,Program,mydb):

    new_in_scopes = []
    new_out_of_scopes = []

    try:
        updated = False
        mycol = mydb[platform]
        for data in Program[platform]:
            program = mycol.find_one({"handle":data["handle"]})
            if program == None:
                logger(args.silent,"[-] Program Not found in Database.")
                updateProgram(args,mycol,platform,data)
            elif program != None:
                old_inscopes = mycol.find_one({"handle":data["handle"]})["in_scope"]
                for new_in_scope in data["in_scope"]:
                    if new_in_scope not in old_inscopes:
                        logger(args.silent,"[+] New in_Scope founds! on {} : {}".format(platform,new_in_scope))
                        new_in_scopes.append(new_in_scope)
                if new_in_scopes != []:
                    updateScope(args,mycol,platform,data,new_in_scopes,"in")
                    updated == True
                for new_out_of_scope in old_inscopes:
                    if new_out_of_scope not in data["in_scope"]:
                        logger(args.silent,"[+] New out_of_Scope founds! on {} : {}".format(platform,new_out_of_scope))
                        new_out_of_scopes.append(new_out_of_scope)
                if new_out_of_scopes != []:
                    updateScope(args,mycol,platform,data,new_out_of_scopes,"out")
                    updated == True
        if updated == False:
            logger(args.silent,"[+] No changes were found in {}. ".format(platform))

    except Exception as e:
        logger(args.silent,"[-] {}".format(e))
        exit(1)


def getPlatforms(args,platform):

    if platform.name == "hackerone":
        logger(args.silent,"[+] Checking {}".format(platform.name))
        try:
            logger(args.silent,"[+] Sending HTTP Request to {} to get recent JSON Object.".format(platform.url))
            res = requests.get(platform.url).json()
            logger(args.silent,"[+] got the JSON Object.")
        except Exception as e:
            logger(args.silent,"[-] {}".format(e))
            exit(1)
        logger(args.silent,"[+] Cleaning JSON Object.")
        programs = []
        for program in res:
            platform.data = {}
            in_scope = []
            out_of_scope = []
            platform.data["name"] = program["attributes"]["name"]
            platform.data["handle"] = program["id"]
            platform.data["url"] = 'https://hackerone.com/{}?type={}'.format(program["attributes"]["handle"],program["type"])
            platform.data["thumbnail"] = program["attributes"]["profile_picture"]
            if program["attributes"]["offers_bounties"] == True:
                platform.data["type"] = "Bug-bounty"
            else:
                platform.data["type"] = "VDP"
            for scope in program["relationships"]["structured_scopes"]["data"]:
                if scope["attributes"]["asset_identifier"].isnumeric() == True:
                    in_scope.append("https://itunes.apple.com/app/id{}".format(scope["attributes"]["asset_identifier"]))
                else:
                    in_scope.append(scope["attributes"]["asset_identifier"])
                if scope["attributes"]["instruction"] != "" and scope["attributes"]["instruction"] is not None :
                    platform.data["instruction"] = scope["attributes"]["instruction"]
            platform.data["in_scope"] = in_scope
            platform.data["out_of_scope"] = out_of_scope
            programs.append(platform.data)
        return {platform.name:programs}
    
            #check_old_data(args,platform.name,platform.data)
            #logger(args.silent,platform.data)

    elif platform.name == "bugcrowd":
        logger(args.silent,"[+] Checking {}".format(platform.name))
        try:

            logger(args.silent,"[+] Sending HTTP Request to {} to get recent JSON Object.".format(platform.url))
            res = requests.get(platform.url).json()
            logger(args.silent,"[+] got the JSON Object.")
            programs = []
            for program in res:
                platform.data = {}
                in_scope = []
                out_of_scope = []
                platform.data["name"] = program["name"]
                platform.data["handle"] = program["code"]
                platform.data["url"] = 'https://bugcrowd.com{}'.format(program["program_url"])
                platform.data["thumbnail"] = program["logo"]
                platform.data["type"] = program["license_key"]
                for scopes2 in program["target_groups"]:
                    if scopes2["in_scope"] == True:
                        for scope in scopes2["targets"]:
                            if scope["uri"] is None or scope["uri"] == "":
                                in_scope.append(scope["name"])
                            else:
                                in_scope.append(scope["uri"])
                    elif scopes2["in_scope"] == False:
                        for scope in scopes2["targets"]:
                            if scope["uri"] is None or scope["uri"] == "":
                                out_of_scope.append(scope["name"])
                            else:
                                out_of_scope.append(scope["uri"])

                platform.data["in_scope"] = in_scope
                platform.data["out_of_scope"] = out_of_scope
                programs.append(platform.data)
                #logger(args.silent,platform.data)
            return {platform.name:programs}
        except Exception as e:
            logger(args.silent,"[-] {}".format(e))
            exit(1)

    elif platform.name == "yeswehack":
        logger(args.silent,"[+] Checking {}".format(platform.name))
        try:
            logger(args.silent,"[+] Sending HTTP Request to {} to get recent JSON Object.".format(platform.url))
            res = requests.get(platform.url).json()
            logger(args.silent,"[+] got the JSON Object.")
        except Exception as e:
            logger(args.silent,"[-] {}".format(e))
            exit(1)
        logger(args.silent,"[+] Cleaning JSON Object.")
        programs = []
        for program in res:
            platform.data = {}
            in_scope = []
            platform.data["name"] = program["title"]
            platform.data["handle"] = program["slug"]
            platform.data["url"] = 'https://yeswehack.com/programs/{}'.format(program["slug"])
            platform.data["thumbnail"] = program["thumbnail"]["url"]
            platform.data["type"] = program["type"]
            for scope in program["scopes"]:
                in_scope.append(scope["scope"])
            platform.data["in_scope"] = in_scope
            platform.data["out_of_scope"] = []
            programs.append(platform.data)
            #logger(args.silent,platform.data)
        return {platform.name:programs}
    
    elif platform.name == "intigriti":
        logger(args.silent,"[+] Checking {}".format(platform.name))
        try:
            logger(args.silent,"[+] Sending HTTP Request to {} to get recent JSON Object.".format(platform.url))
            res = requests.get(platform.url).json()
            logger(args.silent,"[+] got the JSON Object.")
        except Exception as e:
            logger(args.silent,"[-] {}".format(e))
            exit(1)
        programs = []
        for program in res:
            platform.data = {}
            in_scope = []
            platform.data["name"] = program["companyName"]
            platform.data["handle"] = program["handle"]
            platform.data["url"] = 'https://app.intigriti.com/programs/{}{}/detail'.format(program["companyHandle"],program["handle"])
            platform.data["thumbnail"] = "https://bff-public.intigriti.com/file/" + program["logoId"]
            if program["maxBounty"]["value"] == 0:
                platform.data["type"] = "VDP"
            else:
                platform.data["type"] = "Bug-bounty"
            for scope in program["domains"]:
                if scope["endpoint"].isnumeric() == True:
                    in_scope.append("https://itunes.apple.com/app/id{}".format(scope["endpoint"]))
                else:
                    in_scope.append(scope["endpoint"])
            platform.data["in_scope"] = in_scope
            platform.data["out_of_scope"] = []
            programs.append(platform.data)
            #logger(args.silent,platform.data)
        return {platform.name:programs}

def main():
    
    parser = argparse.ArgumentParser(description='Watch scope')
    parser.add_argument("--silent",action="store_true",help="Turn on Logging.")
    parser.add_argument("--update",action="store_true",help="Update Database.")
    parser.add_argument("--telegram",action="store_true",help="set sending method to telegram")
    parser.add_argument("--discord",action="store_true",help="set sending method to discord")
    parser.add_argument("-w","--webhook",help="telegram(BOT-TOKEN) or discord webhook link")
    parser.add_argument("-id","--chat_id",help="telegram chat_id")
    args = parser.parse_args()

    if not len(sys.argv) > 1:
        args.silent = config.silent        
        args.update = config.update
        args.discord = config.discord
        args.telegram = config.telegram
        args.webhook = config.webhook
        args.chat_id = config.chat_id

    myclient = pymongo.MongoClient(config.mongo)
    is_exist = existdb(args,myclient)
    mydb = myclient[config.db]

    if args.update or is_exist != True:
        for p in ["hackerone","bugcrowd","yeswehack","intigriti"]:
            data = Program(p,{})
            program = getPlatforms(args,data)
            updateDatabase(args,program,mydb)
            check_old_data(args,p,program,mydb)

    elif args.telegram or args.discord:
        for p in ["hackerone","bugcrowd","yeswehack","intigriti"]:
            data = Program(p,{})
            program = getPlatforms(args,data)
            check_old_data(args,p,program,mydb)

if __name__ == "__main__":
    main()