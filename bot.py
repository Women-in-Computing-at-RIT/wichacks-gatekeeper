import sys

import discord
import os
import requests
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.reactions = True

client = discord.Client(intents=discord.Intents.all())  # Client initialization
WELCOME_CHANNEL_ID = 1108762097153749133
WICHACKS_GUILD_ID = 1108761815262969937
WICHACKS_GUILD = None


GATEKEEPER_ID = 1076312179432771605

load_dotenv()
SECRET_TOKEN = os.environ.get('BOT_TOKEN')
WICHACKS_API_URL = os.environ.get('WICHACKS_API_URL')

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
AUTH0_AUDIENCE = "wichacks.io"
AUTH0_GRANT_TYPE = "client_credentials"
AUTH0_OAUTH_ENDPOINT = "https://wichacks.us.auth0.com/oauth/token"
auth0Token = None

welcomeMessage = 1208561838342803488

CHECKED_EMOJI = '\N{THUMBS UP SIGN}'
CHECKED_EMOJI_ID = '1078162461661859900'

HACKER_ROLE = 1108762055294595082
HACKER_ROLE_NAME = "hacker"
UNREGISTERED_ROLE = 1108762062613655664
UNREGISTERED_ROLE_NAME = "unregistered"


async def generateNewOauthToken() -> bool:
    global auth0Token
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": AUTH0_AUDIENCE,
        "grant_type": AUTH0_GRANT_TYPE
    }
    auth0Response = requests.post(AUTH0_OAUTH_ENDPOINT, data=payload)
    if not auth0Response.status_code == 200:
        print("Auth0 Oauth Request Failure")
        print(auth0Response.json())
        return False
    auth0Token = auth0Response.json()['access_token']
    return True


async def initializeAPIConnection() -> bool:
    # check healthcheck of API
    response = requests.get(WICHACKS_API_URL + '/')
    if not response.status_code == 200:
        print("Could not connect to API")
        return False

    # generate oauth token
    return await generateNewOauthToken()


async def getWiCHackerManagerData(discordId):
    headers = {
        'authorization': 'Bearer ' + auth0Token
    }
    hackerDataResponse = requests.get(WICHACKS_API_URL + "/discord/user/" + str(discordId), headers=headers)
    if not hackerDataResponse.status_code == 200:
        if hackerDataResponse.status_code == 401:
            # if unauthorized then our token may have expired, generate a new one and try again
            await generateNewOauthToken()
            return await getWiCHackerManagerData(discordId)
        print("Could not get hacker data: ", hackerDataResponse.json())
        print("API Response: ", hackerDataResponse.status_code)
        return None
    return hackerDataResponse.json()


async def handleNewHacker(hacker, discordId):
    hackerData = await getWiCHackerManagerData(discordId)
    if hackerData is None:
        return False
    applicationStatus = hackerData['status']
    if applicationStatus not in ["ACCEPTED", "CONFIRMED"]:
        # make sure hacker can access server
        print("Hacker is not accepted or confirmed. Application Status=%s", applicationStatus)
        return False

    firstName = hackerData['first_name']
    lastName = hackerData['last_name']
    nickname = f'{firstName} {lastName}'
    await hacker.add_roles(HACKER_ROLE)
    await hacker.remove_roles(UNREGISTERED_ROLE)
    await hacker.edit(nick=nickname)
    return True


def getStartupMessageContent():
    return '''
    I agree to sign my life away to Alex along with 45% of my lifetime earnings because he wants to eat ice cream [test](wichacks.io)
    '''


async def sendStartupMessage():
    global welcomeMessage
    welcomeChannel = client.get_channel(WELCOME_CHANNEL_ID)
    welcomeMessage = await welcomeChannel.send(getStartupMessageContent())
    await welcomeMessage.add_reaction(CHECKED_EMOJI)
    return


@client.event
async def on_ready():
    global WICHACKS_GUILD
    global UNREGISTERED_ROLE
    global HACKER_ROLE

    print("Starting Up")

    connectionUp = await initializeAPIConnection()
    if not connectionUp:
        sys.exit(1)

    for guild in client.guilds:
        if guild.id == WICHACKS_GUILD_ID:
            WICHACKS_GUILD = guild
            break

    for role in WICHACKS_GUILD.roles:
        if HACKER_ROLE_NAME in role.name.lower():
            HACKER_ROLE = role
        elif UNREGISTERED_ROLE_NAME in role.name.lower():
            UNREGISTERED_ROLE = role

    await sendStartupMessage()
    print("Ready to go")
    return


@client.event
async def on_message(message):
    if not message.content.startswith("-"):
        return
    command = message.content.strip().split()[0].lower()
    if command == "-check":
        await message.channel.send("I'm Alive")


@client.event
async def on_reaction_add(reaction, user: discord.user):
    """
    check if accepted/confirmed
    change nickname
    remove unregistered role
    give hacker role
    party
    :return:
    """
    if user.id == GATEKEEPER_ID:
        # don't do anything when the bot adds the reaction
        return
    discordId = user.id
    messageId = reaction.message.id
    emoji = reaction.emoji
    if not (messageId == welcomeMessage.id and emoji == CHECKED_EMOJI):
        # reaction is not to welcome message or is wrong reaction
        return
    await handleNewHacker(user, discordId)
    return


def main():
    client.run(SECRET_TOKEN)


if __name__ == '__main__':
    main()
