import requests, pymongo, time, argparse, urllib.parse, sys, config
from discord_webhook import DiscordWebhook, DiscordEmbed
from colorama import Fore

def existdb(args,myclient):
    logger(args.silent,"Checking for Database existence.",TYPE="pending")
    dbnames = myclient.list_database_names()
    if config.db in dbnames:
        logger(args.silent,"Database Found.",TYPE="success")
        return True
    logger(args.silent,"Database Not Found.",TYPE="error")

class Program:
    def __init__(self,name:str,data:object):
        self.name = name
        self.url = "https://raw.githubusercontent.com/Osb0rn3/bugbounty-targets/main/programs/{}.json".format(name)
        self.data = data

def logger(silent,message,TYPE):
    if silent != True:
        if TYPE == "error":
            print(Fore.LIGHTCYAN_EX+"["+Fore.LIGHTYELLOW_EX+"✗"+Fore.LIGHTCYAN_EX+"] "+Fore.RED+message+Fore.RESET)
        elif TYPE == "success":
            print(Fore.LIGHTCYAN_EX+"["+Fore.LIGHTYELLOW_EX+"✓"+Fore.LIGHTCYAN_EX+"] "+Fore.LIGHTCYAN_EX+message+Fore.RESET)
        elif TYPE == "pending":
            print(Fore.LIGHTCYAN_EX+"["+Fore.LIGHTYELLOW_EX+"*"+Fore.LIGHTCYAN_EX+"] "+Fore.LIGHTMAGENTA_EX+message+Fore.RESET)
        time.sleep(0.30)
def listScope(scopes):
    scp = ""
    for s in scopes:
        scp = scp + s + "\n"
    return scp

def updateDatabase(args,program,mydb):
    try:
        for key in program.keys():
            logger(args.silent,"Updating {} Database.".format(key),TYPE="pending")
            mycol = mydb[key]
            logger(args.silent,"Removing previous collection.",TYPE="pending")
            mycol.drop()
            mycol.insert_many(program[key])
            logger(args.silent,"{} Database Updated.".format(key),TYPE="success")
    except Exception as e:
        logger(args.silent,"{}".format(e),TYPE="error")
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
        # if data["target_platform"] == "hackerone":
        #    embed.add_embed_field(name='instruction', value="{}".format(data["instruction"]),inline=False)
        embed.set_timestamp()
        webhook.add_embed(embed)
        response = webhook.execute()
        time.sleep(5)
        if response.status_code != 200:
            logger(args.silent,"Cannot send to discord",TYPE="error")
            exit(1)
        logger(args.silent,"Sent to discord.",TYPE="success")

    if args.telegram:
        webhook = args.webhook
        chat_id = args.chat_id
        message = urllib.parse.quote_plus(f'{title}\n———————————————\n🎯Scopes: {scp}———————————————\n> Platform {platform}\n———————————————\n> Name: {data["name"]}\n———————————————\n> Type {data["type"]}\n———————————————\nURL: {data["url"]}')
        req = requests.get(f"https://api.telegram.org/bot{webhook}/sendmessage?chat_id={chat_id}&text={message}")
        time.sleep(5)
        if req.status_code != 200:
            logger(args.silent,"Cannot send to Telegram check chat_id and Webhook",TYPE="error")
            exit(1)

def updateProgram(args,mycol,platform,data):
    logger(args.silent,"Adding {} [{}] : to Database.".format(data["name"],platform),TYPE="pending")
    try:
        mycol.insert_one(data)
        logger(args.silent,"Program Added.",TYPE="success")
        push(args,platform,data,data["in_scope"])
    except Exception as e:
        logger(args.silent,"{}".format(e),TYPE="error")
        exit(1)

def updateScope(args,mycol,platform,data,scopes,Type,old):
    try:
        if Type == "in":
            logger(args.silent,"Adding {}'s new in_scopes [{}] : to Database.".format(data["name"],platform),TYPE="pending")
            for scope in scopes:
                if scope in old:
                    old.remove(scope)
            update = mycol.update_one({"handle":data["handle"]},{"$set":{"out_of_scope":old}})
            for scope in scopes:
                update = mycol.update_one({"handle":data["handle"]},{"$push":{"in_scope":scope}})
            push(args,platform,data,scopes,"in")

        elif Type == "out":
            logger(args.silent,"Adding {}'s new out_of_scopes [{}] : to Database.".format(data["name"],platform),TYPE="pending")
            for scope in scopes:
                if scope in old:
                    old.remove(scope)
            update = mycol.update_one({"handle":data["handle"]},{"$set":{"in_scope":old}})
            for scope in scopes:
                update = mycol.update_one({"handle":data["handle"]},{"$push":{"out_of_scope":scope}})
            push(args,platform,data,scopes,"out")

    except Exception as e:
        logger(args.silent,"{}".format(e),TYPE="error")
        
def check_old_data(args,platform,Program,mydb):
    try:
        new_in_scopes = []
        new_out_of_scopes = []
        updated = False
        mycol = mydb[platform]

        for data in Program[platform]:
            program = mycol.find_one({"handle":data["handle"]})
            if program == None:
                logger(args.silent,"Program Not found in Database.",TYPE="error")
                updateProgram(args,mycol,platform,data)
                updated = True

            elif program != None:

                old_inscopes = mycol.find_one({"handle":data["handle"]})["in_scope"]
                old_out_of_scopes = mycol.find_one({"handle":data["handle"]})["out_of_scope"]

                for new_in_scope in data["in_scope"]:
                    if new_in_scope not in old_inscopes:
                        logger(args.silent,"New in_Scope founds! on {} : {}".format(platform,new_in_scope),TYPE="success")
                        new_in_scopes.append(new_in_scope)

                if new_in_scopes != []:
                    updateScope(args,mycol,platform,data,new_in_scopes,"in",old_out_of_scopes)
                    new_in_scopes = []
                    updated == True
                    
                old_inscopes = mycol.find_one({"handle":data["handle"]})["in_scope"]
                old_out_of_scopes = mycol.find_one({"handle":data["handle"]})["out_of_scope"]

                for new_out_of_scope in old_inscopes:
                    if new_out_of_scope not in data["in_scope"]:
                        logger(args.silent,"New out_of_Scope founds! on {} : {}".format(platform,new_out_of_scope),TYPE="success")
                        new_out_of_scopes.append(new_out_of_scope)

                if new_out_of_scopes != []:
                    updateScope(args,mycol,platform,data,new_out_of_scopes,"out",old_inscopes)
                    new_out_of_scopes = []
                    updated == True


        if updated == False:
            logger(args.silent,"No changes were found in {}. ".format(platform),TYPE="success")

    except Exception as e:
        logger(args.silent,"{}".format(e),TYPE="error")
        exit(1)


def getPlatforms(args,platform):

    if platform.name == "hackerone":
        logger(args.silent,"Checking {}".format(platform.name),TYPE="pending")
        try:
            logger(args.silent,"Sending HTTP Request to {} to get recent JSON Object.".format(platform.url),TYPE="pending")
            res = requests.get(platform.url).json()
            logger(args.silent,"got the JSON Object.",TYPE="success")
        except Exception as e:
            logger(args.silent,"{}".format(e),TYPE="error")
            exit(1)
        logger(args.silent,"Cleaning JSON Object.",TYPE="pending")
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
    
    elif platform.name == "bugcrowd":
        logger(args.silent,"Checking {}".format(platform.name),TYPE="pending")
        try:

            logger(args.silent,"Sending HTTP Request to {} to get recent JSON Object.".format(platform.url),TYPE="pending")
            res = requests.get(platform.url).json()
            logger(args.silent,"got the JSON Object.",TYPE="success")
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

            return {platform.name:programs}
        except Exception as e:
            logger(args.silent,"{}".format(e),TYPE="error")
            exit(1)

    elif platform.name == "yeswehack":
        logger(args.silent,"Checking {}".format(platform.name),TYPE="pending")
        try:
            logger(args.silent,"Sending HTTP Request to {} to get recent JSON Object.".format(platform.url),TYPE="pending")
            res = requests.get(platform.url).json()
            logger(args.silent,"got the JSON Object.",TYPE="success")
        except Exception as e:
            logger(args.silent,"{}".format(e),TYPE="error")
            exit(1)
        logger(args.silent,"Cleaning JSON Object.",TYPE="pending")
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

        return {platform.name:programs}
    
    elif platform.name == "intigriti":
        logger(args.silent,"Checking {}".format(platform.name),TYPE="pending")
        try:
            logger(args.silent,"Sending HTTP Request to {} to get recent JSON Object.".format(platform.url),TYPE="pending")
            res = requests.get(platform.url).json()
            logger(args.silent,"got the JSON Object.",TYPE="success")
        except Exception as e:
            logger(args.silent,"{}".format(e),TYPE="error")
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

        return {platform.name:programs}

def main():
    parser = argparse.ArgumentParser(description='Watch scope')
    parser.add_argument("--silent",action="store_true",help="Turn on Logging.")
    parser.add_argument("--update",action="store_true",help="Update Database.")
    parser.add_argument("--telegram",action="store_true",help="set sending method to telegram")
    parser.add_argument("--discord",action="store_true",help="set sending method to discord")
    parser.add_argument("-w","--webhook",help="telegram(BOT-TOKEN) or discord webhook link")
    parser.add_argument("-id","--chat_id",help="telegram chat_id")
    parser.add_argument("-p","--platform",help="bugbounty platform names (ex: hackerone,bugcrowd). default: all",default="all")
    args = parser.parse_args()

    if not len(sys.argv) > 1:
        args.silent = config.silent        
        args.update = config.update
        args.discord = config.discord
        args.telegram = config.telegram
        args.webhook = config.webhook
        args.chat_id = config.chat_id
        args.platform = config.platform

    myclient = pymongo.MongoClient("mongodb://{}:{}/".format(config.mongo_host,config.mongo_port))
    is_exist = existdb(args,myclient)
    mydb = myclient[config.db]

    if args.platform == "all":
        platforms = ["hackerone","bugcrowd","yeswehack","intigriti"]
    else:
        platforms = args.platform.split(",")

    if args.update or is_exist != True:

        if is_exist == True:
            logger(args.silent,"Removing previous Database.",TYPE="pending")
            myclient.drop_database(config.db)
            logger(args.silent,"Database Removed.",TYPE="success")

        for p in platforms:
            data = Program(p,{})
            program = getPlatforms(args,data)
            updateDatabase(args,program,mydb)
            #check_old_data(args,p,program,mydb)

    elif args.telegram or args.discord:
        for p in platforms:
            data = Program(p,{})
            program = getPlatforms(args,data)
            check_old_data(args,p,program,mydb)

if __name__ == "__main__":
    main()